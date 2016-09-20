from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.loaders import extract_post_query, append_post_query

from io import BytesIO
import pprint
import re


#=================================================================
class WbRequest(object):
    """
    Represents the main pywb request object.

    Contains various info from wsgi env, add additional info
    about the request, such as coll, relative prefix,
    host prefix, absolute prefix.

    If a wburl and url rewriter classes are specified, the class
    also contains the url rewriter.

    """
    @staticmethod
    def make_host_prefix(env):
        try:
            host = env.get('HTTP_HOST')
            if not host:
                host = env['SERVER_NAME'] + ':' + env['SERVER_PORT']

            return env.get('wsgi.url_scheme', 'http') + '://' + host
        except KeyError:
            return ''

    def __init__(self, env,
                 request_uri=None,
                 rel_prefix='',
                 wb_url_str='/',
                 coll='',
                 host_prefix='',
                 use_abs_prefix=False,
                 wburl_class=None,
                 urlrewriter_class=None,
                 is_proxy=False,
                 cookie_scope=None,
                 rewrite_opts={},
                 user_metadata={},
                 ):

        self.env = env

        if request_uri:
            self.request_uri = request_uri
        else:
            self.request_uri = env.get('REL_REQUEST_URI')

        self.method = self.env.get('REQUEST_METHOD')

        self.coll = coll

        self.final_mod = ''

        if not host_prefix:
            host_prefix = self.make_host_prefix(env)

        self.host_prefix = host_prefix
        self.rel_prefix = rel_prefix

        if use_abs_prefix:
            self.wb_prefix = host_prefix + rel_prefix
        else:
            self.wb_prefix = rel_prefix

        if not wb_url_str:
            wb_url_str = '/'

        self.wb_url_str = wb_url_str

        # wb_url present and not root page
        if wb_url_str != '/' and wburl_class:
            self.wb_url = wburl_class(wb_url_str)
            self.urlrewriter = urlrewriter_class(self.wb_url,
                                                 self.wb_prefix,
                                                 host_prefix + rel_prefix,
                                                 rel_prefix,
                                                 env.get('SCRIPT_NAME', '/'),
                                                 cookie_scope,
                                                 rewrite_opts)

            self.urlrewriter.deprefix_url()
        # no wb_url, just store blank wb_url
        else:
            self.wb_url = None
            self.urlrewriter = None

        self.referrer = env.get('HTTP_REFERER')

        self.options = dict()
        self.options['is_ajax'] = self._is_ajax()
        self.options['is_proxy'] = is_proxy or env.get('pywb_proxy_magic')

        self.query_filter = []
        self.custom_params = {}
        self.user_metadata = user_metadata
        self.rewrite_opts = rewrite_opts

        # PERF
        env['X_PERF'] = {}

        if env.get('HTTP_X_PYWB_NOREDIRECT'):
            self.custom_params['noredir'] = True

        self._parse_extra()

    def _is_ajax(self):
        value = self.env.get('HTTP_X_REQUESTED_WITH')
        value = value or self.env.get('HTTP_X_PYWB_REQUESTED_WITH')
        if value and value.lower() == 'xmlhttprequest':
            return True

        return False

    RANGE_ARG_RX = re.compile('.*.googlevideo.com/videoplayback.*([&?]range=(\d+)-(\d+))')

    RANGE_HEADER = re.compile('bytes=(\d+)-(\d+)?')

    def extract_range(self):
        url = self.wb_url.url
        use_206 = False
        start = None
        end = None

        range_h = self.env.get('HTTP_RANGE')

        if range_h:
            m = self.RANGE_HEADER.match(range_h)
            if m:
                start = m.group(1)
                end = m.group(2)
                use_206 = True

        else:
            m = self.RANGE_ARG_RX.match(url)
            if m:
                start = m.group(2)
                end = m.group(3)
                url = url[:m.start(1)] + url[m.end(1):]
                use_206 = False

        if not start:
            return None

        start = int(start)
        self.custom_params['noredir'] = True

        if end:
            end = int(end)
        else:
            end = ''

        result = (url, start, end, use_206)
        return result

    def __repr__(self):
        varlist = vars(self)
        varstr = pprint.pformat(varlist)
        return varstr

    def _parse_extra(self):
        pass

    def extract_referrer_wburl_str(self):
        if not self.referrer:
            return None

        if not self.referrer.startswith(self.host_prefix + self.rel_prefix):
            return None

        wburl_str = self.referrer[len(self.host_prefix + self.rel_prefix):]
        return wburl_str

    def normalize_post_query(self):
        if self.method != 'POST':
            return

        if not self.wb_url:
            return

        mime = self.env.get('CONTENT_TYPE', '')
        length = self.env.get('CONTENT_LENGTH')
        stream = self.env['wsgi.input']

        buffered_stream = BytesIO()

        post_query = extract_post_query('POST', mime, length, stream,
                                        buffered_stream=buffered_stream,
                                        environ=self.env)

        if post_query:
            self.env['wsgi.input'] = buffered_stream
            self.wb_url.url = append_post_query(self.wb_url.url, post_query)


#=================================================================
class WbResponse(object):
    """
    Represnts a pywb wsgi response object.

    Holds a status_headers object and a response iter, to be
    returned to wsgi container.
    """
    def __init__(self, status_headers, value=[], **kwargs):
        self.status_headers = status_headers
        self.body = value
        self._init_derived(kwargs)

    def _init_derived(self, params):
        pass

    @staticmethod
    def text_stream(stream, content_type='text/plain; charset=utf-8', status='200 OK'):
        def encode(stream):
            for obj in stream:
                yield obj.encode('utf-8')

        if 'charset' not in content_type:
            content_type += '; charset=utf-8'

        return WbResponse.bin_stream(encode(stream), content_type, status)

    @staticmethod
    def bin_stream(stream, content_type, status='200 OK',
                    headers=None):
        def_headers = [('Content-Type', content_type)]
        if headers:
            def_headers += headers

        status_headers = StatusAndHeaders(status, def_headers)

        return WbResponse(status_headers, value=stream)

    @staticmethod
    def text_response(text, status='200 OK', content_type='text/plain; charset=utf-8'):
        encoded_text = text.encode('utf-8')
        status_headers = StatusAndHeaders(status,
                                          [('Content-Type', content_type),
                                           ('Content-Length', str(len(encoded_text)))])

        return WbResponse(status_headers, value=[encoded_text])

    @staticmethod
    def redir_response(location, status='302 Redirect', headers=None):
        redir_headers = [('Location', location), ('Content-Length', '0')]
        if headers:
            redir_headers += headers

        return WbResponse(StatusAndHeaders(status, redir_headers))

    def __call__(self, env, start_response):
        start_response(self.status_headers.statusline,
                       self.status_headers.headers)

        if env['REQUEST_METHOD'] == 'HEAD':
            if hasattr(self.body, 'close'):
                self.body.close()
            return []

        return self.body

    def add_range(self, *args):
        self.status_headers.add_range(*args)
        return self

    def __repr__(self):
        return str(vars(self))
