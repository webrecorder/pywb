from wbarchivalurl import ArchivalUrl
#WB Request and Response

class WbRequest:
    """
    >>> WbRequest.parse({'REQUEST_URI': '/save/_embed/example.com/?a=b'})
    {'wb_url': ('latest_replay', '', '', 'http://_embed/example.com/?a=b', '/http://_embed/example.com/?a=b'), 'coll': 'save', 'wb_prefix': '/save/', 'request_uri': '/save/_embed/example.com/?a=b'}

    >>> WbRequest.parse({'REQUEST_URI': '/2345/20101024101112im_/example.com/?b=c'})
    {'wb_url': ('replay', '20101024101112', 'im_', 'http://example.com/?b=c', '/20101024101112im_/http://example.com/?b=c'), 'coll': '2345', 'wb_prefix': '/2345/', 'request_uri': '/2345/20101024101112im_/example.com/?b=c'}

    >>> WbRequest.parse({'REQUEST_URI': '/2010/example.com'})
    {'wb_url': ('latest_replay', '', '', 'http://example.com', '/http://example.com'), 'coll': '2010', 'wb_prefix': '/2010/', 'request_uri': '/2010/example.com'}

    >>> WbRequest.parse({'REQUEST_URI': '../example.com'})
    {'wb_url': ('latest_replay', '', '', 'http://example.com', '/http://example.com'), 'coll': '', 'wb_prefix': '/', 'request_uri': '../example.com'}
    """

    @staticmethod
    def parse(env, request_uri = ''):
        if not request_uri:
            request_uri = env.get('REQUEST_URI')

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

        return WbRequest(env, request_uri, wb_prefix, wb_url, coll)

    def __init__(self, env, request_uri, wb_prefix, wb_url, coll):
        self.env = env

        self.request_uri = request_uri if request_uri else env.get('REQUEST_URI')

        self.wb_prefix = wb_prefix

        self.wb_url = ArchivalUrl(wb_url)

        self.coll = coll

        self.referrer = env.get('HTTP_REFERER')

        self.is_ajax = self._is_ajax()


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
    {'status': '200 OK', 'body': ['Test'], 'headersList': [('Content-Type', 'text/plain')]}

    >>> WbResponse.text_stream(['Test', 'Another'], '404')
    {'status': '404', 'body': ['Test', 'Another'], 'headersList': [('Content-Type', 'text/plain')]}

    >>> WbResponse.redir_response('http://example.com/otherfile')
    {'status': '302 Redirect', 'body': [], 'headersList': [('Location', 'http://example.com/otherfile')]}

    """

    def __init__(self, status, value = [], headersList = []):
        self.status = status
        self.body = value
        self.headersList = headersList

    @staticmethod
    def text_stream(text, status = '200 OK'):
        return WbResponse(status, value = text, headersList = [('Content-Type', 'text/plain')])

    @staticmethod
    def text_response(text, status = '200 OK'):
        return WbResponse(status, value = [text], headersList = [('Content-Type', 'text/plain')])

    @staticmethod
    def redir_response(location, status = '302 Redirect'):
        return WbResponse(status, headersList = [('Location', location)])

    def get_header(self, name):
        name_upp = name.upper()
        for value in self.headersList:
            if (value[0].upper() == name_upp):
                return value[1]

    def __call__(self, env, start_response):
        #headersList = []
        #for key, value in self.headers.iteritems():
        #    headersList.append((key, value))

        start_response(self.status, self.headersList)

        if hasattr(self.body, '__iter__'):
            return self.body
        else:
            return [str(self.body)]


    def __repr__(self):
        return str(vars(self))



if __name__ == "__main__":
    import doctest
    doctest.testmod()

