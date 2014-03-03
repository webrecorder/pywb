from pywb.cdx.query import CDXQuery
from pywb.cdx.cdxserver import create_cdx_server

from pywb.framework.archivalrouter import ArchivalRouter, Route
from pywb.framework.basehandlers import BaseHandler

from views import TextCapturesView


#=================================================================
class CDXHandler(BaseHandler):
    """
    Handler which passes wsgi request to cdx server and
    returns a text-based cdx response
    """
    def __init__(self, index_reader, view=None):
        self.index_reader = index_reader
        self.view = view if view else TextCapturesView()

    def __call__(self, wbrequest):
        params = CDXQuery.extract_params_from_wsgi_env(wbrequest.env)
        cdx_lines = self.index_reader.load_cdx(**params)

        return self.view.render_response(wbrequest, cdx_lines)

    def __str__(self):
        return 'CDX Handler: ' + str(self.index_reader)


#=================================================================
DEFAULT_RULES = 'pywb/rules.yaml'

#=================================================================
def create_cdx_server_app(config):
    """
    Create a cdx server config to be wrapped in a wsgi app
    Currently using single access point '/cdx'
    TODO: more complex example with multiple collections?
    """
    cdx_server = create_cdx_server(config, DEFAULT_RULES)
    port = config.get('port')
    routes = [Route('cdx', CDXHandler(cdx_server))]
    return ArchivalRouter(routes, port=port)
