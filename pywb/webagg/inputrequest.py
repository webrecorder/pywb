from warcio.limitreader import LimitReader
from warcio.statusandheaders import StatusAndHeadersParser

from pywb.utils.loaders import extract_post_query, append_post_query

from six.moves.urllib.parse import urlsplit, quote
from six import iteritems, StringIO
from io import BytesIO


#=============================================================================
class DirectWSGIInputRequest(object):
    def __init__(self, env):
        self.env = env

    def get_req_method(self):
        return self.env['REQUEST_METHOD'].upper()

    def get_req_protocol(self):
        return self.env['SERVER_PROTOCOL']

    def get_req_headers(self):
        headers = {}

        for name, value in iteritems(self.env):
            # will be set by requests to match actual host
            if name == 'HTTP_HOST':
                continue

            elif name.startswith('HTTP_'):
                name = name[5:].title().replace('_', '-')

            elif name in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                name = name.title().replace('_', '-')

            else:
                value = None

            if value:
                headers[name] = value

        return headers

    def get_req_body(self):
        input_ = self.env['wsgi.input']
        len_ = self._get_content_length()
        enc = self._get_header('Transfer-Encoding')

        if len_:
            data = LimitReader(input_, int(len_))
        elif enc:
            data = input_
        else:
            data = None

        return data

    def _get_content_type(self):
        return self.env.get('CONTENT_TYPE')

    def _get_content_length(self):
        return self.env.get('CONTENT_LENGTH')

    def _get_header(self, name):
        return self.env.get('HTTP_' + name.upper().replace('-', '_'))

    def include_post_query(self, url):
        if not url or self.get_req_method() != 'POST':
            return url

        mime = self._get_content_type()
        #mime = mime.split(';')[0] if mime else ''
        length = self._get_content_length()
        stream = self.env['wsgi.input']

        buffered_stream = BytesIO()

        post_query = extract_post_query('POST', mime, length, stream,
                                        buffered_stream=buffered_stream,
                                        environ=self.env)

        if post_query:
            self.env['wsgi.input'] = buffered_stream
            url = append_post_query(url, post_query)

        return url

    def get_full_request_uri(self):
        req_uri = self.env.get('REQUEST_URI')
        if req_uri and not self.env.get('SCRIPT_NAME'):
            return req_uri

        req_uri = quote(self.env.get('PATH_INFO', ''), safe='/~!$&\'()*+,;=:@')
        query = self.env.get('QUERY_STRING')
        if query:
            req_uri += '?' + query

        return req_uri

    def reconstruct_request(self, url=None):
        buff = StringIO()
        buff.write(self.get_req_method())
        buff.write(' ')
        buff.write(self.get_full_request_uri())
        buff.write(' ')
        buff.write(self.get_req_protocol())
        buff.write('\r\n')

        headers = self.get_req_headers()

        if url:
            parts = urlsplit(url)
            buff.write('Host: ')
            buff.write(parts.netloc)
            buff.write('\r\n')

        for name, value in iteritems(headers):
            if name.lower() == 'host':
                continue

            buff.write(name)
            buff.write(': ')
            buff.write(value)
            buff.write('\r\n')

        buff.write('\r\n')
        buff = buff.getvalue().encode('latin-1')

        body = self.get_req_body()
        if body:
            buff += body.read()

        return buff


#=============================================================================
class POSTInputRequest(DirectWSGIInputRequest):
    def __init__(self, env):
        self.env = env

        parser = StatusAndHeadersParser([], verify=False)

        self.status_headers = parser.parse(self.env['wsgi.input'])

    def get_req_method(self):
        return self.status_headers.protocol

    def get_req_headers(self):
        headers = {}
        for n, v in self.status_headers.headers:
            headers[n] = v

        return headers

    def get_full_request_uri(self):
        return self.status_headers.statusline.split(' ', 1)[0]

    def get_req_protocol(self):
        return self.status_headers.statusline.split(' ', 1)[-1]

    def _get_content_type(self):
        return self.status_headers.get_header('Content-Type')

    def _get_content_length(self):
        return self.status_headers.get_header('Content-Length')

    def _get_header(self, name):
        return self.status_headers.get_header(name)



