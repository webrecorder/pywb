import webtest

from pywb.perms.perms_handler import create_perms_checker_app
from pywb.perms.perms_handler import ALLOW, BLOCK
from pywb.framework.wsgi_wrappers import init_app

class TestPermsApp:
    TEST_CONFIG = 'tests/test_config.yaml'

    def setup(self):
        self.app = init_app(create_perms_checker_app,
                            load_yaml=True,
                            config_file=self.TEST_CONFIG)

        self.testapp = webtest.TestApp(self.app)


    def test_allow(self):
        resp = self.testapp.get('/check-access/http://example.com')

        assert resp.content_type == 'application/json'

        assert ALLOW in resp.body


    def test_allow_with_timestamp(self):
        resp = self.testapp.get('/check-access/20131024000102/http://example.com')

        assert resp.content_type == 'application/json'

        assert ALLOW in resp.body


    def test_block_with_timestamp(self):
        resp = self.testapp.get('/check-access/20131024000102/http://www.iana.org/_img/bookmark_icon.ico')

        assert resp.content_type == 'application/json'

        assert BLOCK in resp.body


    def test_bad_url(self):
        resp = self.testapp.get('/check-access/@#$', expect_errors=True, status = 400)

        assert resp.status_int == 400

        assert 'Invalid Url: http://@' in resp.body


    def test_not_found(self):
        resp = self.testapp.get('/check-access/#abc', expect_errors=True, status = 404)

        assert resp.status_int == 404
