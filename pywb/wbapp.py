import utils
import wbexceptions

from wbrequestresponse import WbResponse, StatusAndHeaders

import os
import importlib
import logging



## ===========
'''

To declare Wayback with one collection, `mycoll`
and will be accessed by user at:

`http://mywb.example.com:8080/mycoll/`

and will load cdx from cdx server running at:

`http://cdx.example.com/cdx`

and look for warcs at paths:

`http://warcs.example.com/servewarc/` and
`http://warcs.example.com/anotherpath/`,

one could declare a `sample_wb_settings()` method as follows
'''



def create_wb_app(wb_router):

    # Top-level wsgi application
    def application(env, start_response):
        if env.get('SCRIPT_NAME') or not env.get('REQUEST_URI'):
            env['REL_REQUEST_URI'] = utils.rel_request_uri(env)
        else:
            env['REL_REQUEST_URI'] = env['REQUEST_URI']

        response = None

        try:
            response = wb_router(env)

            if not response:
                raise wbexceptions.NotFoundException('No handler for "{0}"'.format(env['REL_REQUEST_URI']))

        except wbexceptions.InternalRedirect as ir:
            response = WbResponse(StatusAndHeaders(ir.status, ir.httpHeaders))

        except (wbexceptions.NotFoundException, wbexceptions.AccessException) as e:
            logging.info(str(e))
            response = handle_exception(env, e)

        except Exception as e:
            last_exc = e
            import traceback
            traceback.print_exc()
            response = handle_exception(env, e)

        return response(env, start_response)


    return application


def handle_exception(env, exc):
    if hasattr(exc, 'status'):
        status = exc.status()
    else:
        status = '400 Bad Request'

    return WbResponse.text_response(status + ' Error: ' + str(exc), status = status)


#=================================================================
DEFAULT_CONFIG_FILE = 'config.yaml'

def main():
    try:
        # Attempt to load real settings from globalwb module
        logging.basicConfig(format = '%(asctime)s: [%(levelname)s]: %(message)s', level = logging.DEBUG)

        config_name = os.environ.get('PYWB_CONFIG')

        if not config_name:
            config_name = 'pywb.pywb_init'
            logging.info('PYWB_CONFIG not specified, loading default settings from module "{0}"'.format(config_name))
            logging.info('')

        module = importlib.import_module(config_name)

        config_file = DEFAULT_CONFIG_FILE

        app = create_wb_app(module.pywb_config(config_file))
        logging.info('')
        logging.info('*** pywb inited with settings from {0}.pywb_config()!\n'.format(config_name))
        return app

    except Exception as e:
        # Otherwise, start with the sample settings
        logging.exception('*** pywb could not init with settings from {0}.pywb_config()!\n'.format(config_name))
        raise e

#=================================================================
if __name__ == "__main__" or utils.enable_doctests():
    import pywb_init
    # Test sample settings
    application = create_wb_app(pywb_init.pywb_config('../' + DEFAULT_CONFIG_FILE))
else:
    application = main()
