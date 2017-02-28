from pytest import raises
import webtest
import base64

from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app
from pywb.cdx.cdxobject import CDXObject

from pywb.utils.loaders import to_native_str

from .server_mock import make_setup_module, BaseIntegration

setup_module = make_setup_module('tests/test_config.yaml')


class TestProxyHttpAuth(BaseIntegration):
    def _assert_basic_html(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert resp.content_length > 0

    def _assert_basic_text(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/plain'
        assert resp.content_length > 0

        assert 'proxy_magic = ""' in resp.text
        assert 'wb.js' in resp.text

    def b64encode(self, string):
        return to_native_str(base64.b64encode(string.encode('utf-8')))

    # 'Simulating' proxy by settings REQUEST_URI explicitly to http:// url and no SCRIPT_NAME
    # would be nice to be able to test proxy more
    def test_proxy_replay(self):
        resp = self.testapp.get('/x-ignore-this-x', extra_environ = dict(REQUEST_URI = 'http://www.iana.org/domains/idn-tables', SCRIPT_NAME = ''))
        self._assert_basic_html(resp)

        assert '"20140126201127"' in resp.text, resp.text

    def test_proxy_replay_auth_filtered(self):
        headers = [('Proxy-Authorization', 'Basic ' + self.b64encode('pywb-filt-2:'))]
        resp = self.testapp.get('/x-ignore-this-x', headers = headers,
                                extra_environ = dict(REQUEST_URI = 'http://www.iana.org/', SCRIPT_NAME = ''))

        self._assert_basic_html(resp)

        assert '"20140126200624"' in resp.text

    def test_proxy_replay_auth(self):
        headers = [('Proxy-Authorization', 'Basic ' + self.b64encode('pywb'))]
        resp = self.testapp.get('/x-ignore-this-x', headers = headers,
                                extra_environ = dict(REQUEST_URI = 'http://www.iana.org/', SCRIPT_NAME = ''))

        self._assert_basic_html(resp)

        assert '"20140127171238"' in resp.text

    def test_proxy_replay_auth_no_coll(self):
        headers = [('Proxy-Authorization', 'Basic ' + self.b64encode('no-such-coll'))]
        resp = self.testapp.get('/x-ignore-this-x', headers = headers,
                                extra_environ = dict(REQUEST_URI = 'http://www.iana.org/', SCRIPT_NAME = ''),
                                status=407)

        assert resp.status_int == 407

    def test_proxy_replay_auth_invalid_1(self):
        headers = [('Proxy-Authorization', 'abc' + self.b64encode('no-such-coll'))]
        resp = self.testapp.get('/x-ignore-this-x', headers = headers,
                                extra_environ = dict(REQUEST_URI = 'http://www.iana.org/', SCRIPT_NAME = ''),
                                status=407)

        assert resp.status_int == 407

    def test_proxy_replay_auth_invalid_2(self):
        headers = [('Proxy-Authorization', 'basic')]
        resp = self.testapp.get('/x-ignore-this-x', headers = headers,
                                extra_environ = dict(REQUEST_URI = 'http://www.iana.org/', SCRIPT_NAME = ''),
                                status=407)


    def test_proxy_connect_unsupported(self):
        resp = self.testapp.request('/x-ignore-this-x', method='CONNECT',
                                    environ=dict(REQUEST_URI='example:443', SCRIPT_NAME=''),
                                    status=405)

        assert resp.status_int == 405
