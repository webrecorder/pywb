from .base_config_test import BaseConfigTest, fmod

import webtest
import os

from six.moves.urllib.parse import urlencode


# ============================================================================
class TestEmbargoApp(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestEmbargoApp, cls).setup_class('config_test_access.yaml')

    def test_embargo_before(self):
        resp = self.testapp.get('/pywb-embargo-before/20140126201054mp_/http://www.iana.org/domains/reserved', status=404)

        resp = self.testapp.get('/pywb-embargo-before/20140127mp_/http://example.com/', status=200)
        assert resp.headers['Content-Location'] == 'http://localhost:80/pywb-embargo-before/20140127171251mp_/http://example.com'

    def test_embargo_after(self):
        resp = self.testapp.get('/pywb-embargo-after/20140126201054mp_/http://www.iana.org/domains/reserved', status=200)

        resp = self.testapp.get('/pywb-embargo-after/20140127mp_/http://example.com/', status=200)
        assert resp.headers['Content-Location'] == 'http://localhost:80/pywb-embargo-after/20130729195151mp_/http://test@example.com/'

    def test_embargo_older(self):
        resp = self.testapp.get('/pywb-embargo-older/20140126201054mp_/http://www.iana.org/domains/reserved', status=404)

        resp = self.testapp.get('/pywb-embargo-older/20140127mp_/http://example.com/', status=404)

    def test_embargo_newer(self):
        resp = self.testapp.get('/pywb-embargo-newer/20140126201054mp_/http://www.iana.org/domains/reserved', status=200)

        resp = self.testapp.get('/pywb-embargo-newer/20140127mp_/http://example.com/', status=200)
        assert resp.headers['Content-Location'] == 'http://localhost:80/pywb-embargo-newer/20140127171251mp_/http://example.com'

    def test_embargo_ignore_acl(self):
        # embargoed
        resp = self.testapp.get('/pywb-embargo-acl/20140126201054mp_/http://example.com/', status=404)

        # ignore embargo
        resp = self.testapp.get('/pywb-embargo-acl/20140126201054mp_/http://example.com/?example=2', status=200)


    def test_embargo_ignore_acl_with_header_only(self):
        # ignore embargo with custom header only
        headers = {"X-Pywb-ACL-User": "staff2"}
        resp = self.testapp.get('/pywb-embargo-acl/20140126201054mp_/http://example.com/?example=1', status=200, headers=headers)

        resp = self.testapp.get('/pywb-embargo-acl/20140126201054mp_/http://example.com/?example=1', status=404)





