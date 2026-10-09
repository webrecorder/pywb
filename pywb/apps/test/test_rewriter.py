from gevent import monkey; monkey.patch_all(thread=False)

from pywb.warcserver.test.testutils import LiveServerTests, BaseTestClass
from pywb.warcserver.test.testutils import FakeRedisTests

from pywb.apps.frontendapp import FrontEndApp
from pywb.utils.geventserver import GeventServer

import os
import webtest


LIVE_CONFIG = {'collections': {'live': '$live'}}


def example_app(environ, start_response):
    # local stand-in for an example.com page
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [b'<html><body><a href="https://www.iana.org/domains/example">More information...</a></body></html>']


class TestRewriterApp(FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRewriterApp, cls).setup_class()

        #cls.app = RWApp.create_app(replay_port=cls.server.port)
        #cls.testapp = webtest.TestApp(cls.app.app)
        cls.testapp = webtest.TestApp(FrontEndApp(custom_config=LIVE_CONFIG,
                                                  config_file=None))

        cls.example_server = GeventServer(example_app)
        cls.example_url = 'http://localhost:{0}/'.format(cls.example_server.port)

    @classmethod
    def teardown_class(cls):
        cls.example_server.stop()
        super(TestRewriterApp, cls).teardown_class()

    def test_replay(self):
        resp = self.testapp.get('/live/mp_/' + self.example_url)
        resp.charset = 'utf-8'

        assert '"http://localhost:80/live/mp_/https://www.iana.org/domains/example"' in resp.text

        assert '"{0}"'.format(self.example_url) in resp.text

    def test_top_frame(self):
        resp = self.testapp.get('/live/' + self.example_url)
        resp.charset = 'utf-8'

        assert '"{0}"'.format(self.example_url) in resp.text

    #def test_cookie_track_1(self):
    #    resp = self.testapp.get('/live/mp_/https://twitter.com/')

    #    assert resp.headers['set-cookie'] != None

