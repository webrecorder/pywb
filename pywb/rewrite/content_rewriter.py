from io import BytesIO

from contextlib import closing

from warcio.bufferedreaders import BufferedReader, ChunkedDataReader
from warcio.utils import to_native_str

import re
import webencodings
import tempfile
import json

from pywb.utils.io import StreamIter, BUFF_SIZE

from pywb.utils.loaders import load_yaml_config, load_py_name


# ============================================================================
class BaseContentRewriter(object):
    CHARSET_REGEX = re.compile(b'<meta[^>]*?[\s;"\']charset\s*=[\s"\']*([^\s"\'/>]*)')

    def __init__(self, rules_file, replay_mod=''):
        self.rules = []
        self.all_rewriters = []
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
        if text_type == 'json' and 'js_regex_func' in rule:
            text_type = 'js-proxy'

        if text_type == 'js' and not rwinfo.is_url_rw():
            text_type = 'js-proxy'

        rw_type = rule.get(text_type, text_type)
        rw_class = self.get_rewriter(rw_type, rwinfo)

        mixin = rule.get('mixin')
        if mixin:
            mixin_params = rule.get('mixin_params', {})
            rw_class = type('custom_js_rewriter', (mixin, rw_class), mixin_params)

        return rw_type, rw_class

    def create_rewriter(self, text_type, rule, rwinfo, cdx, head_insert_func=None):
        rw_type, rw_class = self.get_rw_class(rule, text_type, rwinfo)

        if rw_type in ('js', 'js-proxy'):
            extra_rules = []
            if self.has_custom_rules(rule, cdx):
                extra_rules = rule['js_regex_func'](rwinfo.url_rewriter)

            # if js-proxy and no rules, default to none
            # js rewriting in proxy only if extra rules apply
            if rw_type == 'js-proxy' and not extra_rules:
                return None

            return rw_class(rwinfo.url_rewriter, extra_rules)

        elif rw_type != 'html':
            return rw_class(rwinfo.url_rewriter)

        # HTML Rewriter
        head_insert_str = self.get_head_insert(rwinfo, rule, head_insert_func, cdx)

        js_rewriter = self.create_rewriter('js', rule, rwinfo, cdx)
        css_rewriter = self.create_rewriter('css', rule, rwinfo, cdx)

        # if no js rewriter, then do banner insert only
        if not js_rewriter:
            rw_class = self.get_rewriter('html-banner-only', rwinfo)

        rw = rw_class(rwinfo.url_rewriter,
                      js_rewriter=js_rewriter,
                      css_rewriter=css_rewriter,
                      head_insert=head_insert_str,
                      url=cdx['url'],
                      defmod=self.replay_mod,
                      parse_comments=rule.get('parse_comments', False))

        return rw

    def get_head_insert(self, rwinfo, rule, head_insert_func, cdx):
        head_insert_str = ''
        charset = rwinfo.charset

        # if no charset set, attempt to extract from first 1024
        if not charset:
            first_buff = rwinfo.read_and_keep(1024)
            charset = self.extract_html_charset(first_buff)

        if head_insert_func:
            head_insert_orig = head_insert_func(rule, cdx)

            if charset:
                try:
                    head_insert_str = webencodings.encode(head_insert_orig, charset)
                except:
                    pass

            if not head_insert_str:
                charset = 'utf-8'
                head_insert_str = head_insert_orig.encode(charset)

            head_insert_str = head_insert_str.decode('iso-8859-1')

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

    def __call__(self, record, url_rewriter, cookie_rewriter,
                 head_insert_func=None,
                 cdx=None):

        rwinfo = RewriteInfo(record, self, url_rewriter, cookie_rewriter)
        content_rewriter = None

        url_rewriter.rewrite_opts['cdx'] = cdx

        rule = self.get_rule(cdx)

        if rule.get('mixin') and not rwinfo.text_type:
            rwinfo.text_type = rule.get('mixin_type', 'json')

        if rwinfo.should_rw_content():
            content_rewriter = self.create_rewriter(rwinfo.text_type, rule, rwinfo, cdx, head_insert_func)

        gen = None

        if content_rewriter:
            gen = content_rewriter(rwinfo)
        elif rwinfo.is_content_rw:
            gen = StreamIter(rwinfo.content_stream)

        rw_http_headers = self.rewrite_headers(rwinfo)

        if not gen:
            # if not rewriting content, still need to dechunk
            # to conform to WSGI spec
            if rwinfo.is_chunked:
                stream = ChunkedDataReader(rwinfo.record.raw_stream,
                                           decomp_type=None)
            else:
                stream = rwinfo.record.raw_stream

            gen = StreamIter(stream)

        return rw_http_headers, gen, (content_rewriter != None)

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
            except:
                pass

        return {}

    def _get_adaptive_metadata(self, rwinfo):
        metadata = self._get_record_metadata(rwinfo) if rwinfo else {}
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
        return self.rewrite_text_stream_to_gen(rwinfo.content_stream)

    def rewrite(self, string):
        return string

    def rewrite_complete(self, string, **kwargs):
        return self.first_buff + self.rewrite(string) + self.final_read()

    def final_read(self):
        return ''

    def rewrite_text_stream_to_gen(self, stream):
        """
        Convert stream to generator using applying rewriting func
        to each portion of the stream.
        Align to line boundaries if needed.
        """
        try:
            buff = self.first_buff

            if buff:
                yield buff.encode('iso-8859-1')

            while True:
                buff = stream.read(BUFF_SIZE)
                if not buff:
                    break

                if self.align_to_line:
                    buff += stream.readline()

                buff = self.rewrite(buff.decode('iso-8859-1'))
                yield buff.encode('iso-8859-1')

            # For adding a tail/handling final buffer
            buff = self.final_read()
            if buff:
                yield buff.encode('iso-8859-1')

        finally:
            stream.close()


# ============================================================================
class RewriteInfo(object):
    TAG_REGEX = re.compile(b'^\s*\<')

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
            self.text_type, self.charset = self._fill_text_type_and_charset(content_rewriter)

    def _fill_text_type_and_charset(self, content_rewriter):
        content_type = self.record.http_headers.get_header('Content-Type', '')
        charset = None

        parts = content_type.split(';', 1)
        mime = parts[0]

        orig_text_type = self.rewrite_types.get(mime)

        text_type = self._resolve_text_type(orig_text_type)

        if text_type in ('guess-text', 'guess-bin'):
            text_type = None

        if text_type == 'js':
            if 'callback=jQuery' in self.url_rewriter.wburl.url or '.json?' in self.url_rewriter.wburl.url:
                text_type = 'json'

        if (text_type and orig_text_type != text_type) or text_type == 'html':
            # check if default content_type that needs to be set
            new_mime = content_rewriter.default_content_types.get(text_type)

            if new_mime and new_mime != mime:
                new_content_type = content_type.replace(mime, new_mime)
                self.record.http_headers.replace_header('Content-Type', new_content_type)

            # set charset
            if len(parts) == 2:
                parts = parts[1].lower().split('charset=', 1)
                if len(parts) == 2:
                    charset = parts[1].strip()

        return text_type, charset

    def _resolve_text_type(self, text_type):
        mod = self.url_rewriter.wburl.mod

        if text_type == 'css' and mod == 'js_':
            text_type = 'css'

        is_js_or_css = mod in ('js_', 'cs_')

        # if html or no-content type, allow resolving on js, css,
        # or other templates
        if text_type == 'guess-text':
            if not is_js_or_css and not mod in ('if_', 'mp_', ''):
                return None

        # if application/octet-stream binary, only resolve if in js/css content
        elif text_type in ('guess-bin', 'html'):
            if not is_js_or_css:
                return text_type

        else:
            return text_type

        buff = self.read_and_keep(128)

        # check if doesn't start with a tag, then likely not html
        if self.TAG_REGEX.match(buff):
            return 'html'

        if not is_js_or_css:
            return text_type
        elif mod == 'js_':
            return 'js'
        else:
            return 'css'

        #text_type = 'js' if mod == 'js_' else 'css'

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

        if self.url_rewriter.wburl.mod == 'id_':
            return False

        if self.url_rewriter.rewrite_opts.get('is_ajax'):
            if self.text_type in ('html', 'js'):
                return False

        elif self.text_type == 'css' or self.text_type == 'xml':
            if self.url_rewriter.wburl.mod == 'bn_':
                return False

        return True

    def is_url_rw(self):
        if self.url_rewriter.wburl.mod in ('id_', 'bn_'):
            return False

        return True

