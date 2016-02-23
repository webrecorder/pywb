from pytest import raises
import webtest
import base64

from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app
from pywb.cdx.cdxobject import CDXObject

from six.moves.urllib.parse import urlsplit

from .server_mock import make_setup_module, BaseIntegration

setup_module = make_setup_module('tests/test_config_proxy_ip.yaml')


class TestProxyIPResolver(BaseIntegration):
    def _assert_basic_html(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert resp.content_length > 0
        assert 'proxy_magic = ""' in resp.text

    def _assert_basic_text(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/plain'
        assert resp.content_length > 0

    def get_url(self, uri, addr='127.0.0.1', status='*'):
        parts = urlsplit(uri)
        env = dict(REQUEST_URI=uri, QUERY_STRING=parts.query, SCRIPT_NAME='', REMOTE_ADDR=addr)
        # 'Simulating' proxy by settings REQUEST_URI explicitly to full url with empty SCRIPT_NAME
        return self.testapp.get('/x-ignore-this-x', extra_environ=env, status=status)

    def test_proxy_ip_default_ts(self):
        resp = self.get_url('http://www.iana.org/')
        self._assert_basic_html(resp)

        assert '"20140127171238"' in resp.text
        assert 'wb.js' in resp.text

    def test_proxy_ip_get_defaults(self):
        resp = self.get_url('http://info.pywb.proxy/')
        assert resp.content_type == 'application/json'
        assert resp.json == {'ip': '127.0.0.1', 'coll': None, 'ts': None}

    def test_proxy_ip_set_ts(self):
        resp = self.get_url('http://info.pywb.proxy/set?ts=1996')
        assert resp.content_type == 'application/json'
        assert resp.json == {'ip': '127.0.0.1', 'coll': None, 'ts': '1996'}

    def test_proxy_ip_set_ts_coll(self):
        resp = self.get_url('http://info.pywb.proxy/set?ts=1996&coll=all')
        assert resp.content_type == 'application/json'
        assert resp.json == {'ip': '127.0.0.1', 'coll': 'all', 'ts': '1996'}

    def test_proxy_ip_set_ts_coll_diff_ip(self):
        resp = self.get_url('http://info.pywb.proxy/set?ts=2006&coll=all', '127.0.0.2')
        assert resp.content_type == 'application/json'
        assert resp.json == {'ip': '127.0.0.2', 'coll': 'all', 'ts': '2006'}

        # from previous response
        resp = self.get_url('http://info.pywb.proxy/')
        assert resp.json == {'ip': '127.0.0.1', 'coll': 'all', 'ts': '1996'}

        resp = self.get_url('http://info.pywb.proxy/set?ip=127.0.0.2&ts=2005')
        assert resp.json == {'ip': '127.0.0.2', 'coll': 'all', 'ts': '2005'}

        resp = self.get_url('http://info.pywb.proxy/', '127.0.0.2')
        assert resp.json == {'ip': '127.0.0.2', 'coll': 'all', 'ts': '2005'}

    def test_proxy_ip_change_ts_for_ip(self):
        resp = self.get_url('http://info.pywb.proxy/set?ip=1.2.3.4&ts=20140126200624')
        assert resp.json == {'ip': '1.2.3.4', 'coll': None, 'ts': '20140126200624'}

        # different ts for this ip
        resp = self.get_url('http://www.iana.org/', '1.2.3.4')
        self._assert_basic_html(resp)

        assert '"20140126200624"' in resp.text

        # defaults for any other ip
        resp = self.get_url('http://www.iana.org/', '127.0.0.3')
        self._assert_basic_html(resp)
        assert '"20140127171238"' in resp.text

    def test_proxy_ip_delete_ip(self):
        resp = self.get_url('http://info.pywb.proxy/')
        assert resp.json == {'ip': '127.0.0.1', 'coll': 'all', 'ts': '1996'}

        resp = self.get_url('http://info.pywb.proxy/set?delete=true')
        assert resp.json == {'ip': '127.0.0.1', 'coll': None, 'ts': None}

        resp = self.get_url('http://info.pywb.proxy/')
        assert resp.json == {'ip': '127.0.0.1', 'coll': None, 'ts': None}

    def test_proxy_set_coll_invalid(self):
        resp = self.get_url('http://info.pywb.proxy/set?coll=invalid')
        assert resp.content_type == 'application/json'
        assert resp.json == {'ip': '127.0.0.1', 'coll': 'invalid', 'ts': None}

    def test_proxy_ip_invalid_coll(self):
        resp = self.get_url('http://www.iana.org/', status=500)
        assert 'Invalid Proxy Collection Specified: invalid' in resp.text


