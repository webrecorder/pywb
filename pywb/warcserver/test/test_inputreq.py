from pywb.warcserver.inputrequest import DirectWSGIInputRequest, POSTInputRequest, MethodQueryCanonicalizer
from werkzeug.routing import Map, Rule

import webtest
from six.moves.urllib.parse import parse_qsl
from io import BytesIO
from pyamf import AMF3
from pyamf.remoting import Request, Envelope, encode


#=============================================================================
class InputReqApp(object):
    def __init__(self):
        self.url_map = Map()
        self.url_map.add(Rule('/test/<path:url>', endpoint=self.direct_input_request))
        self.url_map.add(Rule('/test-postreq', endpoint=self.post_fullrequest))

    def direct_input_request(self, environ, url=''):
        inputreq = DirectWSGIInputRequest(environ)
        return inputreq.reconstruct_request(url)

    def post_fullrequest(self, environ):
        params = dict(parse_qsl(environ.get('QUERY_STRING', '')))
        inputreq = POSTInputRequest(environ)
        return inputreq.reconstruct_request(params['url'])

    def __call__(self, environ, start_response):
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except HTTPException as e:
            return e(environ, start_response)

        result = endpoint(environ, **args)
        start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
        return [result]



#=============================================================================
class TestInputReq(object):
    def setup_method(self):
        self.app = InputReqApp()
        self.testapp = webtest.TestApp(self.app)

    def test_get_direct(self):
        res = self.testapp.get('/test/http://example.com/', headers={'Foo': 'Bar'})
        assert res.text == '\
GET /test/http://example.com/ HTTP/1.0\r\n\
Host: example.com\r\n\
Foo: Bar\r\n\
\r\n\
'

    def test_post_direct(self):
        res = self.testapp.post('/test/http://example.com/', headers={'Foo': 'Bar'}, params='ABC')
        lines = res.text.split('\r\n')
        assert lines[0] == 'POST /test/http://example.com/ HTTP/1.0'
        assert 'Host: example.com' in lines
        assert 'Content-Length: 3' in lines
        assert 'Content-Type: application/x-www-form-urlencoded' in lines
        assert 'Foo: Bar' in lines

        assert 'ABC' in lines

    def test_post_req(self):
        postdata = '\
GET /example.html HTTP/1.0\r\n\
Foo: Bar\r\n\
\r\n\
'
        res = self.testapp.post('/test-postreq?url=http://example.com/', params=postdata)

        assert res.text == '\
GET /example.html HTTP/1.0\r\n\
Host: example.com\r\n\
Foo: Bar\r\n\
\r\n\
'


class TestPostQueryExtract(object):
    @classmethod
    def setup_class(cls):
        cls.post_data = b'foo=bar&dir=%2Fbaz'
        cls.binary_post_data = b'\x816l`L\xa04P\x0e\xe0r\x02\xb5\x89\x19\x00fP\xdb\x0e\xb0\x02,'

    def test_post_extract_1(self):
        mq = MethodQueryCanonicalizer('POST', 'application/x-www-form-urlencoded',
                                len(self.post_data), BytesIO(self.post_data))

        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST&foo=bar&dir=/baz'

        assert mq.append_query('http://example.com/?123=ABC') == 'http://example.com/?123=ABC&__wb_method=POST&foo=bar&dir=/baz'

    def test_post_extract_json(self):
        post_data = b'{"a": "b", "c": {"a": 2}, "d": "e"}'
        mq = MethodQueryCanonicalizer('POST', 'application/json',
                                len(post_data), BytesIO(post_data))

        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST&a=b&a.2_=2&d=e'


    def test_put_extract_method(self):
        mq = MethodQueryCanonicalizer('PUT', 'application/x-www-form-urlencoded',
                                len(self.post_data), BytesIO(self.post_data))

        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=PUT&foo=bar&dir=/baz'

    def test_post_extract_non_form_data_1(self):
        mq = MethodQueryCanonicalizer('POST', 'application/octet-stream',
                                len(self.post_data), BytesIO(self.post_data))

        #base64 encoded data
        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST&__wb_post_data=Zm9vPWJhciZkaXI9JTJGYmF6'

    def test_post_extract_non_form_data_2(self):
        mq = MethodQueryCanonicalizer('POST', 'text/plain',
                                len(self.post_data), BytesIO(self.post_data))

        #base64 encoded data
        assert mq.append_query('http://example.com/pathbar?id=123') == 'http://example.com/pathbar?id=123&__wb_method=POST&__wb_post_data=Zm9vPWJhciZkaXI9JTJGYmF6'

    def test_post_extract_length_invalid_ignore(self):
        mq = MethodQueryCanonicalizer('POST', 'application/x-www-form-urlencoded',
                                0, BytesIO(self.post_data))

        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST'

        mq = MethodQueryCanonicalizer('POST', 'application/x-www-form-urlencoded',
                                'abc', BytesIO(self.post_data))

        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST'

    def test_post_extract_length_too_short(self):
        mq = MethodQueryCanonicalizer('POST', 'application/x-www-form-urlencoded',
                                len(self.post_data) - 4, BytesIO(self.post_data))

        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST&foo=bar&dir=%2'

    def test_post_extract_length_too_long(self):
        mq = MethodQueryCanonicalizer('POST', 'application/x-www-form-urlencoded',
                                len(self.post_data) + 4, BytesIO(self.post_data))

        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST&foo=bar&dir=/baz'

    def test_post_extract_malformed_form_data(self):
        mq = MethodQueryCanonicalizer('POST', 'application/x-www-form-urlencoded',
                                len(self.binary_post_data), BytesIO(self.binary_post_data))

        #base64 encoded data
        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST&__wb_post_data=gTZsYEygNFAO4HICtYkZAGZQ2w6wAiw='

    def test_post_extract_no_boundary_in_multipart_form_mimetype(self):
        mq = MethodQueryCanonicalizer('POST', 'multipart/form-data',
                                len(self.post_data), BytesIO(self.post_data))

        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=POST&__wb_post_data=Zm9vPWJhciZkaXI9JTJGYmF6'


    def test_options(self):
        mq = MethodQueryCanonicalizer('OPTIONS', '', 0, BytesIO())
        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=OPTIONS'

    def test_head(self):
        mq = MethodQueryCanonicalizer('HEAD', '', 0, BytesIO())
        assert mq.append_query('http://example.com/') == 'http://example.com/?__wb_method=HEAD'

    def test_amf_parse(self):
        mq = MethodQueryCanonicalizer('POST', 'application/x-amf', 0, BytesIO())

        req = Request(target='t', body="")
        ev_1 = Envelope(AMF3)
        ev_1['/0'] = req

        req = Request(target='t', body="alt_content")
        ev_2 = Envelope(AMF3)
        ev_2['/0'] = req

        assert mq.amf_parse(encode(ev_1).getvalue(), None) != \
               mq.amf_parse(encode(ev_2).getvalue(), None)
