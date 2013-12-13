from wbrequestresponse import WbRequest, WbResponse
from refer_redirect import ReferRedirect
from archiveurl import archiveurl

class WBHandler:
    def run(self, wbrequest):
        wburl = archiveurl(wbrequest.wb_url)
        return WbResponse.text_response(repr(wburl))

class ArchivalParser:
    def __init__(self, mappings, hostpaths=None):
        self.mappings = mappings
        self.fallback = ReferRedirect(hostpaths)

    def find_handler(self, env):
        request_uri = env['REQUEST_URI']

        for key, value in self.mappings.iteritems():
            if request_uri.startswith(key):
                env['WB_URL'] = request_uri[len(key)-1:]
                env['WB_COLL'] = key[1:-1]
                #print "Found: " + str(value) + " for " + key
                return value

        return self.fallback

    def handle_request(self, env):
        handler = self.find_handler(env)
        return handler.run(WbRequest(env))

    def handle_exception(self, env, exc):
        return WbResponse.text_response('Error: ' + str(exc), status = '400 Bad Request')

    def handle_not_found(self, env):
        return WbResponse.text_response('Not Found: ' + env['REQUEST_URI'], status = '404 Not Found')



## ===========
parser = ArchivalParser({'/web/': WBHandler()}, hostpaths = ['http://localhost:9090/'])
## ===========


def application(env, start_response):
    response = None

    try:
        response = parser.handle_request(env)

    except Exception as e:
        last_exc = e
        import traceback
        traceback.print_exc()
        response = parser.handle_exception(env, e)

    if not response:
        response = parser.handle_not_found(env)

    return response(env, start_response)
