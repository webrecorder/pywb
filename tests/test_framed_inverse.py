import webtest
from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app

from .memento_fixture import *

from .server_mock import make_setup_module, BaseIntegration

setup_module = make_setup_module('tests/test_config_frames.yaml')


class TestMementoFrameInverse(MementoMixin, BaseIntegration):
    def test_top_frame_replay(self):
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

    def test_inner_replay(self):
        resp = self.testapp.get('/pywb/20140127171238mp_/http://www.iana.org/')

        # Memento Headers
        # no vary header
        assert VARY not in resp.headers
        assert MEMENTO_DATETIME in resp.headers

        # memento link
        dt = 'Mon, 27 Jan 2014 17:12:38 GMT'

        links = self.get_links(resp)
        assert self.make_memento_link('http://www.iana.org/', '20140127171238mp_', dt) in links

        # timegate link
        assert '<http://localhost:80/pywb/mp_/http://www.iana.org/>; rel="timegate"' in links

        # Body
        assert '"20140127171238"' in resp.text
        assert 'wb.js' in resp.text
        assert 'new _WBWombat' in resp.text, resp.text
        assert '/pywb/20140127171238mp_/http://www.iana.org/time-zones"' in resp.text
