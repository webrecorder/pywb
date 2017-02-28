from pytest import raises
import webtest
import base64

from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app
from pywb.cdx.cdxobject import CDXObject

from six.moves.urllib.parse import urlsplit

from .server_mock import make_setup_module, BaseIntegration

setup_module = make_setup_module('tests/test_config_proxy_no_banner.yaml')

class TestProxyNoBanner(BaseIntegration):
    def get_url(self, uri, addr='127.0.0.1', server_protocol='HTTP/1.0', headers={}):
        parts = urlsplit(uri)
        env = dict(REQUEST_URI=uri, QUERY_STRING=parts.query, SCRIPT_NAME='',
                   SERVER_PROTOCOL=server_protocol, REMOTE_ADDR=addr)
        # 'Simulating' proxy by settings REQUEST_URI explicitly to full url with empty SCRIPT_NAME
        return self.testapp.get('/x-ignore-this-x', extra_environ=env, headers=headers)

    def test_proxy_chunked(self):
        resp = self.get_url('http://www.iana.org/_img/2013.1/icann-logo.svg', server_protocol='HTTP/1.1')
        assert resp.content_type == 'image/svg+xml'
        assert resp.headers['Transfer-Encoding'] == 'chunked'
        #assert 'Content-Length' not in resp.headers
        #assert int(resp.headers['Content-Length']) == len(resp.body)

    def test_proxy_buffered(self):
        resp = self.get_url('http://www.iana.org/_img/2013.1/icann-logo.svg', server_protocol='HTTP/1.0')
        assert resp.content_type == 'image/svg+xml'
        assert 'Transfer-Encoding' not in resp.headers
        assert int(resp.headers['Content-Length']) == len(resp.body)

    def test_proxy_html_url_only_rewrite_buffered(self):
        resp = self.get_url('http://www.iana.org/', server_protocol='HTTP/1.0')
        assert 'Transfer-Encoding' not in resp.headers
        assert int(resp.headers['Content-Length']) == len(resp.body)

    def test_proxy_js_url_only_rewrite_buffered(self):
        resp = self.get_url('http://www.iana.org/_js/2013.1/iana.js', server_protocol='HTTP/1.0')
        assert 'Transfer-Encoding' not in resp.headers
        assert int(resp.headers['Content-Length']) == len(resp.body)

    def test_proxy_js_url_only_rewrite_chunked(self):
        resp = self.get_url('http://www.iana.org/_js/2013.1/iana.js', server_protocol='HTTP/1.1')
        assert resp.headers['Transfer-Encoding'] == 'chunked'
        assert int(resp.headers['Content-Length']) == len(resp.body)

    def test_proxy_html_no_banner(self):
        resp = self.get_url('http://www.iana.org/')

        assert 'wombat' not in resp.text
        assert 'href="/protocols"' in resp.text

    def test_proxy_html_no_banner_with_prefix(self):
        resp = self.get_url('http://www.iana.org/', headers={'Pywb-Rewrite-Prefix': 'http://somehost/'})

        assert 'wombat' not in resp.text
        assert 'href="http://somehost/mp_/http://www.iana.org/protocols"' in resp.text, resp.text
