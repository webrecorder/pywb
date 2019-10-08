from .base_config_test import BaseConfigTest, fmod

from pywb.warcserver.index.cdxobject import CDXObject
import pytest


# ============================================================================
@pytest.fixture(params=[('mp_', 'mp_'),
                        ('', 'mp_'),
                        ('mp_', ''),
                        ('', '')],

                ids=['framed-mp',
                     'framed',
                     'non-framed-mp',
                     'non-frame'])
def fmod(request):
    return request.param


# ============================================================================
class BasePreferTests(BaseConfigTest):
    def get(self, url, param, *args, **kwargs):
        app = self.testapp if param[0] else self.testapp_non_frame
        return app.get(self.format(url, param[1], with_slash=kwargs.pop('with_slash', False)), *args, **kwargs)

    def format(self, string, fmod, with_slash=False):
        if with_slash and fmod:
            fmod += '/'

        return string.format(fmod)

    def _assert_pref_headers(self, resp, pref):
        assert resp.headers['Preference-Applied'] == pref
        assert 'Prefer' in resp.headers['Vary']

    def _assert_raw(self, resp):
        self._assert_pref_headers(resp, 'raw')
        assert '"/time-zones"' in resp.text, resp.text
        assert 'wombat.js' not in resp.text

    def _assert_banner_only(self, resp):
        self._assert_pref_headers(resp, 'banner-only')

        assert '"20140127171238"' in resp.text
        assert 'WB Insert' in resp.text

        assert 'wombat.js' not in resp.text
        assert 'WBWombatInit' not in resp.text, resp.text

    def _assert_rewritten(self, resp):
        self._assert_pref_headers(resp, 'rewritten')

        assert '"20140127171238"' in resp.text
        assert 'WB Insert' in resp.text

        assert 'wombat.js' in resp.text
        assert 'WBWombatInit' in resp.text, resp.text


# ============================================================================
class TestPreferWithRedirects(BasePreferTests):
    @classmethod
    def setup_class(cls):
        super(TestPreferWithRedirects, cls).setup_class('config_test_redirect_classic.yaml')

    def _assert_rewritten(self, resp, fmod):
        super(TestPreferWithRedirects, self)._assert_rewritten(resp)

        self.format('/20140127171238{0}/http://www.iana.org/time-zones"', fmod[0]) in resp.text

    def _assert_redir_to_raw(self, resp):
        self._assert_pref_headers(resp, 'raw')

        assert resp.location.endswith('/pywb/20140127171238id_/http://www.iana.org/')
        resp = resp.follow()

        self._assert_raw(resp)

    def _assert_redir_to_banner_only(self, resp):
        self._assert_pref_headers(resp, 'banner-only')

        assert resp.location.endswith('/pywb/20140127171238bn_/http://www.iana.org/')
        resp = resp.follow()

        self._assert_banner_only(resp)

    def _assert_redir_to_rewritten(self, resp, fmod):
        self._assert_pref_headers(resp, 'rewritten')

        assert resp.location.endswith(self.format('/pywb/20140127171238{0}/http://www.iana.org/', fmod[0]))
        resp = resp.follow()

        self._assert_rewritten(resp, fmod)

    def test_prefer_redir_timegate_raw(self, fmod):
        headers = {'Prefer': 'raw'}
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod, with_slash=True, headers=headers, status=307)

        self._assert_redir_to_raw(resp)

    def test_prefer_redir_timegate_banner_only(self, fmod):
        headers = {'Prefer': 'banner-only'}
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod, with_slash=True, headers=headers, status=307)

        self._assert_redir_to_banner_only(resp)

    def test_prefer_redir_timegate_rewritten(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod, with_slash=True, headers=headers, status=307)

        self._assert_redir_to_rewritten(resp, fmod)

    def test_prefer_redir_memento_to_raw(self, fmod):
        headers = {'Prefer': 'raw'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=307)

        self._assert_redir_to_raw(resp)

    def test_prefer_redir_memento_to_banner_only(self, fmod):
        headers = {'Prefer': 'banner-only'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=307)

        self._assert_redir_to_banner_only(resp)

    def test_prefer_redir_memento_redir_to_banner_only_diff_mod(self, fmod):
        headers = {'Prefer': 'banner-only'}
        resp = self.get('/pywb/20140127171238js_/http://www.iana.org/', fmod, headers=headers, status=307)

        self._assert_redir_to_banner_only(resp)

    def test_prefer_redir_memento_redir_to_rewritten_diff_mod(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/20140127171238js_/http://www.iana.org/', fmod, headers=headers, status=307)

        self._assert_redir_to_rewritten(resp, fmod)

    def test_prefer_redir_memento_rewritten_matches_or_redir(self, fmod):
        headers = {'Prefer': 'rewritten'}

        url = '/pywb/20140127171238{0}/http://www.iana.org/'

        # if framed mode and mp_, or non-framed mode and blank mod, already at canonical url
        # no redirect
        if fmod[0] == fmod[1]:
            resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=200)

            self._assert_rewritten(resp, fmod)
        # otherwise, if framed and blank mod, or non-framed and mp_ mod, redirect to canonical url
        else:
            resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=307)

            self._assert_redir_to_rewritten(resp, fmod)

    def test_prefer_redir_memento_matches_raw(self):
        headers = {'Prefer': 'raw'}
        resp = self.testapp.get('/pywb/20140127171238id_/http://www.iana.org/', headers=headers, status=200)

        self._assert_raw(resp)

    def test_prefer_redir_memento_matches_banner_only(self):
        headers = {'Prefer': 'banner-only'}
        resp = self.testapp.get('/pywb/20140127171238bn_/http://www.iana.org/', headers=headers, status=200)

        self._assert_banner_only(resp)

    def test_prefer_redir_invalid(self, fmod):
        headers = {'Prefer': 'unknown'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=400)


# ============================================================================
class TestPreferWithNoRedirects(BasePreferTests):
    @classmethod
    def setup_class(cls):
        super(TestPreferWithNoRedirects, cls).setup_class('config_test.yaml',
                                        custom_config={'enable_prefer': True})

    def _assert_raw(self, resp):
        super(TestPreferWithNoRedirects, self)._assert_raw(resp)

        assert resp.headers['Content-Location'].endswith('/pywb/20140127171238id_/http://www.iana.org/')

    def _assert_rewritten(self, resp, fmod):
        super(TestPreferWithNoRedirects, self)._assert_rewritten(resp)

        assert resp.headers['Content-Location'].endswith(self.format('/pywb/20140127171238{0}/http://www.iana.org/', fmod[0]))

    def _assert_banner_only(self, resp):
        super(TestPreferWithNoRedirects, self)._assert_banner_only(resp)

        assert resp.headers['Content-Location'].endswith('/pywb/20140127171238bn_/http://www.iana.org/')

    def test_prefer_timegate_raw(self, fmod):
        headers = {'Prefer': 'raw'}
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod, with_slash=True, headers=headers, status=200)

        assert '"/time-zones"' in resp.text
        self._assert_raw(resp)

    def test_prefer_timegate_banner_only(self, fmod):
        headers = {'Prefer': 'banner-only'}
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod, with_slash=True, headers=headers, status=200)

        assert '"/time-zones"' in resp.text
        self._assert_banner_only(resp)

    def test_prefer_timegate_rewritten(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/{0}http://www.iana.org/', fmod, with_slash=True, headers=headers, status=200)

        assert self.format('/pywb/{0}http://www.iana.org/time-zones"', fmod[0], with_slash=True) in resp.text
        self._assert_rewritten(resp, fmod)

    def test_prefer_memento_raw(self, fmod):
        headers = {'Prefer': 'raw'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_raw(resp)

    def test_prefer_memento_banner_only(self, fmod):
        headers = {'Prefer': 'banner-only'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_banner_only(resp)

    def test_prefer_memento_rewritten(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=200)

        assert self.format('/pywb/20140127171238{0}/http://www.iana.org/time-zones"', fmod[0]) in resp.text
        self._assert_rewritten(resp, fmod)

    def test_prefer_memento_raw_id_mod(self):
        headers = {'Prefer': 'raw'}
        resp = self.testapp.get('/pywb/20140127171238id_/http://www.iana.org/', headers=headers, status=200)

        self._assert_raw(resp)

    def test_prefer_memento_rewritten_from_id_mod(self, fmod):
        headers = {'Prefer': 'rewritten'}
        resp = self.get('/pywb/20140127171238id_/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_rewritten(resp, fmod)

    def test_prefer_memento_banner_only_no_mod(self, fmod):
        headers = {'Prefer': 'banner-only'}
        resp = self.get('/pywb/20140127171238/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_banner_only(resp)

    def test_prefer_memento_rewritten_diff_mod(self, fmod):
        headers = {'Prefer': 'raw'}
        resp = self.get('/pywb/20140127171238js_/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_raw(resp)

    def test_prefer_memento_banner_only_diff_mod(self, fmod):
        headers = {'Prefer': 'banner-only'}
        resp = self.get('/pywb/20140127171238js_/http://www.iana.org/', fmod, headers=headers, status=200)

        self._assert_banner_only(resp)

    def test_prefer_invalid(self, fmod):
        headers = {'Prefer': 'unknown'}
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod, headers=headers, status=400)


