#WB Request and Response

class WbRequest:
    """
    >>> WbRequest.prefix_request({'REQUEST_URI': '/save/_embed/example.com/?a=b'}, '/save/')
    WbRequest(env, '/_embed/example.com/?a=b', 'save')
    """

    def __init__(self, env, request_uri = '', wb_url = '', coll = ''):
        self.env = env

 #       if len(wb_url) == 0:
 #           wb_url = request_uri

        setattr(self, 'wb_url', wb_url)
        setattr(self, 'coll', coll)

        setattr(self, 'request_uri', request_uri)
        setattr(self, 'referrer', env.get('HTTP_REFERER'))


    @staticmethod
    def prefix_request(env, prefix, request_uri = ''):
        if not request_uri:
            request_uri = env.get('REQUEST_URI')
        return WbRequest(env, request_uri, request_uri[len(prefix)-1:], coll = prefix[1:-1])

    def __repr__(self):
        return "WbRequest(env, '" + (self.wb_url) + "', '" + (self.coll) + "')"


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

