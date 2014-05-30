#import chardet
import pkgutil
import yaml
from chardet.universaldetector import UniversalDetector
from io import BytesIO

from header_rewriter import RewrittenStatusAndHeaders

from rewriterules import RewriteRules, is_lxml

from pywb.utils.dsrules import RuleSet
from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.bufferedreaders import DecompressingBufferedReader
from pywb.utils.bufferedreaders import ChunkedDataReader


#=================================================================
class RewriteContent:
    def __init__(self, ds_rules_file=None, defmod=''):
        self.ruleset = RuleSet(RewriteRules, 'rewrite',
                               default_rule_config={},
                               ds_rules_file=ds_rules_file)
        self.defmod = defmod

    def sanitize_content(self, status_headers, stream):
        # remove transfer encoding chunked and wrap in a dechunking stream
        if (status_headers.remove_header('transfer-encoding')):
            stream = ChunkedDataReader(stream)

        return (status_headers, stream)

    def rewrite_headers(self, urlrewriter, status_headers, stream, urlkey=''):

        header_rewriter_class = (self.ruleset.get_first_match(urlkey).
                                 rewriters['header'])

        rewritten_headers = (header_rewriter_class().
                             rewrite(status_headers, urlrewriter))

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

    def rewrite_content(self, urlrewriter, headers, stream,
                        head_insert_func=None, urlkey='',
                        sanitize_only=False, cdx=None, mod=None):

        if sanitize_only:
            status_headers, stream = self.sanitize_content(headers, stream)
            return (status_headers, self.stream_to_gen(stream), False)

        (rewritten_headers, stream) = self.rewrite_headers(urlrewriter,
                                                           headers,
                                                           stream)

        status_headers = rewritten_headers.status_headers

        # use rewritten headers, but no further rewriting needed
        if rewritten_headers.text_type is None:
            return (status_headers, self.stream_to_gen(stream), False)

        # Handle text content rewriting
        # ====================================================================
        # special case -- need to ungzip the body

        text_type = rewritten_headers.text_type

        # see known js/css modifier specified, the context should run
        # default text_type
        if mod == 'js_':
            text_type = 'js'
        elif mod == 'cs_':
            text_type = 'css'

        stream_raw = False
        encoding = None
        first_buff = None

        if (rewritten_headers.
             contains_removed_header('content-encoding', 'gzip')):

            #optimize: if already a ChunkedDataReader, add gzip
            if isinstance(stream, ChunkedDataReader):
                stream.set_decomp('gzip')
            else:
                stream = DecompressingBufferedReader(stream)

        if rewritten_headers.charset:
            encoding = rewritten_headers.charset
        elif is_lxml() and text_type == 'html':
            stream_raw = True
        else:
            (encoding, first_buff) = self._detect_charset(stream)

        # if encoding not set or chardet thinks its ascii, use utf-8
        if not encoding or encoding == 'ascii':
            encoding = 'utf-8'

        rule = self.ruleset.get_first_match(urlkey)

        rewriter_class = rule.rewriters[text_type]

        # for html, need to perform header insert, supply js, css, xml
        # rewriters
        if text_type == 'html':
            head_insert_str = ''

            if head_insert_func:
                head_insert_str = head_insert_func(rule, cdx)

            rewriter = rewriter_class(urlrewriter,
                                      js_rewriter_class=rule.rewriters['js'],
                                      css_rewriter_class=rule.rewriters['css'],
                                      head_insert=head_insert_str,
                                      defmod=self.defmod)

        else:
        # apply one of (js, css, xml) rewriters
            rewriter = rewriter_class(urlrewriter)

        # Create rewriting generator
        gen = self._rewriting_stream_gen(rewriter, encoding, stream_raw,
                                         stream, first_buff)

        return (status_headers, gen, True)

    def _parse_full_gen(self, rewriter, encoding, stream):
        buff = rewriter.parse(stream)
        buff = buff.encode(encoding)
        yield buff

    # Create rewrite stream,  may even be chunked by front-end
    def _rewriting_stream_gen(self, rewriter, encoding, stream_raw,
                              stream, first_buff=None):

        if stream_raw:
            return self._parse_full_gen(rewriter, encoding, stream)

        def do_rewrite(buff):
            buff = self._decode_buff(buff, stream, encoding)

            buff = rewriter.rewrite(buff)

            buff = buff.encode(encoding)

            return buff

        def do_finish():
            result = rewriter.close()
            result = result.encode(encoding)

            return result

        return self.stream_to_gen(stream,
                                  rewrite_func=do_rewrite,
                                  final_read_func=do_finish,
                                  first_buff=first_buff)

    @staticmethod
    def _decode_buff(buff, stream, encoding):
        try:
            buff = buff.decode(encoding)
        except UnicodeDecodeError, e:
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

    def _detect_charset(self, stream):
        full_buff = stream.read(8192)
        io_buff = BytesIO(full_buff)

        detector = UniversalDetector()

        try:
            buff = io_buff.read(256)
            while buff:
                detector.feed(buff)
                if detector.done:
                    break

                buff = io_buff.read(256)
        finally:
            detector.close()

        print "chardet result: " + str(detector.result)
        return (detector.result['encoding'], full_buff)

    # Create a generator reading from a stream,
    # with optional rewriting and final read call
    @staticmethod
    def stream_to_gen(stream, rewrite_func=None,
                      final_read_func=None, first_buff=None):
        try:
            if first_buff:
                buff = first_buff
            else:
                buff = stream.read()
                if buff:
                    buff += stream.readline()

            while buff:
                if rewrite_func:
                    buff = rewrite_func(buff)
                yield buff
                buff = stream.read()
                if buff:
                    buff += stream.readline()

            # For adding a tail/handling final buffer
            if final_read_func:
                buff = final_read_func()
                if buff:
                    yield buff

        finally:
            stream.close()
