from gevent import monkey; monkey.patch_all(thread=False)

from pywb.warcserver.test.testutils import LiveServerTests, BaseTestClass
from pywb.warcserver.test.testutils import FakeRedisTests

from pywb.apps.frontendapp import FrontEndApp

import os
import webtest


LIVE_CONFIG = {'collections': {'live': '$live'}}


class TestRewriterApp(FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRewriterApp, cls).setup_class()

        #cls.app = RWApp.create_app(replay_port=cls.server.port)
        #cls.testapp = webtest.TestApp(cls.app.app)
        cls.testapp = webtest.TestApp(FrontEndApp(custom_config=LIVE_CONFIG,
                                                  config_file=None))

    def test_replay(self):
        resp = self.testapp.get('/live/mp_/https://example-com.webrecorder.net/')
        resp.charset = 'utf-8'

        assert '"http://localhost:80/live/mp_/https://www.iana.org/domains/example"' in resp.text

        assert '"https://example-com.webrecorder.net/"' in resp.text

    def test_top_frame(self):
        resp = self.testapp.get('/live/https://example-com.webrecorder.net/')
        resp.charset = 'utf-8'

        assert '"https://example-com.webrecorder.net/"' in resp.text

    #def test_cookie_track_1(self):
    #    resp = self.testapp.get('/live/mp_/https://twitter.com/')

    #    assert resp.headers['set-cookie'] != None

