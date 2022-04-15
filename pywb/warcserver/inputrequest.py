from warcio.limitreader import LimitReader
from warcio.statusandheaders import StatusAndHeadersParser
from pywb.warcserver.amf import Amf
from pyamf.remoting import decode
from warcio.utils import to_native_str

from six.moves.urllib.parse import urlsplit, quote, unquote_plus, urlencode
from six import iteritems, StringIO, PY3
from io import BytesIO

import base64
import cgi
import json
import sys


#=============================================================================
class DirectWSGIInputRequest(object):
    def __init__(self, env):
        self.env = env

    def get_req_method(self):
        return self.env['REQUEST_METHOD'].upper()

    def get_req_protocol(self):
        return self.env['SERVER_PROTOCOL']

    def get_referrer(self):
        return self._get_header('Referer')

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

    def include_method_query(self, url):
        if not url:
            return url

        method = self.get_req_method()

        if method == 'GET' or method == 'HEAD':
            return url

        mime = self._get_content_type()
        length = self._get_content_length()
        stream = self.env['wsgi.input']

        buffered_stream = BytesIO()

        query = MethodQueryCanonicalizer(method, mime, length, stream,
                                           buffered_stream=buffered_stream,
                                           environ=self.env)

        new_url = query.append_query(url)
        if new_url != url:
            self.env['wsgi.input'] = buffered_stream

        return new_url

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


# ============================================================================
class MethodQueryCanonicalizer(object):
    #MAX_POST_SIZE = 16384
    MAX_QUERY_LENGTH = 4096

    def __init__(self, method, mime, length, stream,
                       buffered_stream=None,
                       environ=None):
        """
        Append the method for HEAD/OPTIONS as __pywb_method=<method>
        For POST requests, requests extract a url-encoded form from stream
        read content length and convert to query params, if possible
        Attempt to decode application/x-www-form-urlencoded or multipart/*,
        otherwise read whole block and b64encode
        """
        self.query = b''

        method = method.upper()
        self.method = method

        if method != 'POST' and method != 'PUT':
            return

        try:
            length = int(length)
        except (ValueError, TypeError):
            return

        if length <= 0:
            return

        # always read entire POST request, but limit query string later
        #length = min(length, self.MAX_POST_SIZE)
        query = []

        while length > 0:
            buff = stream.read(length)
            length -= len(buff)

            if not buff:
                break

            query.append(buff)

        query = b''.join(query)

        if buffered_stream:
            buffered_stream.write(query)
            buffered_stream.seek(0)

        if not mime:
            mime = ''

        def handle_binary(query):
            query = base64.b64encode(query)
            query = to_native_str(query)
            query = '__wb_post_data=' + query
            return query

        if mime.startswith('application/x-www-form-urlencoded'):
            try:
                query = to_native_str(query.decode('utf-8'))
                query = unquote_plus(query)
            except UnicodeDecodeError:
                query = handle_binary(query)

        elif mime.startswith('multipart/'):
            env = {'REQUEST_METHOD': 'POST',
                   'CONTENT_TYPE': mime,
                   'CONTENT_LENGTH': len(query)}

            args = dict(fp=BytesIO(query),
                        environ=env,
                        keep_blank_values=True)

            if PY3:
                args['encoding'] = 'utf-8'

            try:
                data = cgi.FieldStorage(**args)
            except ValueError:
                # Content-Type multipart/form-data may lack "boundary" info
                query = handle_binary(query)
            else:
                values = []
                for item in data.list:
                    values.append((item.name, item.value))

                query = urlencode(values, True)

        elif mime.startswith('application/x-amf'):
            query = self.amf_parse(query, environ)

        elif mime.startswith('application/json'):
            try:
                query = self.json_parse(query)
            except Exception as e:
                sys.stderr.write("Ignoring query, error parsing as json: " + query.decode("utf-8") + "\n")
                query = ''

        elif mime.startswith('text/plain'):
            try:
                query = self.json_parse(query)
            except Exception as e:
                query = handle_binary(query)

        else:
            query = handle_binary(query)

        if query:
            self.query = query[:self.MAX_QUERY_LENGTH]

    def amf_parse(self, string, warn_on_error):
        try:
            res = decode(BytesIO(string))
            return urlencode({"request": Amf.get_representation(res)})

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
            return None

    def json_parse(self, string):
        data = {}
        dupes = {}

        def get_key(n):
            if n not in data:
                return n

            if n not in dupes:
                dupes[n] = 1

            dupes[n] += 1
            return n + "." + str(dupes[n]) + "_";

        def _parser(json_obj, name=""):
            if isinstance(json_obj, dict):
                for n, v in json_obj.items():
                    _parser(v, n)

            elif isinstance(json_obj, list):
                for v in json_obj:
                    _parser(v, name)

            elif name:
                data[get_key(name)] = str(json_obj)

        _parser(json.loads(string))
        return urlencode(data)

    def append_query(self, url):
        if self.method == 'GET':
            return url

        if '?' not in url:
            append_str = '?'
        else:
            append_str = '&'

        append_str += "__wb_method=" + self.method
        if self.query:
            append_str += '&' + self.query

        return url + append_str
