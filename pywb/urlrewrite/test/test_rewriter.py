
from pywb.webagg.test.testutils import LiveServerTests, BaseTestClass
from pywb.webagg.test.testutils import FakeRedisTests

from .simpleapp import RWApp, debug

import os
import webtest


class TestRewriter(LiveServerTests, FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRewriter, cls).setup_class()
        #cls.upstream_url = 'http://localhost:{0}'.format(cls.server.port)
        #cls.upstream_url += '/{type}/resource/postreq?url={url}&closest={closest}'
        #cls.app = RWApp(cls.upstream_url)

        cls.app = RWApp.create_app(replay_port=cls.server.port)
        cls.testapp = webtest.TestApp(cls.app.app)
        debug(True)

    def test_replay(self):
        resp = self.testapp.get('/live/mp_/http://example.com/')
        resp.charset = 'utf-8'

        assert '"http://localhost:80/live/mp_/http://www.iana.org/domains/example"' in resp.text

        assert 'wbinfo.url = "http://example.com/"'

    def test_top_frame(self):
        resp = self.testapp.get('/live/http://example.com/')
        resp.charset = 'utf-8'

        assert '"http://localhost:80/live/mp_/http://example.com/"' in resp.text

        assert 'wbinfo.capture_url = "http://example.com/"' in resp.text

    def test_cookie_track_1(self):
        resp = self.testapp.get('/live/mp_/https://twitter.com/')

        assert resp.headers['set-cookie'] != None

