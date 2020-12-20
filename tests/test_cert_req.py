from .base_config_test import BaseConfigTest

# ============================================================================
class TestCertReq(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestCertReq, cls).setup_class('config_test_cert_req.yaml')

    def test_expired_cert(self):
        resp = self.testapp.get('/live/mp_/https://expired.badssl.com/', status='*')

        assert resp.status_int == 400

    def test_good_cert(self):
        resp = self.testapp.get('/live/mp_/https://www.google.com/', status='*')

        assert resp.status_int >= 200 and resp.status_int < 400
