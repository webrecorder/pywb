from cdxserver import CDXServer
import logging
import os
import yaml
import pkgutil

#=================================================================
TEST_CDX_DIR = os.path.dirname(os.path.realpath(__file__)) + '/../sample_data/'

CONFIG_FILE = 'config.yaml'

DEFAULT_PORT = 8080

if __package__:
    config = pkgutil.get_data(__package__, CONFIG_FILE)
    config = yaml.load(config)
else:
    config = None


#=================================================================
def main():
    logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                        level=logging.DEBUG)

    cdx_config = config.get('index_paths') if config else None

    if not cdx_config:
        cdx_config = [TEST_CDX_DIR]

    cdxserver = CDXServer(cdx_config)

    def application(env, start_response):
        try:
            response = cdxserver.load_cdx_from_request(env)
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
