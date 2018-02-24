from .base_config_test import BaseConfigTest, fmod

from pywb.warcserver.index.cdxobject import CDXObject


# ============================================================================
class TestPreferWithRedirects(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestPreferWithRedirects, cls).setup_class('config_test_redirect_classic.yaml')

    def _assert_pref_headers(self, resp, pref):
        assert resp.headers['Preference-Applied'] == pref
        assert 'Prefer' in resp.headers['Vary']

    def _assert_raw_memento(self, resp):
        self._assert_pref_headers(resp, 'raw')
        assert '"/time-zones"' in resp.text, resp.text
        assert 'wombat.js' not in resp.text

    def _assert_rewritten(self, resp, fmod):
        self._assert_pref_headers(resp, 'rewritten')

        assert '"20140127171238"' in resp.text
        assert 'wombat.js' in resp.text
        assert 'new _WBWombat' in resp.text, resp.text
        assert '/20140127171238{0}/http://www.iana.org/time-zones"'.format(fmod) in resp.text

    def _assert_redir_to_raw(self, resp):
        self._assert_pref_headers(resp, 'raw')

        assert resp.location.endswith('/pywb/20140127171238id_/http://www.iana.org/')
        resp = resp.follow()

        self._assert_raw_memento(resp)

    def _assert_redir_to_rewritten(self, resp, fmod):
        self._assert_pref_headers(resp, 'rewritten')

        assert resp.location.endswith('/pywb/20140127171238{0}/http://www.iana.org/'.format(fmod))
        resp = resp.follow()

        self._assert_rewritten(resp, fmod)

    def test_prefer_redir_timegate_raw(self, fmod):
        headers = {'Prefer': 'raw'}
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod_slash, headers=headers, status=307)

        self._assert_redir_to_raw(resp)

    def test_prefer_redir_timegate_rewritten(self, fmod):
        headers = {'Prefer': 'rewritten'}
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod_slash, headers=headers, status=307)

        self._assert_redir_to_rewritten(resp, fmod)

    def test_prefer_redir_memento_to_raw(self, fmod):
        headers = {'Prefer': 'raw'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=307)

        self._assert_redir_to_raw(resp)

    def test_prefer_redir_memento_redir_to_rewritten_diff_mod(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/20140127171238js_/http://www.iana.org/', fmod, headers=headers, status=307)

        self._assert_redir_to_rewritten(resp, fmod)

    def test_prefer_redir_memento_matches_rewritten(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_rewritten(resp, fmod)

    def test_prefer_redir_memento_matches_raw(self):
        headers = {'Prefer': 'raw'}
        resp = self.testapp.get('/pywb/20140127171238id_/http://www.iana.org/', headers=headers, status=200)

        self._assert_raw_memento(resp)

    def test_prefer_redir_invalid(self, fmod):
        headers = {'Prefer': 'unknown'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=400)


# ============================================================================
class TestPreferWithNoRedirects(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestPreferWithNoRedirects, cls).setup_class('config_test.yaml',
                                        custom_config={'enable_prefer': True})

    def _assert_pref_headers(self, resp, pref):
        assert resp.headers['Preference-Applied'] == pref
        assert 'Prefer' in resp.headers['Vary']

    def _assert_raw(self, resp):
        self._assert_pref_headers(resp, 'raw')
        assert '"/time-zones"' in resp.text, resp.text
        assert 'wombat.js' not in resp.text

        assert resp.headers['Content-Location'].endswith('/pywb/20140127171238id_/http://www.iana.org/')

    def _assert_rewritten(self, resp, fmod):
        self._assert_pref_headers(resp, 'rewritten')

        assert '"20140127171238"' in resp.text
        assert 'wombat.js' in resp.text
        assert 'new _WBWombat' in resp.text, resp.text

        assert resp.headers['Content-Location'].endswith('/pywb/20140127171238{0}/http://www.iana.org/'.format(fmod))

    def test_prefer_timegate_raw(self, fmod):
        headers = {'Prefer': 'raw'}
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod_slash, headers=headers, status=200)

        self._assert_raw(resp)

    def test_prefer_timegate_rewritten(self, fmod):
        headers = {'Prefer': 'rewritten'}
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod_slash, headers=headers, status=200)

        assert '/pywb/{0}http://www.iana.org/time-zones"'.format(fmod_slash) in resp.text
        self._assert_rewritten(resp, fmod)

    def test_prefer_memento_raw(self, fmod):
        headers = {'Prefer': 'raw'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_raw(resp)

    def test_prefer_memento_rewritten(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_rewritten(resp, fmod)

    def test_prefer_memento_raw_id_mod(self):
        headers = {'Prefer': 'raw'}
        resp = self.testapp.get('/pywb/20140127171238id_/http://www.iana.org/', headers=headers, status=200)

        self._assert_raw(resp)

    def test_prefer_memento_rewritten_id_mod(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/20140127171238id_/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_rewritten(resp, fmod)

    def test_prefer_memento_rewritten_diff_mod(self):
        headers = {'Prefer': 'raw'}
        resp = self.get('/pywb/20140127171238js_/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_raw(resp)

    def test_prefer_invalid(self, fmod):
        headers = {'Prefer': 'unknown'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=400)


