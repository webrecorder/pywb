from pywb.utils.loaders import extract_client_cookie
from pywb.utils.loaders import extract_post_query, append_post_query
from pywb.utils.loaders import LimitReader
from pywb.utils.statusandheaders import StatusAndHeadersParser

from six.moves.urllib.parse import urlsplit
from six import StringIO, iteritems
from io import BytesIO


#=============================================================================
class WSGIInputRequest(object):
    def __init__(self, env):
        self.env = env

    def get_req_method(self):
        return self.env['REQUEST_METHOD'].upper()

    def get_req_headers(self):
        headers = {}

        for name, value in iteritems(self.env):
            if name == 'HTTP_HOST':
                #name = 'Host'
                #value = splits.netloc
                # will be set automatically
                continue

            #elif name == 'HTTP_ORIGIN':
            #    name = 'Origin'
            #    value = (splits.scheme + '://' + splits.netloc)

            elif name == 'HTTP_X_CSRFTOKEN':
                name = 'X-CSRFToken'
                cookie_val = extract_client_cookie(env, 'csrftoken')
                if cookie_val:
                    value = cookie_val

            #elif name == 'HTTP_X_FORWARDED_PROTO':
            #    name = 'X-Forwarded-Proto'
            #    value = splits.scheme

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
        input_ = self.env.get('wsgi.input')
        if not input_:
            return None

        len_ = self._get_content_length()
        enc = self._get_header('Transfer-Encoding')

        if len_:
            data = LimitReader(input_, int(len_))
        elif enc:
            data = input_
        else:
            data = None

        return data
        #buf = data.read().decode('utf-8')
        #print(buf)
        #return StringIO(buf)

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
        mime = mime.split(';')[0] if mime else ''
        length = self._get_content_length()
        stream = self.env['wsgi.input']

        buffered_stream = BytesIO()

        post_query = extract_post_query('POST', mime, length, stream,
                                        buffered_stream=buffered_stream)

        if post_query:
            self.env['wsgi.input'] = buffered_stream
            url = append_post_query(url, post_query)

        return url


#=============================================================================
class POSTInputRequest(WSGIInputRequest):
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

    def _get_content_type(self):
        return self.status_headers.get_header('Content-Type')

    def _get_content_length(self):
        return self.status_headers.get_header('Content-Length')

    def _get_header(self, name):
        return self.status_headers.get_header(name)



