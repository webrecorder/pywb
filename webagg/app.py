from webagg.liverec import request as remote_request

from webagg.inputrequest import DirectWSGIInputRequest, POSTInputRequest
from bottle import route, request, response, abort, Bottle
import bottle

import traceback
import json

JSON_CT = 'application/json; charset=utf-8'


#=============================================================================
class ResAggApp(object):
    def __init__(self, *args, **kwargs):
        self.application = Bottle()
        self.application.default_error_handler = self.err_handler
        self.route_dict = {}

        @self.application.route('/')
        def list_routes():
            return self.route_dict

    def add_route(self, path, handler):
        @self.application.route([path, path + '/<mode:path>'], 'ANY')
        @wrap_error
        def direct_input_request(mode=''):
            params = dict(request.query)
            params['mode'] = mode
            params['_input_req'] = DirectWSGIInputRequest(request.environ)
            return handler(params)

        @self.application.route([path + '/postreq', path + '/<mode:path>/postreq'], 'POST')
        @wrap_error
        def post_fullrequest(mode=''):
            params = dict(request.query)
            params['mode'] = mode
            params['_input_req'] = POSTInputRequest(request.environ)
            return handler(params)

        handler_dict = handler.get_supported_modes()
        self.route_dict[path] = handler_dict
        self.route_dict[path + '/postreq'] = handler_dict

    def err_handler(self, exc):
        if bottle.debug:
            print(exc)
            traceback.print_exc()
        response.status = exc.status_code
        response.content_type = JSON_CT
        err_msg = json.dumps({'message': exc.body})
        response.headers['ResErrors'] = err_msg
        return err_msg


#=============================================================================
def wrap_error(func):
    def wrap_func(*args, **kwargs):
        try:
            out_headers, res, errs = func(*args, **kwargs)

            if out_headers:
                for n, v in out_headers.items():
                    response.headers[n] = v

            if res:
                if errs:
                    response.headers['ResErrors'] = json.dumps(errs)
                return res

            last_exc = errs.pop('last_exc', None)
            if last_exc:
                if bottle.debug:
                    traceback.print_exc()

                response.status = last_exc.status()
                message = last_exc.msg
            else:
                response.status = 404
                message = 'No Resource Found'

            response.content_type = JSON_CT
            res = {'message': message}
            if errs:
                res['errors'] = errs

            err_msg = json.dumps(res)
            response.headers['ResErrors'] = err_msg
            return err_msg

        except Exception as e:
            if bottle.debug:
                traceback.print_exc()
            abort(500, 'Internal Error: ' + str(e))

    return wrap_func


