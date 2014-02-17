from cdxserver import create_cdx_server, extract_params_from_wsgi_env
from pywb import get_test_dir

import logging
import os
import yaml
import pkgutil

#=================================================================
CONFIG_FILE = 'config.yaml'

DEFAULT_PORT = 8080

config = None
if __package__:
    try:
        config = pkgutil.get_data(__package__, CONFIG_FILE)
        config = yaml.load(config)
    except:
        pass


#=================================================================
def main(paths=None):
    logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                        level=logging.DEBUG)

    if not paths:
        if config:
            paths = config
        else:
            paths = get_test_dir() + 'cdx/'

    cdxserver = create_cdx_server(paths)

    def application(env, start_response):
        try:
            params = extract_params_from_wsgi_env(env)
            response = cdxserver.load_cdx(**params)
            start_response('200 OK', [('Content-Type', 'text/plain')])

            response = list(response)

        except Exception as exc:
            import traceback
            err_details = traceback.format_exc(exc)
            start_response('400 Error', [('Content-Type', 'text/plain')])
            response = [str(exc)]
            print err_details

        return response

    return application


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    app = main()

    port = DEFAULT_PORT
    if config:
        port = config.get('port', DEFAULT_PORT)

    httpd = make_server('', port, app)

    logging.debug('Starting CDX Server on port ' + str(port))

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    logging.debug('Stopping CDX Server')
else:
    application = main()
