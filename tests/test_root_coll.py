from .base_config_test import BaseConfigTest, fmod
from pywb.warcserver.test.testutils import HttpBinLiveTests


# ============================================================================
class TestRootColl(HttpBinLiveTests, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestRootColl, cls).setup_class('config_test_root_coll.yaml')

    def test_root_replay_ts(self, fmod):
        resp = self.get('/20140127171238{0}/http://httpbin.org/base64/PGh0bWw+PGJvZHk+PGEgaHJlZj0iL3Rlc3QvcGF0aCI+VGVzdCBVUkw8L2E+PC9ib2R5PjwvaHRtbD4=', fmod)

        # Body
        assert '"20140127171238"' in resp.text
        assert 'wombat.js' in resp.text
        assert 'WBWombatInit' in resp.text, resp.text
        assert 'wbinfo.enable_auto_fetch = true;' in resp.text, resp.text
        assert '/20140127171238{0}/http://httpbin.org/test/path"'.format(fmod) in resp.text

    def test_root_replay_no_ts(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/{0}http://httpbin.org/base64/PGh0bWw+PGJvZHk+PGEgaHJlZj0iL3Rlc3QvcGF0aCI+VGVzdCBVUkw8L2E+PC9ib2R5PjwvaHRtbD4=', fmod_slash)

        # Body
        assert 'request_ts = ""' in resp.text
        assert 'wombat.js' in resp.text
        assert 'WBWombatInit' in resp.text, resp.text
        assert 'wbinfo.enable_auto_fetch = true;' in resp.text, resp.text
        assert '/{0}http://httpbin.org/test/path"'.format(fmod_slash) in resp.text

    def test_root_replay_redir(self, fmod):
        resp = self.get('/20140128051539{0}/http://httpbin.org/redirect-to?url=http://httpbin.org/get', fmod)

        assert resp.status_int in (301, 302)

        location = self.get_httpbin_url(resp.headers['Location'])
        assert location == 'http://localhost:80/20140128051539{0}/http://httpbin.org/get'.format(fmod)

    def test_root_home_search(self):
        resp = self.testapp.get('/')
        assert 'Search' in resp.text

    def test_root_cdx(self):
        resp = self.testapp.get('/cdx?url=http://www.iana.org/&output=json&limit=1')
        resp.content_type = 'application/json'
        assert resp.json['is_live'] == 'true'
        assert resp.json['url'] == 'http://www.iana.org/'
        assert resp.json['source'] == '$root'
