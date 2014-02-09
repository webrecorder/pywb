import utils
import wbexceptions

from wbrequestresponse import WbResponse, StatusAndHeaders

import os
import importlib
import logging



#=================================================================
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
            response = handle_exception(env, wb_router.error_view, e, False)

        except wbexceptions.WbException as wbe:
            response = handle_exception(env, wb_router.error_view, wbe, False)

        except Exception as e:
            response = handle_exception(env, wb_router.error_view, e, True)

        return response(env, start_response)


    return application


def handle_exception(env, error_view, exc, print_trace):
    if hasattr(exc, 'status'):
        status = exc.status()
    else:
        status = '400 Bad Request'

    if print_trace:
        import traceback
        err_details = traceback.format_exc(exc)
        print err_details
    else:
        logging.info(str(exc))
        err_details = None

    if error_view:
        import traceback
        return error_view.render_response(err_msg = str(exc), err_details = err_details, status = status)
    else:
        return WbResponse.text_response(status + ' Error: ' + str(exc), status = status)


#=================================================================
DEFAULT_CONFIG_FILE = 'config.yaml'

def main():
    try:
        logging.basicConfig(format = '%(asctime)s: [%(levelname)s]: %(message)s', level = logging.DEBUG)

        # see if there's a custom init module
        config_name = os.environ.get('PYWB_CONFIG_MODULE')

        if not config_name:
            # use default module
            config_name = 'pywb.pywb_init'
            logging.info('Loading from default config module "{0}"'.format(config_name))
            logging.info('')

        module = importlib.import_module(config_name)

        app = create_wb_app(module.pywb_config())
        logging.info('')
        logging.info('*** pywb inited with settings from {0}.pywb_config()!\n'.format(config_name))
        return app

    except Exception:
        logging.exception('*** pywb could not init with settings from {0}.pywb_config()!\n'.format(config_name))
        raise

#=================================================================
if __name__ == "__main__" or utils.enable_doctests():
    pass
else:
    application = main()
