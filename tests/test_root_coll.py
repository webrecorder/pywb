from .base_config_test import BaseConfigTest, fmod


# ============================================================================
class TestRootColl(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestRootColl, cls).setup_class('config_test_root_coll.yaml')

    def test_root_replay_ts(self, fmod):
        resp = self.get('/20140127171238{0}/http://www.iana.org/', fmod)

        # Body
        assert '"20140127171238"' in resp.text
        assert 'wombat.js' in resp.text
        assert 'WBWombatInit' in resp.text, resp.text
        assert 'wbinfo.enable_auto_fetch = true;' in resp.text, resp.text
        assert '/20140127171238{0}/http://www.iana.org/time-zones"'.format(fmod) in resp.text

    def test_root_replay_no_ts(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/{0}http://www.iana.org/', fmod_slash)

        # Body
        assert 'request_ts = ""' in resp.text
        assert 'wombat.js' in resp.text
        assert 'WBWombatInit' in resp.text, resp.text
        assert 'wbinfo.enable_auto_fetch = true;' in resp.text, resp.text
        assert '/{0}http://www.iana.org/time-zones"'.format(fmod_slash) in resp.text

    def test_root_replay_redir(self, fmod):
        resp = self.get('/20140128051539{0}/http://www.iana.org/domains/example', fmod)

        assert resp.status_int == 302

        assert resp.headers['Location'] == 'http://localhost:80/20140128051539{0}/https://www.iana.org/domains/reserved'.format(fmod)

    def test_root_home_search(self):
        resp = self.testapp.get('/')
        assert 'Search' in resp.text

    def test_root_cdx(self):
        resp = self.testapp.get('/cdx?url=http://www.iana.org/&output=json&limit=1')
        resp.content_type = 'application/json'
        assert resp.json['is_live'] == 'true'
        assert resp.json['url'] == 'http://www.iana.org/'
        assert resp.json['source'] == '$root'
