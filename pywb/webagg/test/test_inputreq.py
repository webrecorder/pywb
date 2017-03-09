from pywb.webagg.inputrequest import DirectWSGIInputRequest, POSTInputRequest
from werkzeug.routing import Map, Rule

import webtest
import traceback
from six.moves.urllib.parse import parse_qsl


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
    def setup(self):
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

