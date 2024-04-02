from .base_config_test import BaseConfigTest, fmod


# ============================================================================
class TestForceHttps(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestForceHttps, cls).setup_class('config_test.yaml')

    def test_force_https_replay_1(self, fmod):
        resp = self.get('/pywb/20140128051539{0}/http://example.com/', fmod,
                        headers={'X-Forwarded-Proto': 'https'})

        assert '"https://localhost:80/pywb/20140128051539{0}/http://www.iana.org/domains/example"'.format(fmod) in resp.text, resp.text


# ============================================================================
class TestForceHttpsConfig(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestForceHttpsConfig, cls).setup_class('config_test.yaml',
                                                     custom_config={'force_scheme': 'https'})

    def test_force_https_replay_1(self, fmod):
        resp = self.get('/pywb/20140128051539{0}/http://example.com/', fmod)

        assert '"https://localhost:80/pywb/20140128051539{0}/http://www.iana.org/domains/example"'.format(fmod) in resp.text, resp.text


# ============================================================================
class TestForceHttpsRedirect(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestForceHttpsRedirect, cls).setup_class('config_test_redirect_classic.yaml')

    def test_force_https_redirect_replay_1(self, fmod):
        resp = self.get('/pywb/20140128051539{0}/http://example.com/', fmod,
                        headers={'X-Forwarded-Proto': 'https'})

        assert resp.headers['Location'] == 'https://localhost:80/pywb/20140127171251{0}/http://example.com'.format(fmod)
        resp = resp.follow()

        assert resp.headers['Location'] == 'https://localhost:80/pywb/20140127171251{0}/http://example.com/'.format(fmod)
        resp = resp.follow()

        assert '"https://localhost:80/pywb/20140127171251{0}/http://www.iana.org/domains/example"'.format(fmod) in resp.text, resp.text


# ============================================================================
class TestForceHttpsRoot(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestForceHttpsRoot, cls).setup_class('config_test_root_coll.yaml')

    def test_force_https_root_replay_1(self, fmod):
        resp = self.get('/20140128051539{0}/http://www.iana.org/domains/example', fmod,
                        headers={'X-Forwarded-Proto': 'https'})

        assert resp.headers['Location'] == 'https://localhost:80/20140128051539{0}/http://www.iana.org/help/example-domains'.format(fmod)


