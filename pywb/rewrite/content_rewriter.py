import codecs
import json
import re
import tempfile
from contextlib import closing

import webencodings
from warcio.bufferedreaders import BufferedReader, ChunkedDataReader
from warcio.utils import to_native_str

from pywb.utils.io import BUFF_SIZE, StreamIter
from pywb.utils.loaders import load_py_name, load_yaml_config
from pywb.utils.constants import CharSets, ContentRewriteTypes, RewriteMods


# ============================================================================
class BaseContentRewriter(object):
    CHARSET_REGEX = re.compile(b'<meta[^>]*?[\s;"\']charset\s*=[\s"\']*([^\s"\'/>]*)')

    def __init__(self, rules_file, replay_mod=''):
        self.rules = []
        self.all_rewriters = {}
        self.load_rules(rules_file)
        self.replay_mod = replay_mod

    def add_rewriter(self, rw):
        self.all_rewriters[rw.name] = rw

    def get_rewriter(self, rw_type, rwinfo=None):
        return self.all_rewriters.get(rw_type)

    def load_rules(self, filename):
        config = load_yaml_config(filename)
        for rule in config.get('rules'):
            rule = self.parse_rewrite_rule(rule)
            if rule:
                self.rules.append(rule)

    def parse_rewrite_rule(self, config):
        rw_config = config.get('rewrite')
        if not rw_config:
            return

        rule = rw_config
        url_prefix = config.get('url_prefix')
        if not isinstance(url_prefix, list):
            url_prefix = [url_prefix]

        rule['url_prefix'] = url_prefix

        regexs = rule.get('js_regexs')
        if regexs:
            parse_rules_func = self.init_js_regex(regexs)
            rule['js_regex_func'] = parse_rules_func

        mixin = rule.get('mixin')
        if mixin:
            rule['mixin'] = load_py_name(mixin)

        return rule

    def get_rule(self, cdx):
        urlkey = to_native_str(cdx['urlkey'])

        for rule in self.rules:
            if any((urlkey.startswith(prefix) for prefix in rule['url_prefix'])):
                return rule

        return {}

    def has_custom_rules(self, rule, cdx):
        if 'js_regex_func' not in rule:
            return False

        if rule.get('live_only') and not cdx.get('is_live'):
            return False

        return True

    def get_rw_class(self, rule, text_type, rwinfo):
        if text_type == ContentRewriteTypes.json and 'js_regex_func' in rule:
            text_type = ContentRewriteTypes.js_proxy

        if text_type == ContentRewriteTypes.js and not rwinfo.is_url_rw():
            text_type = ContentRewriteTypes.js_proxy

        rw_type = rule.get(text_type, text_type)
        rw_class = self.get_rewriter(rw_type, rwinfo)

        mixin = rule.get('mixin')
        if mixin:
            mixin_params = rule.get('mixin_params', {})
            rw_class = type('custom_js_rewriter', (mixin, rw_class), mixin_params)

        return rw_type, rw_class

    def create_rewriter(self, text_type, rule, rwinfo, cdx, head_insert_func=None):
        rw_type, rw_class = self.get_rw_class(rule, text_type, rwinfo)

        if rw_type in ContentRewriteTypes.js_and_js_proxy:
            extra_rules = []
            if self.has_custom_rules(rule, cdx):
                extra_rules = rule['js_regex_func'](rwinfo.url_rewriter)

            # if js-proxy and no rules, default to none
            # js rewriting in proxy only if extra rules apply
            if rw_type == ContentRewriteTypes.js_proxy and not extra_rules:
                return None

            return rw_class(rwinfo.url_rewriter, extra_rules)

        elif rw_type != ContentRewriteTypes.html:
            return rw_class(rwinfo.url_rewriter)

        # HTML Rewriter
        head_insert_str = self.get_head_insert(rwinfo, rule, head_insert_func, cdx)

        js_rewriter = self.create_rewriter(ContentRewriteTypes.js, rule, rwinfo, cdx)
        css_rewriter = self.create_rewriter(ContentRewriteTypes.css, rule, rwinfo, cdx)

        # if no js rewriter, then do banner insert only
        if not js_rewriter:
            rw_class = self.get_rewriter('html-banner-only', rwinfo)

        rw = rw_class(
            rwinfo.url_rewriter,
            js_rewriter=js_rewriter,
            css_rewriter=css_rewriter,
            head_insert=head_insert_str,
            url=cdx['url'],
            defmod=self.replay_mod,
            parse_comments=rule.get('parse_comments', False),
            charset=rwinfo.charset,
        )

        return rw

    def get_head_insert(self, rwinfo, rule, head_insert_func, cdx):
        head_insert_str = ''

        # if no charset set, attempt to extract from first 1024
        if not rwinfo.charset:
            first_buff = rwinfo.read_and_keep(1024)
            rwinfo.charset = self.extract_html_charset(first_buff)

        if head_insert_func:
            head_insert_orig = head_insert_func(rule, cdx)

            if rwinfo.charset:
                try:
                    head_insert_str = webencodings.encode(
                        head_insert_orig, rwinfo.charset
                    )
                except Exception:
                    pass

            # no charset detected, encode banner as ascii html entities
            if not head_insert_str:
                head_insert_str = head_insert_orig.encode(
                    CharSets.ascii, 'xmlcharrefreplace'
                )

            head_insert_str = head_insert_str.decode(CharSets.iso)

        return head_insert_str

    def extract_html_charset(self, buff):
        charset = None
        m = self.CHARSET_REGEX.search(buff)
        if m:
            charset = m.group(1)
            charset = to_native_str(charset)

        return charset

    def rewrite_headers(self, rwinfo):
        header_rw_class = self.get_rewriter('header', rwinfo)
        return header_rw_class(rwinfo)()

    def __call__(
        self,
        record,
        url_rewriter,
        cookie_rewriter,
        head_insert_func=None,
        cdx=None,
        environ=None,
    ):

        environ = environ or {}
        rwinfo = RewriteInfo(record, self, url_rewriter, cookie_rewriter)
        content_rewriter = None

        url_rewriter.rewrite_opts['cdx'] = cdx

        rule = self.get_rule(cdx)

        if rule.get('mixin') and not rwinfo.text_type:
            rwinfo.text_type = rule.get('mixin_type', 'json')

        if rwinfo.should_rw_content():
            content_rewriter = self.create_rewriter(
                rwinfo.text_type, rule, rwinfo, cdx, head_insert_func
            )

        gen = None

        # check if decoding is needed
        if not rwinfo.is_content_rw:
            content_encoding = rwinfo.record.http_headers.get_header('Content-Encoding')
            accept_encoding = environ.get('HTTP_ACCEPT_ENCODING', '')

            # if content-encoding is set but encoding is not in accept encoding,
            # enable content_rw force decompression
            if content_encoding and content_encoding not in accept_encoding:
                rwinfo.is_content_rw = True

        if content_rewriter:
            gen = content_rewriter(rwinfo)
        elif rwinfo.is_content_rw:
            gen = StreamIter(rwinfo.content_stream)

        rw_http_headers = self.rewrite_headers(rwinfo)

        if not gen:
            # if not rewriting content, still need to dechunk
            # to conform to WSGI spec
            if rwinfo.is_chunked:
                stream = ChunkedDataReader(rwinfo.record.raw_stream, decomp_type=None)
            else:
                stream = rwinfo.record.raw_stream

            gen = StreamIter(stream)

        return rw_http_headers, gen, content_rewriter is not None

    def init_js_regexs(self, regexs):
        raise NotImplemented()

    def get_rewrite_types(self):
        raise NotImplemented()


# ============================================================================
class BufferedRewriter(object):
    def __init__(self, url_rewriter=None):
        self.url_rewriter = url_rewriter

    def __call__(self, rwinfo):
        stream_buffer = tempfile.SpooledTemporaryFile(BUFF_SIZE * 4)

        with closing(rwinfo.content_stream) as fh:
            while True:
                buff = fh.read()
                if not buff:
                    break

                stream_buffer.write(buff)

        stream_buffer.seek(0)
        return StreamIter(self.rewrite_stream(stream_buffer, rwinfo))

    def rewrite_stream(self, stream, rwinfo):
        raise NotImplemented('implement in subclass')

    def _get_record_metadata(self, rwinfo):
        client_metadata = rwinfo.record.rec_headers.get_header('WARC-JSON-Metadata')
        if client_metadata:
            try:
                return json.loads(client_metadata)
            except Exception:
                pass

        return {}

    def _get_adaptive_metadata(self, rwinfo):
        metadata = self._get_record_metadata(rwinfo) if rwinfo else dict()
        max_resolution = int(metadata.get('adaptive_max_resolution', 0))
        max_bandwidth = int(metadata.get('adaptive_max_bandwidth', 1000000000))
        return max_resolution, max_bandwidth


# ============================================================================
class StreamingRewriter(object):
    def __init__(self, url_rewriter, align_to_line=True, first_buff=''):
        self.url_rewriter = url_rewriter
        self.align_to_line = align_to_line
        self.first_buff = first_buff

    def __call__(self, rwinfo):
        return self.rewrite_text_stream_to_gen(rwinfo.content_stream, rwinfo)

    def rewrite(self, string):
        return string

    def rewrite_complete(self, string, **kwargs):
        return self.first_buff + self.rewrite(string) + self.final_read()

    def final_read(self):
        return ''

    def rewrite_text_stream_to_gen(self, stream, rwinfo):
        """
        Convert stream to generator using applying rewriting func
        to each portion of the stream.
        Align to line boundaries if needed.
        """
        try:
            buff = self.first_buff

            # for html rewriting:
            # if charset is utf-8, use that, otherwise default to encode to ascii-compatible encoding
            # encoding only used for url rewriting, encoding back to bytes after rewriting
            if (
                rwinfo.charset == CharSets.utf
                and rwinfo.text_type == ContentRewriteTypes.html
            ):
                charset = CharSets.utf
            else:
                charset = CharSets.iso

            if buff:
                yield buff.encode(charset)

            decoder = codecs.getincrementaldecoder(charset)()

            while 1:
                buff = stream.read(BUFF_SIZE)
                if not buff:
                    break

                if self.align_to_line:
                    buff += stream.readline()

                try:
                    buff = decoder.decode(buff)
                except UnicodeDecodeError:
                    if charset == CharSets.utf:
                        rwinfo.charset = CharSets.iso
                        charset = rwinfo.charset
                        decoder = codecs.getincrementaldecoder(charset)()
                        buff = decoder.decode(buff)

                buff = self.rewrite(buff)

                yield buff.encode(charset)

            # For adding a tail/handling final buffer
            buff = self.final_read()

            # ensure decoder is marked as finished (final buffer already decoded)
            decoder.decode(b'', final=True)

            if buff:
                yield buff.encode(charset)

        finally:
            stream.close()


# ============================================================================
class RewriteInfo(object):
    TAG_REGEX = re.compile(b'^(\xef\xbb\xbf)?\s*\<')
    TAG_REGEX2 = re.compile(b'^.*<\w+[\s>]')
    JSON_REGEX = re.compile(
        b'^\s*[{[][{"]'
    )  # if it starts with this then highly likely not HTML

    JSONP_CONTAINS = ['callback=jQuery', 'callback=jsonp', '.json?']

    def __init__(self, record, content_rewriter, url_rewriter, cookie_rewriter=None):
        self.record = record

        self._content_stream = None
        self.is_content_rw = False
        self.is_chunked = False

        self.rewrite_types = content_rewriter.get_rewrite_types()

        self.text_type = None
        self.charset = None

        self.url_rewriter = url_rewriter

        if not cookie_rewriter:
            cookie_rw_class = content_rewriter.get_rewriter('cookie', self)
            if cookie_rw_class:
                cookie_rewriter = cookie_rw_class(url_rewriter)

        self.cookie_rewriter = cookie_rewriter

        if self.record:
            self.text_type, self.charset = self._fill_text_type_and_charset(
                content_rewriter
            )

    def _fill_text_type_and_charset(self, content_rewriter):
        content_type = self.record.http_headers.get_header('Content-Type', '')
        charset = None

        parts = content_type.split(';', 1)
        mime = parts[0]

        orig_text_type = self.rewrite_types.get(mime)

        text_type = self._resolve_text_type(orig_text_type)
        url = self.url_rewriter.wburl.url

        if text_type in ContentRewriteTypes.guess_text_type:
            text_type = None

        if text_type == ContentRewriteTypes.js:
            # determine if url contains strings that indicate jsonp
            if any(jsonp_string in url for jsonp_string in self.JSONP_CONTAINS):
                text_type = ContentRewriteTypes.json

        if (
            text_type and orig_text_type != text_type
        ) or text_type == ContentRewriteTypes.html:
            if url.endswith('.json'):
                buff = self.read_and_keep(56)
                if self.JSON_REGEX.match(buff) is not None:
                    return ContentRewriteTypes.json, charset
            # check if default content_type that needs to be set
            new_mime = content_rewriter.default_content_types.get(text_type)

            if new_mime and new_mime != mime:
                new_content_type = content_type.replace(mime, new_mime)
                self.record.http_headers.replace_header(
                    'Content-Type', new_content_type
                )

            # set charset
            if len(parts) == 2:
                parts = parts[1].lower().split('charset=', 1)
                if len(parts) == 2:
                    charset = parts[1].strip()

        return text_type, charset

    def _resolve_text_type(self, text_type):
        mod = self.url_rewriter.wburl.mod

        if mod in RewriteMods.js_worker_mods:
            return None

        if text_type == ContentRewriteTypes.css and mod == RewriteMods.javascript:
            text_type = ContentRewriteTypes.css

        is_js_or_css = mod in RewriteMods.css_and_js

        # if html or no-content type, allow resolving on js, css,
        # or other templates
        if text_type in ContentRewriteTypes.guess_text:
            if not is_js_or_css and mod not in RewriteMods.known_text_types:
                return None

        # if application/octet-stream binary, only resolve if in js/css content
        elif text_type in ContentRewriteTypes.guess_bin_or_html:
            if not is_js_or_css:
                return text_type

        else:
            return text_type

        buff = self.read_and_keep(128)

        # check if doesn't start with a tag, then likely not html
        if self.TAG_REGEX.match(buff):
            return ContentRewriteTypes.html
        # perform additional check to see if it has any html tags
        elif text_type == ContentRewriteTypes.guess_html and not is_js_or_css:
            if self.TAG_REGEX2.match(buff):
                return ContentRewriteTypes.html

        if not is_js_or_css:
            return text_type
        elif mod == RewriteMods.javascript:
            return ContentRewriteTypes.js
        else:
            return ContentRewriteTypes.css

        # text_type = 'js' if mod == 'js_' else 'css'

    @property
    def content_stream(self):
        if not self._content_stream:
            self._content_stream = self.record.content_stream()
            self.is_content_rw = True

        return self._content_stream

    def read_and_keep(self, size):
        buff = self.content_stream.read(size)
        self._content_stream = BufferedReader(self._content_stream, starting_data=buff)
        return buff

    def should_rw_content(self):
        if not self.text_type:
            return False

        if self.url_rewriter.wburl.mod == RewriteMods.identity:
            return False

        if self.url_rewriter.rewrite_opts.get('is_ajax'):
            if self.text_type in ContentRewriteTypes.html_or_js:
                return False

        elif self.text_type in ContentRewriteTypes.css_or_xml:
            if self.url_rewriter.wburl.mod == RewriteMods.binary:
                return False

        return True

    def is_url_rw(self):
        if self.url_rewriter.wburl.mod in RewriteMods.url_rw_excluded_mods:
            return False

        return True
