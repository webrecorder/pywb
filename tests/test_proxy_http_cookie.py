from wsgiref.simple_server import make_server

import requests
from .server_thread import ServerThreadRunner


#=================================================================
TEST_CONFIG = 'tests/test_config_proxy_http_cookie.yaml'

server = None
sesh_key = None


#=================================================================
# Inited once per module
def setup_module():
    def make_httpd(app):
        return make_server('', 0, app)

    global server
    server = ServerThreadRunner(make_httpd, TEST_CONFIG)

def teardown_module():
    global server
    server.stop_thread()


#=================================================================
class TestProxyHttpCookie:
    def setup(self):
        self.session = requests.Session()

    def get_url(self, url):
        global sesh_key
        if sesh_key:
            self.session.headers.update({'Cookie': '__pywb_proxy_sesh=' + sesh_key})
            self.session.cookies.set('__pywb_proxy_sesh', sesh_key, domain='.pywb.proxy')

        return self.session.get(url,
                                proxies=server.proxy_dict)

    def post_url(self, url, data):
        global sesh_key
        if sesh_key:
            self.session.headers.update({'Cookie': '__pywb_proxy_sesh=' + sesh_key})
            self.session.cookies.set('__pywb_proxy_sesh', sesh_key, domain='.pywb.proxy')

        return self.session.post(url,
                                 data=data,
                                 proxies=server.proxy_dict)

    def _test_basic(self, resp, url):
        assert resp.status_code == 200
        assert 'Content-Length' in resp.headers
        assert resp.url == url

    def test_replay_no_coll(self):
        resp = self.get_url('http://iana.org/')
        self._test_basic(resp, 'http://select.pywb.proxy/http://iana.org/')

    def test_replay_set_older_coll(self):
        resp = self.get_url('http://older-set.pywb.proxy/http://iana.org/')
        self._test_basic(resp, 'http://iana.org/')
        assert '20140126200624' in resp.text

        sesh1 = self.session.cookies.get('__pywb_proxy_sesh', domain='.pywb.proxy')
        sesh2 = self.session.cookies.get('__pywb_proxy_sesh', domain='.iana.org')
        assert sesh1 and sesh1 == sesh2, self.session.cookies

        # store session cookie
        global sesh_key
        sesh_key = sesh1

        sesh2 = self.session.cookies.get('__pywb_proxy_sesh', domain='.iana.org')
        assert sesh_key == sesh2

    def test_replay_same_coll(self):
        resp = self.get_url('http://iana.org/')
        self._test_basic(resp, 'http://iana.org/')
        assert 'wbinfo.proxy_magic = "pywb.proxy";' in resp.text
        assert '20140126200624' in resp.text

    def test_replay_set_change_coll(self):
        resp = self.get_url('http://all-set.pywb.proxy/http://iana.org/')
        self._test_basic(resp, 'http://iana.org/')
        assert '20140127171238' in resp.text

        # verify still same session cookie
        sesh2 = self.session.cookies.get('__pywb_proxy_sesh', domain='.iana.org')
        global sesh_key
        assert sesh_key == sesh2

    def test_query(self):
        resp = self.get_url('http://query.pywb.proxy/*/http://iana.org/')
        self._test_basic(resp, 'http://query.pywb.proxy/*/http://iana.org/')
        assert 'text/html' in resp.headers['content-type']
        assert '20140126200624' in resp.text
        assert '20140127171238' in resp.text
        assert '<b>3</b> captures' in resp.text

    # testing via http here
    def test_change_timestamp(self):
        resp = self.get_url('http://query.pywb.proxy/20140126200624/http://iana.org/')
        self._test_basic(resp, 'http://iana.org/')
        assert 'Content-Length' in resp.headers
        assert '20140126200624' in resp.text

    def test_change_coll_same_ts(self):
        resp = self.get_url('http://all-set.pywb.proxy/iana.org/')
        self._test_basic(resp, 'http://iana.org/')
        assert 'Content-Length' in resp.headers
        assert '20140126200624' in resp.text

    # testing via http here
    def test_change_latest_ts(self):
        resp = self.get_url('http://query.pywb.proxy/http://iana.org/?_=1234')
        self._test_basic(resp, 'http://iana.org/?_=1234')
        assert 'Content-Length' in resp.headers
        assert '20140127171238' in resp.text

    def test_diff_url(self):
        resp = self.get_url('http://example.com/')
        self._test_basic(resp, 'http://example.com/')
        assert 'Content-Length' in resp.headers
        assert '20140127171251' in resp.text

    def test_post_replay_all_coll(self):
        resp = self.post_url('http://httpbin.org/post', data={'foo': 'bar', 'test': 'abc'})
        self._test_basic(resp, 'http://httpbin.org/post')
        assert 'application/json' in resp.headers['content-type']

    # Bounce back to select.pywb.proxy due to missing session
    def test_clear_key(self):
        # clear session key
        global sesh_key
        sesh_key = None

    def test_no_sesh_latest_bounce(self):
        resp = self.get_url('http://query.pywb.proxy/http://iana.org/')
        assert resp.url == 'http://select.pywb.proxy/http://iana.org/'

    def test_no_sesh_coll_change_bounce(self):
        resp = self.get_url('http://auto.pywb.proxy/http://iana.org/')
        assert resp.url == 'http://select.pywb.proxy/http://iana.org/'

    def test_no_sesh_ts_bounce(self):
        resp = self.get_url('http://query.pywb.proxy/20140126200624/http://iana.org/')
        assert resp.url == 'http://select.pywb.proxy/20140126200624/http://iana.org/'

    def test_no_sesh_query_bounce(self):
        resp = self.get_url('http://query.pywb.proxy/*/http://iana.org/')
        assert resp.url == 'http://select.pywb.proxy/http://query.pywb.proxy/*/http://iana.org/'

    # static replay
    def test_replay_static(self):
        resp = self.get_url('http://pywb.proxy/static/__pywb/wb.js')
        assert resp.status_code == 200
        assert 'function init_banner' in resp.text

    # download index page and cert downloads
    def test_replay_dl_page(self):
        resp = self.get_url('http://pywb.proxy/')
        assert resp.status_code == 200
        assert 'text/html' in resp.headers['content-type']
        assert 'Sorry' in resp.text

    def test_dl_pem(self):
        resp = self.get_url('http://pywb.proxy/pywb-ca.pem')
        assert resp.status_code == 404

    def test_dl_p12(self):
        resp = self.get_url('http://pywb.proxy/pywb-ca.p12')
        assert resp.status_code == 404
