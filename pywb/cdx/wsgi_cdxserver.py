from werkzeug.wrappers import BaseRequest, BaseResponse
from cdxserver import create_cdx_server
from pywb import get_test_dir

import logging
import os
import yaml
import pkg_resources

#=================================================================
CONFIG_FILE = 'config.yaml'

RULES_FILE = 'rules.yaml'

DEFAULT_PORT = 8080

#=================================================================
class CDXQueryRequest(BaseRequest):
    def __init__(self, environ):
        super(CDXQueryRequest, self).__init__(environ)

    @property
    def output(self):
        return self.args.get('output', 'text')
    @property
    def filter(self):
        return self.args.getlist('filter', [])
    @property
    def params(self):
        return dict(t if t[0] == 'filter' else (t[0], t[1][0])
                    for t in self.args.iterlists())

class WSGICDXServer(object):
    def __init__(self, paths, rules_file):
        self.cdxserver = create_cdx_server(paths, rules_file)

    def __call__(self, environ, start_response):
        request = CDXQueryRequest(environ)
        try:
            logging.debug('request.args=%s', request.params)
            result = self.cdxserver.load_cdx(**request.params)

            # TODO: select response type by "output" parameter
            response = PlainTextResponse(result)
            return response(environ, start_response)
        except Exception as exc:
            logging.error('load_cdx failed', exc_info=1)
            # TODO: error response should be different for each response
            # type
            start_response('400 Error', [('Content-Type', 'text/plain')])
            return [str(exc)]

class PlainTextResponse(BaseResponse):
    def __init__(self, cdxitr, status=200, content_type='text/plain'):
        super(PlainTextResponse, self).__init__(
            response=cdxitr,
            status=status, content_type=content_type)
        
# class JsonResponse(Response):
#     pass
# class MementoResponse(Response):
#     pass

def create_app(paths=None):
    logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                        level=logging.DEBUG)

    if not paths:
        paths = config or get_test_dir() + 'cdx/'

    return WSGICDXServer(paths, RULES_FILE)

if __name__ == "__main__":
    from optparse import OptionParser
    from werkzeug.serving import run_simple

    opt = OptionParser('%prog [OPTIONS]')
    opt.add_option('-p', '--port', type='int', default=None)

    options, args = opt.parse_args()

    configdata = pkg_resources.resource_string(__name__, CONFIG_FILE)
    config = yaml.load(configdata)

    port = options.port
    if port is None:
        port = (config and config.get('port')) or DEFAULT_PORT

    app = create_app()

    logging.debug('Starting CDX Server on port %s', port)
    try:
        run_simple('0.0.0.0', port, app, use_reloader=True, use_debugger=True)
    except KeyboardInterrupt as ex:
        pass
    logging.debug('Stopping CDX Server')
else:
    application = create_app()
