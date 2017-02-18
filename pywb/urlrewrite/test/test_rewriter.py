from gevent import monkey; monkey.patch_all(thread=False)

from pywb.webagg.test.testutils import LiveServerTests, BaseTestClass
from pywb.webagg.test.testutils import FakeRedisTests

from pywb.urlrewrite.frontendapp import FrontEndApp

import os
import webtest


LIVE_CONFIG = {'collections': {'live': '$live'}}


class TestRewriter(FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRewriter, cls).setup_class()

        #cls.app = RWApp.create_app(replay_port=cls.server.port)
        #cls.testapp = webtest.TestApp(cls.app.app)
        cls.testapp = webtest.TestApp(FrontEndApp(custom_config=LIVE_CONFIG,
                                                  config_file=None))

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

    #def test_cookie_track_1(self):
    #    resp = self.testapp.get('/live/mp_/https://twitter.com/')

    #    assert resp.headers['set-cookie'] != None

