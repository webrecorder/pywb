import webtest

from pywb.perms.perms_handler import create_perms_checker_app
from pywb.perms.perms_handler import ALLOW, BLOCK
from pywb.framework.wsgi_wrappers import init_app

from .server_mock import make_setup_module, BaseIntegration

setup_module = make_setup_module('tests/test_config.yaml', create_perms_checker_app)

class TestPermsApp(BaseIntegration):
    def test_allow(self):
        resp = self.testapp.get('/check-access/http://example.com')

        assert resp.content_type == 'application/json'

        assert ALLOW in resp.text


    def test_allow_with_timestamp(self):
        resp = self.testapp.get('/check-access/20131024000102/http://example.com')

        assert resp.content_type == 'application/json'

        assert ALLOW in resp.text


    def test_block_with_timestamp(self):
        resp = self.testapp.get('/check-access/20131024000102/http://www.iana.org/_img/bookmark_icon.ico')

        assert resp.content_type == 'application/json'

        assert BLOCK in resp.text

    # no longer 'bad' due since surt 0.3b
    #def test_bad_url(self):
    #    resp = self.testapp.get('/check-access/@#$', expect_errors=True, status = 400)

    #    assert resp.status_int == 404

    #    assert 'Invalid Url: http://@' in resp.text


    def test_not_found(self):
        resp = self.testapp.get('/check-access/#abc', expect_errors=True, status = 404)

        assert resp.status_int == 404
