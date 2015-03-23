from pywb.utils.wbexception import WbException, NotFoundException
from pywb.utils.loaders import load_yaml_config

from wbrequestresponse import WbResponse, StatusAndHeaders


import os
import logging


DEFAULT_PORT = 8080

#=================================================================
# adapted from wsgiref.request_uri, but doesn't include domain name
# and allows all characters which are allowed in the path segment
# according to: http://tools.ietf.org/html/rfc3986#section-3.3
# explained here:
# http://stackoverflow.com/questions/4669692/
#   valid-characters-for-directory-part-of-a-url-for-short-links


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
    url = quote(environ.get('PATH_INFO', ''), safe='/~!$&\'()*+,;=:@')
    if include_query and environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']

    return url


#=================================================================
class WSGIApp(object):
    def __init__(self, wb_router):
        self.wb_router = wb_router

    # Top-level wsgi application
    def __call__(self, env, start_response):
        if env['REQUEST_METHOD'] == 'CONNECT':
            return self.handle_connect(env, start_response)
        else:
            return self.handle_methods(env, start_response)

    def handle_connect(self, env, start_response):
        def ssl_start_response(statusline, headers):
            ssl_sock = env.get('pywb.proxy_ssl_sock')
            if not ssl_sock:
                start_response(statusline, headers)
                return

            env['pywb.proxy_statusline'] = statusline

            ssl_sock.write('HTTP/1.1 ' + statusline + '\r\n')
            for name, value in headers:
                ssl_sock.write(name + ': ' + value + '\r\n')

        resp_iter = self.handle_methods(env, ssl_start_response)

        ssl_sock = env.get('pywb.proxy_ssl_sock')
        if not ssl_sock:
            return resp_iter

        ssl_sock.write('\r\n')

        for obj in resp_iter:
            if obj:
                ssl_sock.write(obj)
        ssl_sock.close()

        start_response(env['pywb.proxy_statusline'], [])

        return []

    def handle_methods(self, env, start_response):
        if env.get('SCRIPT_NAME') or not env.get('REQUEST_URI'):
            env['REL_REQUEST_URI'] = rel_request_uri(env)
        else:
            env['REL_REQUEST_URI'] = env['REQUEST_URI']

        wb_router = self.wb_router
        response = None

        try:
            response = wb_router(env)

            if not response:
                msg = 'No handler for "{0}".'.format(env['REL_REQUEST_URI'])
                raise NotFoundException(msg)

        except WbException as e:
            response = self.handle_exception(env, e, False)

        except Exception as e:
            response = self.handle_exception(env, e, True)

        return response(env, start_response)

    def handle_exception(self, env, exc, print_trace):
        error_view = None

        if hasattr(self.wb_router, 'error_view'):
            error_view = self.wb_router.error_view

        if hasattr(exc, 'status'):
            status = exc.status()
        else:
            status = '500 Internal Server Error'

        if hasattr(exc, 'url'):
            err_url = exc.url
        else:
            err_url = None

        err_msg = exc.message

        if print_trace:
            import traceback
            err_details = traceback.format_exc(exc)
            print err_details
        else:
            logging.info(err_msg)
            err_details = None

        if error_view:
            if err_url and isinstance(err_url, str):
                err_url = err_url.decode('utf-8', 'ignore')
            if err_msg and isinstance(err_msg, str):
                err_msg = err_msg.decode('utf-8', 'ignore')

            return error_view.render_response(exc_type=type(exc).__name__,
                                              err_msg=err_msg,
                                              err_details=err_details,
                                              status=status,
                                              env=env,
                                              err_url=err_url)
        else:
            msg = status + ' Error: '
            if err_msg:
                msg += err_msg

            msg = msg.encode('utf-8', 'ignore')
            return WbResponse.text_response(msg,
                                            status=status)

#=================================================================
DEFAULT_CONFIG_FILE = 'config.yaml'


#=================================================================
def init_app(init_func, load_yaml=True, config_file=None, config={}):
    logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                        level=logging.DEBUG)
    logging.debug('')

    try:
        if load_yaml:
            # env setting overrides all others
            env_config = os.environ.get('PYWB_CONFIG_FILE')
            if env_config:
                config_file = env_config

            if not config_file:
                config_file = DEFAULT_CONFIG_FILE

            if os.path.isfile(config_file):
                config = load_yaml_config(config_file)

        wb_router = init_func(config)
    except:
        msg = '*** pywb app init FAILED config from "%s"!\n'
        logging.exception(msg, init_func.__name__)
        raise
    else:
        msg = '*** pywb app inited with config from "%s"!\n'
        logging.debug(msg, init_func.__name__)

    return WSGIApp(wb_router)


#=================================================================
def start_wsgi_ref_server(the_app, name, port):  # pragma: no cover
    from wsgiref.simple_server import make_server

    # disable is_hop_by_hop restrictions
    import wsgiref.handlers
    wsgiref.handlers.is_hop_by_hop = lambda x: False

    if not port:
        port = DEFAULT_PORT

    logging.info('Starting %s on port %s', name, port)

    try:
        httpd = make_server('', port, the_app)
        httpd.serve_forever()
    except KeyboardInterrupt as ex:
        pass
    finally:
        logging.info('Stopping %s', name)
