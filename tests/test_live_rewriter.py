from .base_config_test import BaseConfigTest, fmod_sl


# ============================================================================
class TestLiveRewriter(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestLiveRewriter, cls).setup_class('config_test.yaml')

    def test_live_live_1(self, fmod_sl):
        headers = [('User-Agent', 'python'), ('Referer', 'http://localhost:80/live/other.example.com')]
        resp = self.get('/live/{0}http://example.com/', fmod_sl, headers=headers)
        assert resp.status_int == 200

    def test_live_live_redirect_2(self, fmod_sl):
        resp = self.get('/live/{0}http://httpbin.org/redirect-to?url=http://example.com/', fmod_sl)
        assert resp.status_int == 302

    def test_live_live_post(self, fmod_sl):
        resp = self.post('/live/{0}httpbin.org/post', fmod_sl, {'foo': 'bar', 'test': 'abc'})
        assert resp.status_int == 200
        resp.charset = 'utf-8'
        assert '"foo": "bar"' in resp.text
        assert '"test": "abc"' in resp.text
        assert resp.status_int == 200

    def test_live_anchor_encode(self, fmod_sl):
        resp = self.get('/live/{0}httpbin.org/anything/abc%23%23xyz', fmod_sl)
        assert '"http://httpbin.org/anything/abc##xyz"' in resp.text
        assert resp.status_int == 200

    def test_live_head(self, fmod_sl):
        resp = self.head('/live/{0}httpbin.org/anything/foo', fmod_sl)
        #assert '"http://httpbin.org/anything/foo"' in resp.text
        assert resp.status_int == 200

    def test_live_live_frame(self):
        resp = self.testapp.get('/live/http://example.com/')
        assert resp.status_int == 200
        resp.charset = 'utf-8'
        #assert '<iframe ' in resp.text
        assert '"http://localhost:80/live/"' in resp.text, resp.text
        assert '"http://example.com/"' in resp.text, resp.text

    def test_live_invalid(self, fmod_sl):
        resp = self.get('/live/{0}http://abcdef', fmod_sl, status=307)
        resp = resp.follow(status=400)
        assert resp.status_int == 400

    def test_live_invalid_2(self, fmod_sl):
        resp = self.get('/live/{0}@#$@#$', fmod_sl, status=307)
        resp = resp.follow(status=400)
        assert resp.status_int == 400

    def test_live_video_info(self):
        resp = self.testapp.get('/live/vi_/https://www.youtube.com/watch?v=DjFZyFWSt1M')
        assert resp.status_int == 200
        assert resp.content_type == 'application/vnd.youtube-dl_formats+json', resp.content_type

    def test_deflate(self, fmod_sl):
        resp = self.get('/live/{0}http://httpbin.org/deflate', fmod_sl)
        assert b'"deflated": true' in resp.body
