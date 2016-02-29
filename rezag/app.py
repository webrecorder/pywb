from rezag.inputrequest import DirectWSGIInputRequest, POSTInputRequest
from bottle import route, request, response, default_app, abort

from pywb.utils.wbexception import WbException

import traceback
import json

def err_handler(exc):
    response.status = exc.status_code
    response.content_type = 'application/json'
    return json.dumps({'message': exc.body})

def wrap_error(func):
    def do_d(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except WbException as exc:
            if application.debug:
                traceback.print_exc()
            abort(exc.status(), exc.msg)
        except Exception as e:
            if application.debug:
                traceback.print_exc()
            abort(500, 'Internal Error: ' + str(e))

    return do_d


def add_route(path, handler):
    @wrap_error
    def direct_input_request(mode=''):
        params = dict(request.query)
        params['_input_req'] = DirectWSGIInputRequest(request.environ)
        return handler(params)

    @wrap_error
    def post_fullrequest(mode=''):
        params = dict(request.query)
        params['_input_req'] = POSTInputRequest(request.environ)
        return handler(params)

    route(path + '/postreq', method=['POST'], callback=post_fullrequest)
    route(path, method=['ANY'], callback=direct_input_request)


application = default_app()
application.default_error_handler = err_handler


