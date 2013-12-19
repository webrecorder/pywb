from refer_redirect import ReferRedirect
from wbrequestresponse import WbRequest, WbResponse

class ArchivalRequestRouter:
    def __init__(self, mappings, hostpaths=None):
        self.mappings = mappings
        self.fallback = ReferRedirect(hostpaths)

    def parse_request(self, env):
        request_uri = env['REQUEST_URI']

        for key, value in self.mappings.iteritems():
            if request_uri.startswith(key):
                return value, WbRequest.prefix_request(env, key, request_uri)

        return self.fallback, WbRequest(env)

    def handle_request(self, env):
        handler, wbrequest = self.parse_request(env)
        return handler.run(wbrequest)


