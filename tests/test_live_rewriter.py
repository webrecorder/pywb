from pywb.webapp.live_rewrite_handler import RewriteHandler
from pywb.apps.cli import LiveCli
from pywb.framework.wsgi_wrappers import init_app
import webtest
import pywb.rewrite.rewrite_live

#=================================================================
class MockYTDWrapper(object):
    def extract_info(self, url):
        return {'mock': 'youtube_dl_data'}


pywb.rewrite.rewrite_live.youtubedl = MockYTDWrapper()


def setup_module():
    global app
    global testapp
    app = LiveCli(['-f']).application
    testapp = webtest.TestApp(app)


#=================================================================
class TestLiveRewriter:
    def setup(self):
        self.app = app
        self.testapp = testapp

    def test_live_live_1(self):
        headers = [('User-Agent', 'python'), ('Referer', 'http://localhost:80/live/other.example.com')]
        resp = self.testapp.get('/live/mp_/http://example.com/', headers=headers)
        assert resp.status_int == 200

    def test_live_live_redirect_2(self):
        resp = self.testapp.get('/live/mp_/http://httpbin.org/redirect-to?url=http://example.com/')
        assert resp.status_int == 302

    def test_live_live_post(self):
        resp = self.testapp.post('/live/mp_/httpbin.org/post', {'foo': 'bar', 'test': 'abc'})
        assert resp.status_int == 200
        resp.charset = 'utf-8'
        assert '"foo": "bar"' in resp.text
        assert '"test": "abc"' in resp.text
        assert resp.status_int == 200

    def test_live_live_frame(self):
        resp = self.testapp.get('/live/http://example.com/')
        assert resp.status_int == 200
        resp.charset = 'utf-8'
        assert '<iframe ' in resp.text
        assert 'src="http://localhost:80/live/mp_/http://example.com/"' in resp.text, resp.text

    def test_live_invalid(self):
        resp = self.testapp.get('/live/mp_/http://abcdef', status=400)
        assert resp.status_int == 400

    def test_live_invalid_2(self):
        resp = self.testapp.get('/live/mp_/@#$@#$', status=400)
        assert resp.status_int == 400

    def test_live_video_info(self):
        resp = self.testapp.get('/live/vi_/https://www.youtube.com/watch?v=DjFZyFWSt1M')
        assert resp.status_int == 200
        assert resp.content_type == RewriteHandler.YT_DL_TYPE, resp.content_type

    def test_deflate(self):
        resp = self.testapp.get('/live/mp_/http://httpbin.org/deflate')
        assert b'"deflated": true' in resp.body
