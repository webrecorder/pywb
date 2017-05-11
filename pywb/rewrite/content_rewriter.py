from io import BytesIO

from contextlib import closing

from warcio.bufferedreaders import BufferedReader
from warcio.utils import to_native_str

import re
import webencodings

from pywb.webagg.utils import StreamIter, BUFF_SIZE
from pywb.rewrite.cookie_rewriter import ExactPathCookieRewriter

from pywb.utils.loaders import load_yaml_config


# ============================================================================
class BaseContentRewriter(object):
    CHARSET_REGEX = re.compile(b'<meta[^>]*?[\s;"\']charset\s*=[\s"\']*([^\s"\'/>]*)')

    def __init__(self, rules_file, replay_mod=''):
        self.rules = []
        self.load_rules(rules_file)
        self.replay_mod = replay_mod
        #for rw in self.known_rewriters:
        #    self.all_rewriters[rw.name] = rw

    def add_rewriter(self, rw):
        self.all_rewriters[rw.name] = rw

    def get_rewriter(self, url, text_type):
        return self.all_rewriters.get(text_type)

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

        return rule

    def get_rule(self, cdx):
        urlkey = to_native_str(cdx['urlkey'])

        for rule in self.rules:
            if any((urlkey.startswith(prefix) for prefix in rule['url_prefix'])):
                return rule

        return {}

    def get_rw_class(self, rule, text_type, rwinfo):
        if text_type == 'js' and not rwinfo.is_url_rw():
            text_type = 'js-proxy'

        rw_type = rule.get(text_type, text_type)
        rw_class = self.all_rewriters.get(rw_type)

        return rw_type, rw_class

    def create_rewriter(self, text_type, rule, rwinfo, cdx, head_insert_func=None):
        rw_type, rw_class = self.get_rw_class(rule, text_type, rwinfo)

        if rw_type in ('js', 'js_proxy'):
            extra_rules = []
            if 'js_regex_func' in rule:
                extra_rules = rule['js_regex_func'](rwinfo.url_rewriter)

            return rw_class(rwinfo.url_rewriter, extra_rules)

        elif rw_type != 'html':
            return rw_class(rwinfo.url_rewriter)

        # HTML Rewriter
        head_insert_str = self.get_head_insert(rwinfo, rule, head_insert_func, cdx)

        js_rewriter = self.create_rewriter('js', rule, rwinfo, cdx)
        css_rewriter = self.create_rewriter('css', rule, rwinfo, cdx)

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
        if rwinfo.is_url_rw():
            header_rw_name = 'header'
        else:
            header_rw_name = 'header-proxy'

        header_rw_class = self.all_rewriters.get(header_rw_name)
        rwinfo.rw_http_headers = header_rw_class(rwinfo)()

    def __call__(self, record, url_rewriter, cookie_rewriter,
                 head_insert_func=None,
                 cdx=None):

        rwinfo = RewriteInfo(record, self.get_rewrite_types(), url_rewriter, cookie_rewriter)

        self.rewrite_headers(rwinfo)

        content_rewriter = None
        if rwinfo.is_content_rw():
            rule = self.get_rule(cdx)
            content_rewriter = self.create_rewriter(rwinfo.text_type, rule, rwinfo, cdx, head_insert_func)

        if content_rewriter:
            gen = content_rewriter(rwinfo)
        else:
            gen = StreamIter(rwinfo.content_stream)

        return rwinfo.rw_http_headers, gen, (content_rewriter != None)

    def init_js_regexs(self, regexs):
        raise NotImplemented()

    def get_rewrite_types(self):
        raise NotImplemented()


# ============================================================================
class StreamingRewriter(object):
    def __init__(self):
        self.align_to_line = True

    def __call__(self, rwinfo):
        gen = self.rewrite_text_stream_to_gen(rwinfo.content_stream,
                                              rewrite_func=self.rewrite,
                                              final_read_func=self.close,
                                              align_to_line=self.align_to_line)

        return gen

    def rewrite(self, string):
        return string

    def close(self):
        return ''

    def rewrite_text_stream_to_gen(cls, stream,
                                   rewrite_func,
                                   final_read_func,
                                   align_to_line):
        """
        Convert stream to generator using applying rewriting func
        to each portion of the stream.
        Align to line boundaries if needed.
        """
        try:
            buff = ''

            while True:
                buff = stream.read(BUFF_SIZE)
                if not buff:
                    break

                if align_to_line:
                    buff += stream.readline()

                buff = rewrite_func(buff.decode('iso-8859-1'))
                yield buff.encode('iso-8859-1')

            # For adding a tail/handling final buffer
            buff = final_read_func()
            if buff:
                yield buff.encode('iso-8859-1')

        finally:
            stream.close()


# ============================================================================
class RewriteInfo(object):
    TAG_REGEX = re.compile(b'^\s*\<')

    def __init__(self, record, rewrite_types, url_rewriter, cookie_rewriter):
        self.record = record

        self.rw_http_headers = record.http_headers
        self.content_stream = record.content_stream()

        self.rewrite_types = rewrite_types

        self.text_type = None
        self.charset = None

        self.url_rewriter = url_rewriter

        if not cookie_rewriter:
            cookie_rewriter = ExactPathCookieRewriter(url_rewriter)

        self.cookie_rewriter = cookie_rewriter

        self._fill_text_type_and_charset()
        self._resolve_text_type()

    def _fill_text_type_and_charset(self):
        content_type = self.record.http_headers.get_header('Content-Type')
        if not content_type:
            return

        parts = content_type.split(';', 1)
        mime = parts[0]

        self.text_type = self.rewrite_types.get(mime)
        if not self.text_type:
            return

        if len(parts) == 2:
            parts = parts[1].lower().split('charset=', 1)
            if len(parts) == 2:
                self.charset = parts[1].strip()

    def _resolve_text_type(self):
        mod = self.url_rewriter.wburl.mod

        if self.text_type == 'css' and mod == 'js_':
            self.text_type = 'css'

        # only attempt to resolve between html and other text types
        if self.text_type != 'html':
            return

        if mod != 'js_' and mod != 'cs_':
            return

        buff = self.read_and_keep(128)

        # check if starts with a tag, then likely html
        if self.TAG_REGEX.match(buff):
            self.text_type = 'html'

    def read_and_keep(self, size):
        buff = self.content_stream.read(size)
        self.content_stream = BufferedReader(self.content_stream, starting_data=buff)
        return buff

    def is_content_rw(self):
        if not self.url_rewriter.prefix:
            return False

        if self.url_rewriter.wburl.mod == 'id_':
            return False

        if self.text_type == 'html':
            if self.url_rewriter.rewrite_opts.get('is_ajax'):
                return False

        elif self.text_type == 'plain':
            if self.url_rewriter.wburl.mod not in ('js_', 'cs_'):
                return False

        elif not self.text_type:
            return False

        return True

    def is_url_rw(self):
        if not self.url_rewriter:
            return False

        if self.url_rewriter.wburl.mod == 'id_':
            return False

        return True


