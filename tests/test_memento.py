from .base_config_test import BaseConfigTest, fmod

from .memento_fixture import *

# ============================================================================
class TestMemento(MementoMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestMemento, cls).setup_class('config_test.yaml')

    def _test_top_frame_replay(self):
        resp = self.testapp.get('/pywb/20140127171238/http://www.iana.org/')

        # Memento Headers
        # no vary header
        assert VARY not in resp.headers
        assert MEMENTO_DATETIME in resp.headers

        # memento link
        dt = 'Mon, 27 Jan 2014 17:12:38 GMT'

        links = self.get_links(resp)
        assert self.make_memento_link('http://www.iana.org/', '20140127171238mp_', dt) in links

        #timegate link
        assert '<http://localhost:80/pywb/mp_/http://www.iana.org/>; rel="timegate"' in links

        # Body
        assert '<iframe ' in resp.text
        assert '/pywb/20140127171238mp_/http://www.iana.org/' in resp.text, resp.text

    def test_memento_content_replay(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod)

        # Memento Headers
        # no vary header
        assert VARY not in resp.headers
        assert MEMENTO_DATETIME in resp.headers

        # memento link
        dt = 'Mon, 27 Jan 2014 17:12:38 GMT'

        links = self.get_links(resp)
        assert self.make_memento_link('http://www.iana.org/', '20140127171238{0}'.format(fmod), dt) in links

        # timegate link
        assert '<http://localhost:80/pywb/{0}http://www.iana.org/>; rel="timegate"'.format(fmod_slash) in links

        # Body
        assert '"20140127171238"' in resp.text
        assert 'wb.js' in resp.text
        assert 'new _WBWombat' in resp.text, resp.text
        assert '/pywb/20140127171238{0}/http://www.iana.org/time-zones"'.format(fmod) in resp.text
