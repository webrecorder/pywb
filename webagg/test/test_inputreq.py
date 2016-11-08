from webagg.inputrequest import DirectWSGIInputRequest, POSTInputRequest
from bottle import Bottle, request, response, debug
import webtest
import traceback


#=============================================================================
class InputReqApp(object):
    def __init__(self):
        self.application = Bottle()
        debug(True)

        @self.application.route('/test/<url:re:.*>', 'ANY')
        def direct_input_request(url=''):
            inputreq = DirectWSGIInputRequest(request.environ)
            response['Content-Type'] = 'text/plain; charset=utf-8'
            return inputreq.reconstruct_request(url)

        @self.application.route('/test-postreq', 'POST')
        def post_fullrequest():
            params = dict(request.query)
            inputreq = POSTInputRequest(request.environ)
            response['Content-Type'] = 'text/plain; charset=utf-8'
            return inputreq.reconstruct_request(params.get('url'))


#=============================================================================
class TestInputReq(object):
    def setup(self):
        self.app = InputReqApp()
        self.testapp = webtest.TestApp(self.app.application)

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

