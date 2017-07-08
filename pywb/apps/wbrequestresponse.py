from warcio.statusandheaders import StatusAndHeaders
from werkzeug.wrappers import Request  # for options response see comments in options_response

import json



#=================================================================
class WbResponse(object):
    """
    Represnts a pywb wsgi response object.

    Holds a status_headers object and a response iter, to be
    returned to wsgi container.
    """
    def __init__(self, status_headers, value=[], **kwargs):
        self.status_headers = status_headers
        self.body = value
        self._init_derived(kwargs)

    def _init_derived(self, params):
        pass

    @staticmethod
    def text_stream(stream, content_type='text/plain; charset=utf-8', status='200 OK'):
        def encode(stream):
            for obj in stream:
                yield obj.encode('utf-8')

        if 'charset' not in content_type:
            content_type += '; charset=utf-8'

        return WbResponse.bin_stream(encode(stream), content_type, status)

    @staticmethod
    def bin_stream(stream, content_type, status='200 OK',
                    headers=None):
        def_headers = [('Content-Type', content_type)]
        if headers:
            def_headers += headers

        status_headers = StatusAndHeaders(status, def_headers)

        return WbResponse(status_headers, value=stream)

    @staticmethod
    def text_response(text, status='200 OK', content_type='text/plain; charset=utf-8'):
        encoded_text = text.encode('utf-8')
        status_headers = StatusAndHeaders(status,
                                          [('Content-Type', content_type),
                                           ('Content-Length', str(len(encoded_text)))])

        return WbResponse(status_headers, value=[encoded_text])

    @staticmethod
    def options_response(environ, status='200 OK', headers=None):
        """
        In order to maintain High Fidelity Replay the
        replay system must respond to OPTIONS requests
        either pre-flighted or explicit with a
        at least allow all origins and state support for GET,POST,HEAD,OPTIONS,CONNECT methods.
        Heavy JS pages will do all manner of fun things with OPTIONS
        and redirection. Most that do use explicit JS made OPTIONS
        request will not replay if the appropriate Access-Control-Allow-Origin
        is not in the headers of the response. The most
        common use case of this is cors preflighting, webrecorder
        suffers the most from this :'(
        https://fetch.spec.whatwg.org/#cors-protocol-and-credentials
        https://www.w3.org/TR/cors/
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS
        https://www.html5rocks.com/en/tutorials/cors/#toc-adding-cors-support-to-the-server
        """
        # to conform to cors negotiation, the HTTP headers
        # are only nicely accessible by wrapping environment in werkzeug.wrappers.Request
        head = Request(environ).headers
        allowed_meth = 'GET,HEAD,POST,OPTIONS,CONNECT'
        if head.get('Method') not in allowed_meth:
            allowed_meth += ',%s' % head.get('Method')
        opts_headers = [
            ('Access-Control-Allow-Origin', head.get('Origin', '*')),  # origin will always be set but....
            ('Access-Control-Allow-Methods', allowed_meth)  # the bare essentials
        ]
        acrh = head.get('Access-Control-Request-Headers', None)
        if acrh is not None:
            opts_headers.append(('Access-Control-Allow-Headers', acrh))

        if head.get('Cookie', None) is not None:
            opts_headers.append(('Access-Control-Allow-Credentials', 'true'))

        opts_headers.append(('Content-Length', '0'))
        if headers:
            opts_headers += headers
        return WbResponse(StatusAndHeaders(status, opts_headers))

    @staticmethod
    def json_response(obj, status='200 OK', content_type='application/json; charset=utf-8'):
        return WbResponse.text_response(json.dumps(obj), status, content_type)

    @staticmethod
    def redir_response(location, status='302 Redirect', headers=None):
        redir_headers = [('Location', location), ('Content-Length', '0')]
        if headers:
            redir_headers += headers

        return WbResponse(StatusAndHeaders(status, redir_headers))

    def __call__(self, env, start_response):
        start_response(self.status_headers.statusline,
                       self.status_headers.headers)

        if env['REQUEST_METHOD'] == 'HEAD':
            if hasattr(self.body, 'close'):
                self.body.close()
            return []

        return self.body

    def add_range(self, *args):
        self.status_headers.add_range(*args)
        return self

    def __repr__(self):
        return str(vars(self))
