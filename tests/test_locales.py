from .base_config_test import BaseConfigTest


# ============================================================================
class TestLocales(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestLocales, cls).setup_class('config_test_loc.yaml')

    def test_locale_en_home(self):
        res = self.testapp.get('/en/')

        assert 'Pywb Wayback Machine' in res.text, res.text

    def test_locale_l337_home(self):
        res = self.testapp.get('/l337/')

        print(res.text)
        assert r'Py\/\/b W4yb4ck /\/\4ch1n3' in res.text

    def test_locale_en_replay_banner(self):
        res = self.testapp.get('/en/pywb/mp_/https://example.com/')
        assert '"en"' in res.text
        assert '"Language:"' in res.text

    def test_locale_l337_replay_banner(self):
        res = self.testapp.get('/l337/pywb/mp_/https://example.com/')
        assert '"l337"' in res.text
        assert '"L4n9u4g3:"' in res.text


