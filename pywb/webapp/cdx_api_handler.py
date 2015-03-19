from pywb.cdx.cdxserver import create_cdx_server

from pywb.framework.basehandlers import BaseHandler
from pywb.framework.wbrequestresponse import WbResponse

from query_handler import QueryHandler

from urlparse import parse_qs


#=================================================================
class CDXAPIHandler(BaseHandler):
    """
    Handler which passes wsgi request to cdx server and
    returns a text-based cdx api
    """
    def __init__(self, index_handler):
        self.index_handler = index_handler

    def __call__(self, wbrequest):
        params = self.extract_params_from_wsgi_env(wbrequest.env)

        cdx_iter = self.index_handler.load_cdx(wbrequest, params)

        return WbResponse.text_stream(cdx_iter)

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

        if 'output' not in params:
            params['output'] = 'text'
        elif params['output'] not in ('text', 'json'):
            params['output'] = 'text'

        return params
