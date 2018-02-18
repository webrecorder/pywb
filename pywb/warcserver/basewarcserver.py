from pywb.warcserver.inputrequest import DirectWSGIInputRequest, POSTInputRequest
from pywb.utils.format import query_to_dict

from pywb.utils.wbexception import AccessException

from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException

import requests
import traceback
import json

import six

JSON_CT = 'application/json; charset=utf-8'


#=============================================================================
class BaseWarcServer(object):
    def __init__(self, *args, **kwargs):
        self.route_dict = {}
        self.debug = kwargs.get('debug', False)

        self.url_map = Map()

        def list_routes(environ):
            return {}, self.route_dict, {}

        self.url_map.add(Rule('/', endpoint=list_routes))

    def add_route(self, path, handler, path_param_name='', default_value=''):
        def direct_input_request(environ, mode='', path_param_value=default_value):
            params = self.get_query_dict(environ)
            params['mode'] = mode
            if path_param_value:
                params[path_param_name] = path_param_value
            params['_input_req'] = DirectWSGIInputRequest(environ)
            return handler(params)

        def post_fullrequest(environ, mode='', path_param_value=default_value):
            params = self.get_query_dict(environ)
            params['mode'] = mode
            if path_param_value:
                params[path_param_name] = path_param_value
            params['_input_req'] = POSTInputRequest(environ)
            return handler(params)

        self.url_map.add(Rule(path, endpoint=direct_input_request))
        self.url_map.add(Rule(path + '/<mode>', endpoint=direct_input_request))

        self.url_map.add(Rule(path + '/postreq', endpoint=post_fullrequest))
        self.url_map.add(Rule(path + '/<mode>/postreq', endpoint=post_fullrequest))

        handler_dict = handler.get_supported_modes()

        self.route_dict[path] = handler_dict
        self.route_dict[path + '/postreq'] = handler_dict

    def _add_simple_route(self, path, func):
        self.url_map.add(Rule(path, endpoint=func))

    def get_query_dict(self, environ):
        query_str = environ.get('QUERY_STRING')
        if query_str:
            return query_to_dict(query_str, multi=['filter'])
        else:
            return {}

    def __call__(self, environ, start_response):
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except HTTPException as e:
            return e(environ, start_response)

        try:
            result = endpoint(environ, **args)

            out_headers, res, errs = result

            if not res:
                return self.send_error(errs, start_response)

            if isinstance(res, dict):
                res = self.json_encode(res, out_headers)

            if errs:
                if 'last_exc' in errs:
                    errs['last_exc'] = str(errs['last_exc'])
                out_headers['ResErrors'] = json.dumps(errs)

            start_response('200 OK', list(out_headers.items()))
            return res

        except AccessException as ae:
            out_headers = {}
            res = self.json_encode(ae.msg, out_headers)
            start_response(ae.status(), list(out_headers.items()))
            return res

        except Exception as e:
            if self.debug:
                traceback.print_exc()
            message = 'Internal Error: ' + str(e)
            status = 500
            return self.send_error({}, start_response,
                                   message=message,
                                   status=status)

    def json_encode(self, res, out_headers):
        res = json.dumps(res).encode('utf-8')
        out_headers['Content-Type'] = JSON_CT
        out_headers['Content-Length'] = str(len(res))
        return [res]

    def send_error(self, errs, start_response,
                   message='No Resource Found', status=404):

        last_exc = errs.pop('last_exc', None)
        if last_exc:
            if self.debug:
                traceback.print_exc()

            if not hasattr(last_exc, 'status'):
                status = '503 Archive Not Available'
            else:
                status = last_exc.status()

            message = last_exc.msg

        res = {'message': message}
        if errs:
            res['errors'] = errs

        out_headers = {}
        res = self.json_encode(res, out_headers)

        if six.PY3:
            out_headers['ResErrors'] = res[0].decode('utf-8')
        else:
            out_headers['ResErrors'] = res[0]
            message = message.encode('utf-8')

        message = str(status) + ' ' + message
        start_response(message, list(out_headers.items()))
        return res
