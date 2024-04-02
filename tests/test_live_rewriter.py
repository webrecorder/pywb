#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .base_config_test import BaseConfigTest, fmod_sl
from pywb.warcserver.test.testutils import HttpBinLiveTests

from pywb.utils.geventserver import GeventServer
import pytest
import os
import sys
import six


# ============================================================================
def header_test_server(environ, start_response):
    headers = []
    if environ['PATH_INFO'] == '/unicode':
        body = b'body'
        value = u'⛄'
        value = value.encode('utf-8')
        if six.PY3:
            value = value.decode('latin-1')

        headers = [('Content-Length', str(len(body))),
                   ('x-utf-8', value)]

    elif environ['PATH_INFO'] == '/html-title':
        body = b'<html><title>Test&#39;Title</title></html>'

        headers = [('Content-Length', str(len(body))),
                   ('Content-Type', 'text/html')]

    start_response('200 OK', headers=headers)
    return [body]


# ============================================================================
def cookie_test_server(environ, start_response):
    body = 'cookie value: ' + environ.get('HTTP_COOKIE', '')
    body = body.encode('utf-8')
    headers = [('Content-Length', str(len(body))),
               ('Content-Type', 'text/plain')]

    if b'testcookie' not in body:
        headers.append(('Set-Cookie', 'testcookie=cookie-val; Path=/; Domain=.example.com'))

    start_response('200 OK', headers=headers)
    return [body]


# ============================================================================
class TestLiveRewriter(HttpBinLiveTests, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        cls.lint_app = False
        super(TestLiveRewriter, cls).setup_class('config_test.yaml')
        cls.header_test_serv = GeventServer(header_test_server)
        cls.cookie_test_serv = GeventServer(cookie_test_server)

    @classmethod
    def teardown_class(cls):
        cls.header_test_serv.stop()
        cls.cookie_test_serv.stop()
        super(TestLiveRewriter, cls).teardown_class()

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
        resp = self.get('/live/{0}httpbin.org/get?val=abc%23%23xyz', fmod_sl)
        assert 'get?val=abc%23%23xyz"' in resp.text
        assert '"val": "abc##xyz"' in resp.text
        #assert '"http://httpbin.org/anything/abc##xyz"' in resp.text
        assert resp.status_int == 200

    def test_live_head(self, fmod_sl):
        resp = self.head('/live/{0}httpbin.org/get?foo=bar', fmod_sl)
        assert resp.status_int == 200

    # Following tests are temporarily commented out because latest version of PSF httpbin
    # now returns 400 if content-length header isn't parsable as an int

    # @pytest.mark.skipif(sys.version_info < (3,0), reason='does not respond in 2.7')
    # def test_live_bad_content_length(self, fmod_sl):
    #     resp = self.get('/live/{0}httpbin.org/response-headers?content-length=149,149', fmod_sl, status=200)
    #     assert resp.headers['Content-Length'] == '149'

    #     resp = self.get('/live/{0}httpbin.org/response-headers?Content-Length=xyz', fmod_sl, status=200)
    #     assert resp.headers['Content-Length'] == '90'

    # @pytest.mark.skipif(sys.version_info < (3,0), reason='does not respond in 2.7')
    # def test_live_bad_content_length_with_range(self, fmod_sl):
    #     resp = self.get('/live/{0}httpbin.org/response-headers?content-length=149,149', fmod_sl,
    #                     headers={'Range': 'bytes=0-'}, status=206)
    #     assert resp.headers['Content-Length'] == '149'
    #     assert resp.headers['Content-Range'] == 'bytes 0-148/149'

    #     resp = self.get('/live/{0}httpbin.org/response-headers?Content-Length=xyz', fmod_sl,
    #                     headers={'Range': 'bytes=0-'}, status=206)
    #     assert resp.headers['Content-Length'] == '90'
    #     assert resp.headers['Content-Range'] == 'bytes 0-89/90'

    def test_custom_unicode_header(self, fmod_sl):
        value = u'⛄'
        value = value.encode('utf-8')
        if six.PY3:
            value = value.decode('latin-1')

        resp = self.get('/live/{0}http://localhost:%s/unicode' % self.header_test_serv.port, fmod_sl)
        assert resp.headers['x-utf-8'] == value

    def test_domain_cookie(self, fmod_sl):
        resp = self.get('/live/{0}http://localhost:%s/' % self.cookie_test_serv.port, fmod_sl,
                        headers={'Host': 'example.com'})

        assert resp.headers['Set-Cookie'] == 'testcookie=cookie-val; Path=/live/{0}http://localhost:{1}/'.format(fmod_sl, self.cookie_test_serv.port)
        assert resp.text == 'cookie value: '

        resp = self.get('/live/{0}http://localhost:%s/' % self.cookie_test_serv.port, fmod_sl,
                        headers={'Host': 'example.com'})

        assert resp.text == 'cookie value: testcookie=cookie-val'

        resp = self.get('/live/{0}http://localhost:%s/' % self.cookie_test_serv.port, fmod_sl,
                        headers={'Host': 'sub.example.com'})

        assert 'Set-Cookie' not in resp.headers
        assert resp.text == 'cookie value: testcookie=cookie-val'

    def test_fetch_page_with_html_title(self, fmod_sl):
        resp = self.get('/live/{0}http://localhost:%s/html-title' % self.header_test_serv.port, fmod_sl,
                        headers={'X-Wombat-History-Page': 'http://localhost:{0}/html-title'.format(self.header_test_serv.port),
                                })
        assert resp.json == {'title': "Test'Title"}

    def test_fetch_page_with_title(self, fmod_sl):
        resp = self.get('/live/{0}http://httpbin.org/html', fmod_sl,
                        headers={'X-Wombat-History-Page': 'http://httpbin.org/html',
                                 'X-Wombat-History-Title': 'Test%20Title',
                                })
        assert resp.json == {'title': 'Test Title'}

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

    @pytest.mark.skipif(os.environ.get('CI') is not None, reason='Skip Test on CI')
    def test_live_video_info(self):
        pytest.importorskip('youtube_dl')
        resp = self.testapp.get('/live/vi_/https://www.youtube.com/watch?v=DjFZyFWSt1M')
        assert resp.status_int == 200
        assert resp.content_type == 'application/vnd.youtube-dl_formats+json', resp.content_type

    def test_deflate(self, fmod_sl):
        resp = self.get('/live/{0}http://httpbin.org/deflate', fmod_sl)
        assert b'"deflated": true' in resp.body

    def test_live_origin_and_referrer(self, fmod_sl):
        headers = {'Referer': 'http://localhost:80/live/{0}http://example.com/test'.format(fmod_sl),
                   'Origin': 'http://localhost:80'
                  }

        resp = self.get('/live/{0}http://httpbin.org/get?test=headers', fmod_sl, headers=headers)

        assert resp.json['headers']['Referer'] == 'http://example.com/test'
        assert resp.json['headers']['Origin'] == 'http://example.com'

    def test_live_origin_no_referrer(self, fmod_sl):
        headers = {'Origin': 'http://localhost:80'}

        resp = self.get('/live/{0}http://httpbin.org/get?test=headers', fmod_sl, headers=headers)

        assert resp.json['headers']['Origin'] == 'http://httpbin.org'


