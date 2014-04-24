from pywb.utils.statusandheaders import StatusAndHeaders

import pprint


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
                 is_proxy=False):

        self.env = env

        if request_uri:
            self.request_uri = request_uri
        else:
            self.request_uri = env.get('REL_REQUEST_URI')

        self.coll = coll

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
            self.urlrewriter = urlrewriter_class(self.wb_url, self.wb_prefix,
                                                 host_prefix + rel_prefix)
        else:
        # no wb_url, just store blank wb_url
            self.wb_url = None
            self.urlrewriter = None

        self.referrer = env.get('HTTP_REFERER')

        self.is_ajax = self._is_ajax()

        self.query_filter = []

        self.is_proxy = is_proxy

        self.custom_params = {}

        # PERF
        env['X_PERF'] = {}

        self._parse_extra()

    def _is_ajax(self):
        value = self.env.get('HTTP_X_REQUESTED_WITH')
        if value and value.lower() == 'xmlhttprequest':
            return True

        #if self.referrer and ('ajaxpipe' in self.env.get('QUERY_STRING')):
        #    return True

        return False

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
    def text_stream(stream, status='200 OK', content_type='text/plain'):
        status_headers = StatusAndHeaders(status,
                                          [('Content-Type', content_type)])

        return WbResponse(status_headers, value=stream)

    @staticmethod
    def text_response(text, status='200 OK', content_type='text/plain'):
        status_headers = StatusAndHeaders(status,
                                          [('Content-Type', content_type)])

        return WbResponse(status_headers, value=[text])

    @staticmethod
    def redir_response(location, status='302 Redirect'):
        return WbResponse(StatusAndHeaders(status,
                                           [('Location', location)]))

    def __call__(self, env, start_response):

        # PERF
        perfstats = env.get('X_PERF')
        if perfstats:
            self.status_headers.headers.append(('X-Archive-Perf-Stats',
                                                str(perfstats)))

        start_response(self.status_headers.statusline,
                       self.status_headers.headers)

        if env['REQUEST_METHOD'] == 'HEAD':
            if hasattr(self.body, 'close'):
                self.body.close()
            return []

        if hasattr(self.body, '__iter__'):
            return self.body
        else:
            return [str(self.body)]

    def __repr__(self):
        return str(vars(self))
