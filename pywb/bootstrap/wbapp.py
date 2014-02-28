from pywb.core.wbexceptions import WbException, NotFoundException, InternalRedirect
from pywb.core.wbrequestresponse import WbResponse, StatusAndHeaders

from pywb.cdx.cdxserver import CDXException
from pywb.utils.canonicalize import UrlCanonicalizeException
from pywb.warc.recordloader import ArchiveLoadFailed

import os
import importlib
import logging



#=================================================================
# adapted -from wsgiref.request_uri, but doesn't include domain name and allows all characters
# allowed in the path segment according to: http://tools.ietf.org/html/rfc3986#section-3.3
# explained here: http://stackoverflow.com/questions/4669692/valid-characters-for-directory-part-of-a-url-for-short-links
def rel_request_uri(environ, include_query=1):
    """
    Return the requested path, optionally including the query string

    # Simple test:
    >>> rel_request_uri({'PATH_INFO': '/web/example.com'})
    '/web/example.com'

    # Test all unecoded special chars and double-quote
    # (double-quote must be encoded but not single quote)
    >>> rel_request_uri({'PATH_INFO': "/web/example.com/0~!+$&'()*+,;=:\\\""})
    "/web/example.com/0~!+$&'()*+,;=:%22"
    """
    from urllib import quote
    url = quote(environ.get('PATH_INFO',''), safe='/~!$&\'()*+,;=:@')
    if include_query and environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']

    return url

#=================================================================
def create_wb_app(wb_router):

    # Top-level wsgi application
    def application(env, start_response):
        if env.get('SCRIPT_NAME') or not env.get('REQUEST_URI'):
            env['REL_REQUEST_URI'] = rel_request_uri(env)
        else:
            env['REL_REQUEST_URI'] = env['REQUEST_URI']

        response = None

        try:
            response = wb_router(env)

            if not response:
                raise NotFoundException('No handler for "{0}"'.format(env['REL_REQUEST_URI']))

        except InternalRedirect as ir:
            response = WbResponse(StatusAndHeaders(ir.status, ir.httpHeaders))

        except (WbException, CDXException,
                UrlCanonicalizeException, ArchiveLoadFailed) as e:
            response = handle_exception(env, wb_router.error_view, e, False)

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

DEFAULT_INIT_MODULE = 'pywb.bootstrap.pywb_init'


#=================================================================
def main():
    try:
        logging.basicConfig(format = '%(asctime)s: [%(levelname)s]: %(message)s', level = logging.DEBUG)

        # see if there's a custom init module
        config_name = os.environ.get('PYWB_CONFIG_MODULE')

        if not config_name:
            # use default module
            config_name = DEFAULT_INIT_MODULE
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
if __name__ == "__main__":
    pass
else:
    application = main()
