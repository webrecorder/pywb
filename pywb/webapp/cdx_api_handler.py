from pywb.cdx.cdxserver import create_cdx_server

from pywb.utils.wbexception import NotFoundException
from pywb.framework.basehandlers import BaseHandler
from pywb.framework.wbrequestresponse import WbResponse

from pywb.webapp.query_handler import QueryHandler

from six.moves.urllib.parse import parse_qs
import json
import six


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

        try:
            cdx_iter = self.index_handler.load_cdx(wbrequest, params)
        except NotFoundException:
            msg = 'No Captures found for: ' + params.get('url')
            if params.get('output') == 'json':
                msg = json.dumps(dict(error=msg))
                content_type='application/json'
            else:
                content_type='text/plain'

            return WbResponse.text_response(msg, content_type=content_type,
                                            status='404 Not Found')

        return WbResponse.text_stream(cdx_iter,
                                      content_type='text/plain')

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
        for name, val in six.iteritems(params):
            if name != 'filter':
                params[name] = val[0]

        if 'output' not in params:
            params['output'] = 'text'
        elif params['output'] not in ('text', 'json'):
            params['output'] = 'text'

        return params
