from warcio.statusandheaders import StatusAndHeaders

from pywb.utils.io import no_except_close

try:
    import ujson as json
except ImportError:  # pragma: no cover
    import json


# =================================================================
class WbResponse(object):
    """Represnts a pywb wsgi response object.

    Holds a status_headers object and a response iter, to be
    returned to wsgi container."""

    def __init__(self, status_headers, value=None, **kwargs):
        """
        :param StatusAndHeaders status_headers: The StatusAndHeaders object for this response
        :param Any value: The response body
        :param Any kwargs: Additional keyword arguments to be passed to subclasses
        """
        if value is None:
            value = list()
        self.status_headers = status_headers
        self.body = value
        self._init_derived(kwargs)

    def _init_derived(self, params):
        """Receive the kwargs used in construction of this class

        :param Any params:
        :return:
        :rtype: None
        """
        pass

    @staticmethod
    def text_stream(stream, content_type='text/plain; charset=utf-8', status='200 OK'):
        """Utility method for constructing a streaming text response.

        :param Any stream: The response body stream
        :param str content_type: The content-type of the response
        :param str status: The HTTP status line
        :return: WbResponse that is a text stream
        :rtype WbResponse:
        """
        if 'charset' not in content_type:
            content_type += '; charset=utf-8'

        return WbResponse.bin_stream(WbResponse.encode_stream(stream), content_type, status)

    @staticmethod
    def encode_stream(stream):
        """Utility method to encode a stream using utf-8.

        :param Any stream: The stream to be encoded using utf-8
        :return: A generator that yields the contents of the stream encoded as utf-8
        """
        for obj in stream:
            yield obj.encode('utf-8')

    @staticmethod
    def bin_stream(stream, content_type, status='200 OK',
                   headers=None):
        """Utility method for constructing a binary response.

        :param Any stream: The response body stream
        :param str content_type: The content-type of the response
        :param str status: The HTTP status line
        :param list[tuple[str, str]] headers: Additional headers for this response
        :return: WbResponse that is a binary stream
        :rtype: WbResponse
        """
        def_headers = [('Content-Type', content_type)]
        if headers:
            def_headers += headers

        status_headers = StatusAndHeaders(status, def_headers)

        return WbResponse(status_headers, value=stream)

    @staticmethod
    def text_response(text, status='200 OK', content_type='text/plain; charset=utf-8'):
        """Utility method for constructing a text response.

        :param str text: The text response body
        :param str content_type: The content-type of the response
        :param str status: The HTTP status line
        :return: WbResponse text response
        :rtype: WbResponse
        """
        encoded_text = text.encode('utf-8')
        status_headers = StatusAndHeaders(status,
                                          [('Content-Type', content_type),
                                           ('Content-Length', str(len(encoded_text)))])

        return WbResponse(status_headers, value=[encoded_text])

    @staticmethod
    def json_response(obj, status='200 OK', content_type='application/json; charset=utf-8'):
        """Utility method for constructing a JSON response.

        :param dict obj: The dictionary to be serialized in JSON format
        :param str content_type: The content-type of the response
        :param str status: The HTTP status line
        :return: WbResponse JSON response
        :rtype: WbResponse
        """
        return WbResponse.text_response(json.dumps(obj), status, content_type)

    @staticmethod
    def redir_response(location, status='302 Redirect', headers=None):
        """Utility method for constructing redirection response.

        :param str location: The location of the resource redirecting to
        :param str status: The HTTP status line
        :param list[tuple[str, str]] headers: Additional headers for this response
        :return: WbResponse redirection response
        :rtype: WbResponse
        """
        redir_headers = [('Location', location), ('Content-Length', '0')]
        if headers:
            redir_headers += headers

        return WbResponse(StatusAndHeaders(status, redir_headers))

    @staticmethod
    def options_response(env):
        """Construct WbResponse for OPTIONS based on the WSGI env dictionary

        :param dict env: The WSGI environment dictionary
        :return: The WBResponse for the options request
        :rtype: WbResponse
        """
        status_headers = StatusAndHeaders('200 Ok', [
            ('Content-Type', 'text/plain'),
            ('Content-Length', '0'),
        ])
        response = WbResponse(status_headers)
        response.add_access_control_headers(env=env)
        return response

    def try_fix_errors(self):
        """Utility method to try remove faulty headers from response.

        :return:
        :rtype: None
        """
        for header in self.status_headers.headers:
            try:
                header[1].encode('latin1')
            except UnicodeError:
                self.status_headers.remove_header(header[0])

    def __call__(self, env, start_response):
        """Callable definition to allow WbResponse control over how the response is sent

        :param dict env: The WSGI environment dictionary
        :param function start_response: The WSGI start_response function
        :return: The response body
        """
        try:
            start_response(self.status_headers.statusline,
                           self.status_headers.headers)
        except (UnicodeError, TypeError):
            self.try_fix_errors()
            start_response(self.status_headers.statusline,
                           self.status_headers.headers)

        request_method = env['REQUEST_METHOD']
        if request_method == 'HEAD' or request_method == 'OPTIONS' or self.status_headers.statusline.startswith('304'):
            no_except_close(self.body)
            return []

        return self.body

    def add_range(self, *args):
        """Add HTTP range header values to this response

        :param int args: The values for the range HTTP header
        :return: The same WbResponse but with the values for the range HTTP header added
        :rtype: WbResponse
        """
        self.status_headers.add_range(*args)
        return self

    def add_access_control_headers(self, env=None):
        """Adds Access-Control* HTTP headers to this WbResponse's HTTP headers.

        :param dict env: The WSGI environment dictionary
        :return: The same WbResponse but with the values for the Access-Control* HTTP header added
        :rtype: WbResponse
        """
        allowed_methods = 'GET, POST, PUT, OPTIONS, DELETE, PATCH, HEAD, TRACE, CONNECT'
        allowed_origin = None
        if env is not None:
            acr_method = env.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')
            if acr_method is not None and acr_method not in allowed_methods:
                allowed_methods = allowed_methods + ', ' + acr_method
            r_method = env.get('REQUEST_METHOD')
            if r_method is not None and r_method not in allowed_methods:
                allowed_methods = allowed_methods + ', ' + r_method
            acr_headers = env.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS')
            if acr_headers is not None:
                self.status_headers.replace_header('Access-Control-Allow-Headers', acr_headers)
            allowed_origin = env.get('HTTP_ORIGIN', env.get('HTTP_REFERER', allowed_origin))
        if allowed_origin is None:
            allowed_origin = '*'
        self.status_headers.replace_header('Access-Control-Allow-Origin',  allowed_origin)
        self.status_headers.replace_header('Access-Control-Allow-Methods', allowed_methods)
        self.status_headers.replace_header('Access-Control-Allow-Credentials', 'true')
        self.status_headers.replace_header('Access-Control-Max-Age', '1800')
        return self

    def __repr__(self):
        return str(vars(self))
