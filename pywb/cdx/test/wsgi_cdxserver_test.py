import webtest
from pywb.cdx.wsgi_cdxserver import main
from pywb import get_test_dir

class TestCdx:
    def setup(self):
        self.app = main(get_test_dir() + 'cdx/')
        self.testapp = webtest.TestApp(self.app)

    def test_cdx(self):
        resp = self.testapp.get('/cdx?url=http://www.iana.org/_css/2013.1/screen.css')
        assert resp.content_type == 'text/plain'
        assert resp.content_length > 0


