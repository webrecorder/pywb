from pywb.webapp.live_rewrite_handler import create_live_rewriter_app
from pywb.framework.wsgi_wrappers import init_app
import webtest

class TestLiveRewriter:
    def setup(self):
        self.app = init_app(create_live_rewriter_app, load_yaml=False)
        self.testapp = webtest.TestApp(self.app)

    def test_live_rewrite_1(self):
        headers = [('User-Agent', 'python'), ('Referer', 'http://localhost:80/rewrite/other.example.com')]
        resp = self.testapp.get('/rewrite/mp_/http://example.com/', headers=headers)
        assert resp.status_int == 200

    def test_live_rewrite_redirect_2(self):
        resp = self.testapp.get('/rewrite/mp_/http://facebook.com/')
        assert resp.status_int == 301

    def test_live_rewrite_frame(self):
        resp = self.testapp.get('/rewrite/http://example.com/')
        assert resp.status_int == 200
        assert '<iframe ' in resp.body
        assert 'src="/rewrite/mp_/http://example.com/"' in resp.body


