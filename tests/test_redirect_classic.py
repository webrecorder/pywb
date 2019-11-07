from .base_config_test import BaseConfigTest, fmod


# ============================================================================
class TestRedirectClassic(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestRedirectClassic, cls).setup_class('config_test_redirect_classic.yaml')

    def test_replay_content_inexact(self, fmod):
        resp = self.get('/pywb/20140127171235{0}/http://www.iana.org/', fmod)

        assert resp.status_code == 307
        assert resp.headers['Location'].endswith('/20140127171238{0}/http://www.iana.org/'.format(fmod))
        assert resp.headers['Link'] == '<http://www.iana.org/>; rel="original"'
        resp = resp.follow()

        self._assert_basic_html(resp)

        assert '"20140127171238"' in resp.text, resp.text
        assert 'wombat.js' in resp.text
        assert 'WBWombatInit' in resp.text, resp.text
        assert '/pywb/20140127171238{0}/http://www.iana.org/time-zones"'.format(fmod) in resp.text

        assert ('wbinfo.is_framed = ' + ('true' if fmod else 'false')) in resp.text

        csp = "default-src 'unsafe-eval' 'unsafe-inline' 'self' data: blob: mediastream: ws: wss: ; form-action 'self'"
        assert resp.headers['Content-Security-Policy'] == csp

        # verify enable_rewrite_flash_video is injected
        assert 'vidrw.js' in resp.text

    def test_latest_replay_redirect(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''

        resp = self.get('/pywb/{0}http://example.com/', fmod_slash)
        assert resp.status_code == 307
        assert resp.headers['Location'].endswith('/20140127171251{0}/http://example.com'.format(fmod))
        assert resp.headers['Link'] != ''

        # trailing slash redir
        resp = resp.follow()
        assert resp.status_code == 307
        assert resp.headers['Location'].endswith('/20140127171251{0}/http://example.com/'.format(fmod))
        assert resp.headers['Link'] != ''

        resp = resp.follow()
        self._assert_basic_html(resp)
        assert resp.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'

        assert '"20140127171251"' in resp.text
        assert '/pywb/20140127171251{0}/http://www.iana.org/domains/example'.format(fmod) in resp.text, resp.text

    def test_replay_memento_accept_dt(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        headers = {'Accept-Datetime':  'Mon, 26 Dec 2011 17:12:51 GMT'}

        resp = self.get('/pywb/{0}http://example.com/', fmod_slash, headers=headers)
        assert resp.status_code == 307
        assert resp.headers['Location'].endswith('/20130729195151{0}/http://test@example.com/'.format(fmod))
        assert resp.headers['Link'] != ''

        resp = resp.follow()
        self._assert_basic_html(resp)
        assert resp.headers['Memento-Datetime'] == 'Mon, 29 Jul 2013 19:51:51 GMT'

    def test_replay_fuzzy_1_redirect(self, fmod):
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/?_=123', fmod)
        assert resp.status_int == 307
        assert resp.headers['Location'].endswith('/pywb/20140126200624{0}/http://www.iana.org/'.format(fmod))

    def test_live_no_redir(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/live/{0}http://example.com/?test=test', fmod_slash)
        assert resp.status_int == 200

    def test_replay_limit_cdx(self):
        resp = self.testapp.get('/pywb/cdx?url=http://www.iana.org/*&output=json')
        assert resp.content_type == 'text/x-ndjson'
        assert len(resp.text.rstrip().split('\n')) == 10

