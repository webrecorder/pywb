from rezag.inputrequest import WSGIInputRequest, POSTInputRequest
from bottle import route, request, response, default_app


def add_route(path, handler):
    def debug(func):
        def do_d():
            try:
                return func()
            except Exception:
                import traceback
                traceback.print_exc()

        return do_d

    def direct_input_request():
        params = dict(request.query)
        params['_input_req'] = WSGIInputRequest(request.environ)
        return handler(params)

    def post_fullrequest():
        params = dict(request.query)
        params['_input_req'] = POSTInputRequest(request.environ)
        return handler(params)

    route(path + '/postreq', method=['POST'], callback=debug(post_fullrequest))
    route(path, method=['ANY'], callback=debug(direct_input_request))


application = default_app()

