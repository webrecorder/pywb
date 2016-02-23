from pywb.utils.canonicalize import UrlCanonicalizer
from pywb.utils.wbexception import NotFoundException

from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.archivalrouter import ArchivalRouter, Route
from pywb.framework.wbrequestresponse import WbResponse

BLOCK = '["block"]'
ALLOW = '["allow"]'
RESPONSE_TYPE = 'application/json'

NOT_FOUND = 'Please specify a url to check for access'


#=================================================================
class PermsHandler(WbUrlHandler):

    def __init__(self, perms_policy, url_canon):
        self.perms_policy = perms_policy
        self.url_canon = url_canon

    def __call__(self, wbrequest):
        perms_checker = self.perms_policy(wbrequest)

        if wbrequest.wb_url:
            return self.check_single_url(wbrequest, perms_checker)

#        elif wbrequest.env['REQUEST_METHOD'] == 'POST':
#            return self.check_bulk(wbrequest, perms_checker)

        else:
            raise NotFoundException(NOT_FOUND)

    def check_single_url(self, wbrequest, perms_checker):
        urlkey = self.url_canon(wbrequest.wb_url.url)
        urlkey = urlkey.encode('utf-8')

        if not perms_checker.allow_url_lookup(urlkey):
            response_text = BLOCK
        else:
            response_text = ALLOW

        #TODO: other types of checking
        return WbResponse.text_response(response_text,
                                        content_type=RESPONSE_TYPE)
#TODO
#    def check_bulk_urls(self, wbrequest, perms_checker):
#        pass
#


#=================================================================
def create_perms_checker_app(config):
    """
    Create permissions checker standalone app
    Running under the '/check-access' route
    """
    port = config.get('port')

    perms_policy = config.get('perms_policy')

    canonicalizer = UrlCanonicalizer(config.get('surt_ordered', True))

    handler = PermsHandler(perms_policy, canonicalizer)
    routes = [Route('check-access', handler)]

    return ArchivalRouter(routes, port=port)
