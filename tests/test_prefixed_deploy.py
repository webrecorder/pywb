from .base_config_test import BaseConfigTest, fmod


# ============================================================================
class TestPrefixedDeploy(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestPrefixedDeploy, cls).setup_class('config_test.yaml')

    def get(self, url, fmod=''):
        return super(TestPrefixedDeploy, self).get(url, fmod,
                        extra_environ={'SCRIPT_NAME': '/prefix',
                                       'REQUEST_URI': 'http://localhost:80/prefix' + url})

    def test_home(self):
        resp = self.get('/prefix/')
        print(resp.text)
        self._assert_basic_html(resp)
        assert '/prefix/pywb' in resp.text

    def test_pywb_root(self):
        resp = self.get('/prefix/pywb/')
        self._assert_basic_html(resp)
        assert 'Search' in resp.text

    def test_calendar_query(self):
        resp = self.get('/prefix/pywb/*/iana.org')
        self._assert_basic_html(resp)

        assert '/prefix/static/query.js' in resp.text

    def test_replay_content(self, fmod):
        resp = self.get('/prefix/pywb/20140127171238{0}/http://www.iana.org/', fmod)
        self._assert_basic_html(resp)

        assert '"20140127171238"' in resp.text, resp.text
        assert "'http://localhost:80/prefix/static/wombat.js'" in resp.text
        assert "'http://localhost:80/prefix/static/default_banner.js'" in resp.text
        assert '"http://localhost:80/prefix/static/"' in resp.text
        assert '"http://localhost:80/prefix/pywb/"' in resp.text
        assert 'WBWombatInit' in resp.text, resp.text
        assert '"/prefix/pywb/20140127171238{0}/http://www.iana.org/time-zones"'.format(fmod) in resp.text, resp.text

    def test_static_content(self):
        resp = self.get('/prefix/static/default_banner.css')
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'
        assert resp.content_length > 0


