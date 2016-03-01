from rezag.inputrequest import DirectWSGIInputRequest, POSTInputRequest
from bottle import route, request, response, default_app, abort
import bottle

from pywb.utils.wbexception import WbException

import traceback
import json

def err_handler(exc):
    response.status = exc.status_code
    response.content_type = 'application/json'
    return json.dumps({'message': exc.body})


def wrap_error(func):
    def wrap_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except WbException as exc:
            if bottle.debug:
                traceback.print_exc()
            abort(exc.status(), exc.msg)
        except Exception as e:
            if bottle.debug:
                traceback.print_exc()
            abort(500, 'Internal Error: ' + str(e))

    return wrap_func


route_dict = {}

def add_route(path, handler):
    @route(path, 'ANY')
    @wrap_error
    def direct_input_request():
        params = dict(request.query)
        params['_input_req'] = DirectWSGIInputRequest(request.environ)
        return handler(params)

    @route(path + '/postreq', 'POST')
    @wrap_error
    def post_fullrequest():
        params = dict(request.query)
        params['_input_req'] = POSTInputRequest(request.environ)
        return handler(params)

    global route_dict
    handler_dict = {'handler': handler.get_supported_modes()}
    route_dict[path] = handler_dict
    route_dict[path + '/postreq'] = handler_dict

@route('/')
def list_routes():
    return route_dict







application = default_app()
application.default_error_handler = err_handler


