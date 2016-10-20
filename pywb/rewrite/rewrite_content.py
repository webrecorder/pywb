#import chardet
import pkgutil
import webencodings
import yaml
import re

#from chardet.universaldetector import UniversalDetector
from io import BytesIO

from pywb.rewrite.header_rewriter import RewrittenStatusAndHeaders

from pywb.rewrite.rewriterules import RewriteRules

from pywb.utils.dsrules import RuleSet
from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.bufferedreaders import DecompressingBufferedReader
from pywb.utils.bufferedreaders import ChunkedDataReader, BufferedReader
from pywb.utils.loaders import to_native_str

from pywb.rewrite.regex_rewriters import JSNoneRewriter, JSLinkOnlyRewriter


#=================================================================
class RewriteContent(object):
    HEAD_REGEX = re.compile(b'<\s*head\\b[^>]*[>]+', re.I)

    TAG_REGEX = re.compile(b'^\s*\<')

    CHARSET_REGEX = re.compile(b'<meta[^>]*?[\s;"\']charset\s*=[\s"\']*([^\s"\'/>]*)')

    BUFF_SIZE = 16384

    def __init__(self, ds_rules_file=None, is_framed_replay=False):
        self.ruleset = RuleSet(RewriteRules, 'rewrite',
                               default_rule_config={},
                               ds_rules_file=ds_rules_file)

        if is_framed_replay == 'inverse':
            self.defmod = 'mp_'
        else:
            self.defmod = ''

    def sanitize_content(self, status_headers, stream):
        # remove transfer encoding chunked and wrap in a dechunking stream
        if (status_headers.remove_header('transfer-encoding')):
            stream = ChunkedDataReader(stream)

        return (status_headers, stream)

    def _rewrite_headers(self, urlrewriter, rule, status_headers, stream,
                         urlkey='', cookie_rewriter=None):

        header_rewriter_class = rule.rewriters['header']

        if urlrewriter and not cookie_rewriter:
            cookie_rewriter = urlrewriter.get_cookie_rewriter(rule)

        rewritten_headers = (header_rewriter_class().
                             rewrite(status_headers,
                                     urlrewriter,
                                     cookie_rewriter))

        # note: since chunk encoding may/may not be valid,
        # the approach taken here is to *always* attempt
        # to dechunk if 'transfer-encoding: chunked' is present
        #
        # an alternative may be to serve chunked unless
        # content rewriting is needed
        # todo: possible revisit this approach

        if (rewritten_headers.
             contains_removed_header('transfer-encoding', 'chunked')):

            stream = ChunkedDataReader(stream)

        return (rewritten_headers, stream)


    def _check_encoding(self, rewritten_headers, stream, enc):
        matched = False
        if (rewritten_headers.
             contains_removed_header('content-encoding', enc)):

            #optimize: if already a ChunkedDataReader, add the encoding
            if isinstance(stream, ChunkedDataReader):
                stream.set_decomp(enc)
            else:
                stream = DecompressingBufferedReader(stream, decomp_type=enc)

            rewritten_headers.status_headers.remove_header('content-length')
            matched = True

        return matched, stream



    def rewrite_content(self, urlrewriter, status_headers, stream,
                        head_insert_func=None, urlkey='',
                        cdx=None, cookie_rewriter=None, env=None):

        wb_url = urlrewriter.wburl

        if (wb_url.is_identity or
             (not head_insert_func and wb_url.is_banner_only)):
            status_headers, stream = self.sanitize_content(status_headers,
                                                           stream)
            return (status_headers, self.stream_to_gen(stream), False)

        if urlrewriter and cdx and cdx.get('is_live'):
            urlrewriter.rewrite_opts['is_live'] = True

        rule = self.ruleset.get_first_match(urlkey)

        (rewritten_headers, stream) = self._rewrite_headers(urlrewriter,
                                                            rule,
                                                            status_headers,
                                                            stream,
                                                            urlkey,
                                                            cookie_rewriter)

        res = self.handle_custom_rewrite(rewritten_headers,
                                         stream,
                                         urlrewriter,
                                         wb_url.mod,
                                         env)
        if res:
            return res

        # Handle text content rewriting
        # ====================================================================
        # special case -- need to ungzip the body

        status_headers = rewritten_headers.status_headers
        text_type = rewritten_headers.text_type

        # see known js/css modifier specified, the context should run
        # default text_type
        mod = wb_url.mod

        stream_raw = False
        encoding = None
        first_buff = b''

        for decomp_type in BufferedReader.get_supported_decompressors():
            matched, stream = self._check_encoding(rewritten_headers,
                                                   stream,
                                                   decomp_type)
            if matched:
                break

        if mod == 'js_':
            text_type, stream = self._resolve_text_type('js',
                                                        text_type,
                                                        stream)
        elif mod == 'cs_':
            text_type, stream = self._resolve_text_type('css',
                                                        text_type,
                                                        stream)

        # for proxy mode: use special js_proxy rewriter
        # which may be none rewriter + custom rules (if any)
        if text_type == 'js' and not urlrewriter.prefix:
            rewriter_class = rule.rewriters['js_proxy']
        else:
            rewriter_class = rule.rewriters[text_type]

        # for html, need to perform header insert, supply js, css, xml
        # rewriters
        if text_type == 'html':
            head_insert_str = ''
            charset = rewritten_headers.charset

            # if no charset set, attempt to extract from first 1024
            if not rewritten_headers.charset:
                first_buff = stream.read(1024)
                charset = self._extract_html_charset(first_buff,
                                                     status_headers)

            if head_insert_func and not wb_url.is_url_rewrite_only:
                head_insert_orig = head_insert_func(rule, cdx)

                if charset:
                    try:
                        head_insert_str = webencodings.encode(head_insert_orig, charset)
                    except:
                        pass

                if not head_insert_str:
                    charset = 'utf-8'
                    head_insert_str = head_insert_orig.encode(charset)

                head_insert_buf = head_insert_str
                #head_insert_str = to_native_str(head_insert_str)
                head_insert_str = head_insert_str.decode('iso-8859-1')


            if wb_url.is_banner_only:
                gen = self._head_insert_only_gen(head_insert_buf,
                                                 stream,
                                                 first_buff)

                content_len = status_headers.get_header('Content-Length')
                try:
                    content_len = int(content_len)
                except Exception:
                    content_len = None

                if content_len and content_len >= 0:
                    content_len = str(content_len + len(head_insert_str))
                    status_headers.replace_header('Content-Length',
                                                  content_len)

                return (status_headers, gen, False)

            # if proxy, use js_proxy rewriter
            if not urlrewriter.prefix:
                js_rewriter_class = rule.rewriters['js_proxy']
            else:
                js_rewriter_class = rule.rewriters['js']

            css_rewriter_class = rule.rewriters['css']

            if wb_url.is_url_rewrite_only:
                js_rewriter_class = JSNoneRewriter

            rewriter = rewriter_class(urlrewriter,
                                      js_rewriter_class=js_rewriter_class,
                                      css_rewriter_class=css_rewriter_class,
                                      head_insert=head_insert_str,
                                      url=wb_url.url,
                                      defmod=self.defmod,
                                      parse_comments=rule.parse_comments)

        else:
            if wb_url.is_banner_only:
                return (status_headers, self.stream_to_gen(stream), False)

            # url-only rewriter, but not rewriting urls in JS, so return
            if wb_url.is_url_rewrite_only and text_type == 'js':
                #return (status_headers, self.stream_to_gen(stream), False)
                rewriter_class = JSLinkOnlyRewriter

            # apply one of (js, css, xml) rewriters
            rewriter = rewriter_class(urlrewriter)


        # align to line end for all non-html rewriting
        align = (text_type != 'html')

        # Create rewriting generator
        gen = self.rewrite_text_stream_to_gen(stream,
                                              rewrite_func=rewriter.rewrite,
                                              final_read_func=rewriter.close,
                                              first_buff=first_buff,
                                              align_to_line=align)

        return (status_headers, gen, True)

    def handle_custom_rewrite(self, rewritten_headers, stream,
                              urlrewriter, mod, env):

        text_type = rewritten_headers.text_type
        status_headers = rewritten_headers.status_headers

        # use rewritten headers, but no further rewriting needed
        if text_type is None:
            return (status_headers, self.stream_to_gen(stream), False)

        if ((text_type == 'html' and urlrewriter.rewrite_opts.get('is_ajax')) or
            (text_type == 'plain' and not mod in ('js_', 'cs_'))):
            rewritten_headers.readd_rewrite_removed()
            return (status_headers, self.stream_to_gen(stream), False)

    @staticmethod
    def _extract_html_charset(buff, status_headers):
        charset = None
        m = RewriteContent.CHARSET_REGEX.search(buff)
        if m:
            charset = m.group(1)
            charset = to_native_str(charset)
        #    content_type = 'text/html; charset=' + charset
        #    status_headers.replace_header('content-type', content_type)

        return charset

    @staticmethod
    def _resolve_text_type(mod, text_type, stream):
        if text_type == 'css' and mod == 'js':
            return 'css', stream

        # only attempt to resolve between html and other text types
        if text_type != 'html':
            return mod, stream

        buff = stream.read(128)

        wrapped_stream = BufferedReader(stream, starting_data=buff)

        # check if starts with a tag, then likely html
        if RewriteContent.TAG_REGEX.match(buff):
            mod = 'html'

        return mod, wrapped_stream

    def _head_insert_only_gen(self, insert_str, stream, first_buff=b''):
        buff = first_buff
        max_len = 1024 - len(first_buff)
        while max_len > 0:
            curr = stream.read(max_len)
            if not curr:
                break

            max_len -= len(buff)
            buff += curr

        matcher = self.HEAD_REGEX.search(buff)

        if matcher:
            yield buff[:matcher.end()]
            yield insert_str
            yield buff[matcher.end():]
        else:
            yield insert_str
            yield buff

        for buff in self.stream_to_gen(stream):
            yield buff

    @staticmethod
    def _decode_buff(buff, stream, encoding):  # pragma: no coverage
        try:
            buff = buff.decode(encoding)
        except UnicodeDecodeError as e:
            # chunk may have cut apart unicode bytes -- add 1-3 bytes and retry
            for i in range(3):
                buff += stream.read(1)
                try:
                    buff = buff.decode(encoding)
                    break
                except UnicodeDecodeError:
                    pass
            else:
                raise

        return buff

    @staticmethod
    def stream_to_gen(stream):
        """
        Convert stream to an iterator, reading BUFF_SIZE bytes
        """
        try:
            while True:
                buff = stream.read(RewriteContent.BUFF_SIZE)
                yield buff
                if not buff:
                    break

        finally:
            stream.close()

    @staticmethod
    def rewrite_text_stream_to_gen(stream, rewrite_func,
                                   final_read_func, first_buff,
                                   align_to_line):
        """
        Convert stream to generator using applying rewriting func
        to each portion of the stream.
        Align to line boundaries if needed.
        """
        try:
            has_closed = hasattr(stream, 'closed')
            buff = first_buff

            while True:
                if buff:
                    buff = rewrite_func(buff.decode('iso-8859-1'))
                    yield buff.encode('iso-8859-1')

                buff = stream.read(RewriteContent.BUFF_SIZE)
                # on 2.6, readline() (but not read()) throws an exception
                # if stream already closed, so check stream.closed if present
                if (buff and align_to_line and
                    (not has_closed or not stream.closed)):
                    buff += stream.readline()

                if not buff:
                    break

            # For adding a tail/handling final buffer
            buff = final_read_func()
            if buff:
                yield buff.encode('iso-8859-1')

        finally:
            stream.close()


