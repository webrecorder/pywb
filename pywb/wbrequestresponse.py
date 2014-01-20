from wbarchivalurl import ArchivalUrl
import utils

import pprint
#WB Request and Response

class WbRequest:
    """
    >>> WbRequest.from_uri('/save/_embed/example.com/?a=b')
    {'wb_url': ('latest_replay', '', '', 'http://_embed/example.com/?a=b', '/http://_embed/example.com/?a=b'), 'coll': 'save', 'wb_prefix': '/save/', 'request_uri': '/save/_embed/example.com/?a=b'}

    >>> WbRequest.from_uri('/2345/20101024101112im_/example.com/?b=c')
    {'wb_url': ('replay', '20101024101112', 'im_', 'http://example.com/?b=c', '/20101024101112im_/http://example.com/?b=c'), 'coll': '2345', 'wb_prefix': '/2345/', 'request_uri': '/2345/20101024101112im_/example.com/?b=c'}

    >>> WbRequest.from_uri('/2010/example.com')
    {'wb_url': ('latest_replay', '', '', 'http://example.com', '/http://example.com'), 'coll': '2010', 'wb_prefix': '/2010/', 'request_uri': '/2010/example.com'}

    >>> WbRequest.from_uri('../example.com')
    {'wb_url': ('latest_replay', '', '', 'http://example.com', '/http://example.com'), 'coll': '', 'wb_prefix': '/', 'request_uri': '../example.com'}

    # Abs path
    >>> WbRequest.from_uri('/2010/example.com', {'wsgi.url_scheme': 'https', 'HTTP_HOST': 'localhost:8080'}, use_abs_prefix = True)
    {'wb_url': ('latest_replay', '', '', 'http://example.com', '/http://example.com'), 'coll': '2010', 'wb_prefix': 'https://localhost:8080/2010/', 'request_uri': '/2010/example.com'}

    # No Scheme, so stick to relative
    >>> WbRequest.from_uri('/2010/example.com', {'HTTP_HOST': 'localhost:8080'}, use_abs_prefix = True)
    {'wb_url': ('latest_replay', '', '', 'http://example.com', '/http://example.com'), 'coll': '2010', 'wb_prefix': '/2010/', 'request_uri': '/2010/example.com'}

    """

    @staticmethod
    def from_uri(request_uri, env = {}, use_abs_prefix = False):
        if not request_uri:
            request_uri = env.get('REL_REQUEST_URI')

        parts = request_uri.split('/', 2)

        # Has coll prefix
        if len(parts) == 3:
            wb_prefix = '/' + parts[1] + '/'
            wb_url = '/' + parts[2]
            coll = parts[1]
        # No Coll Prefix
        elif len(parts) == 2:
            wb_prefix = '/'
            wb_url = '/' + parts[1]
            coll = ''
        else:
            wb_prefix = '/'
            wb_url = parts[0]
            coll = ''

        return WbRequest(env, request_uri, wb_prefix, wb_url, coll, use_abs_prefix)


    @staticmethod
    def makeAbsPrefix(env, rel_prefix):
        try:
            return env['wsgi.url_scheme'] + '://' + env['HTTP_HOST'] + rel_prefix
        except KeyError:
            return rel_prefix


    def __init__(self, env, request_uri, wb_prefix, wb_url, coll, use_abs_prefix = False, archivalurl_class = ArchivalUrl):
        self.env = env

        self.request_uri = request_uri if request_uri else env.get('REL_REQUEST_URI')

        self.wb_prefix = wb_prefix if not use_abs_prefix else WbRequest.makeAbsPrefix(env, wb_prefix)

        self.wb_url = archivalurl_class(wb_url)

        self.coll = coll

        self.referrer = env.get('HTTP_REFERER')

        self.is_ajax = self._is_ajax()

        self.customParams = {}

        self.queryFilter = []

        # PERF
        env['X_PERF'] = {}


    def _is_ajax(self):
        value = self.env.get('HTTP_X_REQUESTED_WITH')
        if not value:
            return False

        if value.lower() == 'xmlhttprequest':
            return True

        if self.referrer and ('ajaxpipe' in self.env.get('QUERY_STRING')):
            return True
        return False


    def __repr__(self):
        #return "WbRequest(env, '" + (self.wb_url) + "', '" + (self.coll) + "')"
        #return str(vars(self))
        varlist = vars(self)
        return str({k: varlist[k] for k in ('request_uri', 'wb_prefix', 'wb_url', 'coll')})


class WbResponse:
    """
    >>> WbResponse.text_response('Test')
    {'body': ['Test'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [('Content-Type', 'text/plain')])}

    >>> WbResponse.text_stream(['Test', 'Another'], '404')
    {'body': ['Test', 'Another'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '404', headers = [('Content-Type', 'text/plain')])}

    >>> WbResponse.redir_response('http://example.com/otherfile')
    {'body': [], 'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect', headers = [('Location', 'http://example.com/otherfile')])}
    """

    def __init__(self, status_headers, value = []):
        self.status_headers = status_headers
        self.body = value

    @staticmethod
    def text_stream(text, status = '200 OK', content_type = 'text/plain'):
        return WbResponse(StatusAndHeaders(status, [('Content-Type', content_type)]), value = text)

    @staticmethod
    def text_response(text, status = '200 OK', content_type = 'text/plain'):
        return WbResponse(StatusAndHeaders(status, [('Content-Type', content_type)]), value = [text])

    @staticmethod
    def redir_response(location, status = '302 Redirect'):
        return WbResponse(StatusAndHeaders(status, [('Location', location)]))

    @staticmethod
    def stream_response(status_headers, stream, proc = None, firstBuff = None):
        def streamGen():
            try:
                buff = firstBuff if firstBuff else stream.read()
                while buff:
                    if proc:
                        buff = proc(buff)
                    yield buff
                    buff = stream.read()
            finally:
                stream.close()

        response = WbResponse(status_headers, value = streamGen())
        response._stream = stream
        return response

    def __call__(self, env, start_response):

        # PERF
        perfstats = env.get('X_PERF')
        if perfstats:
            self.status_headers.headers.append(('X-Archive-Perf-Stats', str(perfstats)))


        start_response(self.status_headers.statusline, self.status_headers.headers)

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


#=================================================================
class StatusAndHeaders:
    def __init__(self, statusline, headers, protocol = ''):
        self.statusline = statusline
        self.headers = headers
        self.protocol = protocol

    def getHeader(self, name):
        nameLower = name.lower()
        for value in self.headers:
            if (value[0].lower() == nameLower):
                return value[1]

        return None

    def __repr__(self):
        return "StatusAndHeaders(protocol = '{0}', statusline = '{1}', headers = {2})".format(self.protocol, self.statusline, pprint.pformat(self.headers, indent = 2))
        #return pprint.pformat(self.__dict__)

    def __eq__(self, other):
        return self.statusline == other.statusline and self.headers == other.headers and self.protocol == other.protocol


if __name__ == "__main__":
    import doctest
    doctest.testmod()

