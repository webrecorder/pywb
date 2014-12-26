from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

from server_thread import ServerThreadRunner

from pywb.webapp.live_rewrite_handler import create_live_rewriter_app, RewriteHandler

from pywb.framework.wsgi_wrappers import init_app
import webtest
import shutil

import pywb.webapp.live_rewrite_handler


#=================================================================

#class ProxyServer(ThreadingMixIn, HTTPServer):
class ProxyServer(HTTPServer):
    pass


class ProxyRequest(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.server.force_err:
            # just close connection
            self.wfile.close()
            return

        buff = ''
        buff += self.command + ' ' + self.path + ' ' + self.request_version + '\n'
        for n in self.headers:
            buff += n + ': ' + self.headers[n] + '\n'

        self.server.requestlog.append(buff)

        self.send_response(200)

        self.send_header('x-proxy', 'test')
        self.send_header('content-length', str(len(buff)))
        self.send_header('content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(buff)
        self.wfile.close()

    def do_PUTMETA(self):
        self.do_GET()


#=================================================================
class TestProxyLiveRewriter:
    def setup(self):
        self.requestlog = []
        self.cache = {}

        def make_httpd(app):
            proxyserv = ProxyServer(('', 0), ProxyRequest)
            proxyserv.requestlog = self.requestlog
            proxyserv.force_err = False
            self.proxyserv = proxyserv
            return proxyserv

        self.server = ServerThreadRunner(make_httpd)

        self.app = init_app(create_live_rewriter_app, load_yaml=False,
                           config=dict(framed_replay=True,
                           proxyhostport=self.server.proxy_dict))

        def create_cache():
            return self.cache

        pywb.webapp.live_rewrite_handler.create_cache = create_cache

        self.testapp = webtest.TestApp(self.app)

    def teardown(self):
        self.server.stop_thread()

    def test_echo_proxy_referrer(self):
        headers = [('User-Agent', 'python'), ('Referer', 'http://localhost:80/rewrite/other.example.com')]
        resp = self.testapp.get('/rewrite/http://example.com/', headers=headers)

        # ensure just one request
        assert len(self.requestlog) == 1

        # equal to returned response (echo)
        assert self.requestlog[0] == resp.body
        assert resp.headers['x-archive-orig-x-proxy'] == 'test'

        assert resp.body.startswith('GET http://example.com/ HTTP/1.1')
        assert 'referer: http://other.example.com' in resp.body

        assert len(self.cache) == 0

    def test_echo_proxy_start_unbounded_remove_range(self):
        headers = [('Range', 'bytes=0-')]
        resp = self.testapp.get('/rewrite/http://example.com/', headers=headers)

        # actual response is with range
        assert resp.status_int == 206
        assert 'Content-Range' in resp.headers
        assert resp.headers['Accept-Ranges'] == 'bytes'

        assert len(self.requestlog) == 1

        # proxied, but without range
        assert self.requestlog[0] == resp.body
        assert resp.headers['x-archive-orig-x-proxy'] == 'test'

        assert self.requestlog[0].startswith('GET http://example.com/ HTTP/1.1')
        assert 'range: ' not in self.requestlog[0]

        assert len(self.cache) == 0

    def test_echo_proxy_bounded_noproxy_range(self):
        headers = [('Range', 'bytes=10-1000')]
        resp = self.testapp.get('/rewrite/http://example.com/foobar', headers=headers)

        # actual response is with range
        assert resp.status_int == 206
        assert 'Content-Range' in resp.headers
        assert resp.headers['Accept-Ranges'] == 'bytes'

        # not from proxy
        assert 'x-archive-orig-x-proxy' not in resp.headers

        # proxy receives a request also, but w/o range
        assert len(self.requestlog) == 1

        # proxy receives different request than our response
        assert self.requestlog[0] != resp.body

        assert self.requestlog[0].startswith('GET http://example.com/foobar HTTP/1.1')

        # no range request
        assert 'range: ' not in self.requestlog[0]

        # r: key cached
        assert len(self.cache) == 1
        assert RewriteHandler.create_cache_key('r:', 'http://example.com/foobar') in self.cache

        # Second Request
        # clear log
        self.requestlog.pop()
        headers = [('Range', 'bytes=101-150')]
        resp = self.testapp.get('/rewrite/http://example.com/foobar', headers=headers)

        # actual response is with range
        assert resp.status_int == 206
        assert 'Content-Range' in resp.headers
        assert resp.headers['Accept-Ranges'] == 'bytes'

        # not from proxy
        assert 'x-archive-orig-x-proxy' not in resp.headers

        # already pinged proxy, no additional requests set to proxy
        assert len(self.requestlog) == 0
        assert len(self.cache) == 1

    def test_echo_proxy_video_info(self):
        resp = self.testapp.get('/rewrite/vi_/https://www.youtube.com/watch?v=DjFZyFWSt1M')
        assert resp.status_int == 200
        assert resp.content_type == RewriteHandler.YT_DL_TYPE, resp.content_type

        assert len(self.requestlog) == 1
        assert self.requestlog[0].startswith('PUTMETA http://www.youtube.com/watch?v=DjFZyFWSt1M HTTP/1.1')

        # second request, not sent to proxy
        resp = self.testapp.get('/rewrite/vi_/https://www.youtube.com/watch?v=DjFZyFWSt1M')
        assert len(self.requestlog) == 1

        # v: video info cache
        assert len(self.cache) == 1
        assert RewriteHandler.create_cache_key('v:', 'https://www.youtube.com/watch?v=DjFZyFWSt1M') in self.cache

    def test_echo_proxy_video_with_referrer(self):
        headers = [('Range', 'bytes=1000-2000'), ('Referer', 'http://localhost:80/rewrite/https://example.com/')]
        resp = self.testapp.get('/rewrite/http://www.youtube.com/watch?v=DjFZyFWSt1M', headers=headers)

        # not from proxy
        assert 'x-archive-orig-x-proxy' not in resp.headers

        # proxy receives two requests
        assert len(self.requestlog) == 2

        # first, a video info request recording the page
        assert self.requestlog[0].startswith('PUTMETA http://example.com/ HTTP/1.1')

        # second, non-ranged request for page
        assert self.requestlog[1].startswith('GET http://www.youtube.com/watch?v=DjFZyFWSt1M HTTP/1.1')
        assert 'range' not in self.requestlog[1]

        # both video info and range cached
        assert len(self.cache) == 2
        assert RewriteHandler.create_cache_key('v:', 'http://www.youtube.com/watch?v=DjFZyFWSt1M') in self.cache
        assert RewriteHandler.create_cache_key('r:', 'http://www.youtube.com/watch?v=DjFZyFWSt1M') in self.cache


    def test_echo_proxy_error(self):
        headers = [('Range', 'bytes=1000-2000'), ('Referer', 'http://localhost:80/rewrite/https://example.com/')]

        self.proxyserv.force_err = True
        resp = self.testapp.get('/rewrite/http://www.youtube.com/watch?v=DjFZyFWSt1M', headers=headers)

        # not from proxy
        assert 'x-archive-orig-x-proxy' not in resp.headers

        # no proxy requests as we're forcing exception
        assert len(self.requestlog) == 0

        assert len(self.cache) == 0

