from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app
from pywb.framework.basehandlers import BaseHandler
from pywb.framework.wbrequestresponse import WbResponse

from .server_mock import make_setup_module, BaseIntegration

setup_module = make_setup_module('tests/test_config_root_coll.yaml')


# A custom handler
class RedirHandler(BaseHandler):
    def __call__(self, wbrequest):
        return WbResponse.redir_response(self.redir_path + wbrequest.wb_url_str)


class TestMementoFrameInverse(BaseIntegration):
    def test_timestamp_replay_redir(self):
        resp = self.testapp.get('/http://www.iana.org/')
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/20140127171238/http://www.iana.org/')


    def test_replay(self):
        resp = self.testapp.get('/20140127171238/http://www.iana.org/')

        # Body
        assert '"20140127171238"' in resp.text
        assert 'wb.js' in resp.text
        assert 'new _WBWombat' in resp.text, resp.text
        assert '/20140127171238/http://www.iana.org/time-zones"' in resp.text

    def test_redir_handler_redir(self):
        resp = self.testapp.get('/foo/20140127171238mp_/http://www.iana.org/')
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/20140127171238mp_/http://www.iana.org/')

    def test_home_search(self):
        resp = self.testapp.get('/')
        assert 'Search' in resp.text

