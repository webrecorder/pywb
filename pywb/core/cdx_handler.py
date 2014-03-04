from pywb.cdx.cdxserver import create_cdx_server

from pywb.framework.archivalrouter import ArchivalRouter, Route
from pywb.framework.basehandlers import BaseHandler

from indexreader import IndexReader
from views import TextCapturesView

from urlparse import parse_qs


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
        params = self.extract_params_from_wsgi_env(wbrequest.env)

        cdx_iter = self.index_reader.load_cdx(wbrequest, params)

        return self.view.render_response(wbrequest, cdx_iter)

    def __str__(self):
        return 'CDX Handler: ' + str(self.index_reader)

    @staticmethod
    def extract_params_from_wsgi_env(env):
        """ utility function to extract params and create a CDXQuery
        from a WSGI environment dictionary
        """
        params = parse_qs(env['QUERY_STRING'])

        # parse_qs produces arrays for single values
        # cdx processing expects singleton params for all params,
        # except filters, so convert here
        # use first value of the list
        for name, val in params.iteritems():
            if name != 'filter':
                params[name] = val[0]

        if not 'output' in params:
            params['output'] = 'text'

        return params


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
    perms_policy = config.get('perms_policy')
    cdx_server = IndexReader(cdx_server, perms_policy)

    port = config.get('port')
    routes = [Route('cdx', CDXHandler(cdx_server))]
    return ArchivalRouter(routes, port=port)
