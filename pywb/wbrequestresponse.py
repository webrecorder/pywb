
#WB Request and Response

class WbRequest:
    def __init__(self, env):
        self.env = env
        self.wb_url = env.get('WB_URL')
        self.coll = env.get('WB_COLL')

        setattr(self, 'request_uri', env.get('REQUEST_URI'))
        setattr(self, 'referrer', env.get('HTTP_REFERER'))

    def __repr__(self):
        return self.coll + " " + self.wb_url


class WbResponse:
    def __init__(self, status, value = [], headersList = []):
        self.status = status
        self.body = value
        self.headersList = headersList

    @staticmethod
    def text_response(text, status = '200 OK'):
        return WbResponse(status, value = [text], headersList = [('Content-Type', 'text/plain')])

    @staticmethod
    def redir_response(location):
        return WbResponse('302 Redirect', headersList = [('Location', location)])

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
        return self.body





