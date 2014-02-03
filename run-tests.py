import webtest
import pywb.pywb_init
from pywb.indexreader import CDXCaptureResult

class TestWb:
    def setup(self):
        import pywb.wbapp
        #self.app = pywb.wbapp.create_wb_app(pywb.pywb_init.pywb_config())
        self.app = pywb.wbapp.create_wb_app(pywb.pywb_init.pywb_config_manual())
        self.testapp = webtest.TestApp(self.app)

    def _assert_basic_html(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert resp.content_length > 0

    def _assert_basic_text(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/plain'
        assert resp.content_length > 0

    def test_home(self):
        resp = self.testapp.get('/')
        self._assert_basic_html(resp)
        assert '/pywb' in resp.body

    def test_pywb_root(self):
        resp = self.testapp.get('/pywb/')
        self._assert_basic_html(resp)
        assert 'Search' in resp.body

    def test_calendar_query(self):
        resp = self.testapp.get('/pywb/*/iana.org')
        self._assert_basic_html(resp)
        # 3 Captures + header
        assert len(resp.html.find_all('tr')) == 4

    def test_cdx_query(self):
        resp = self.testapp.get('/pywb/cdx_/*/http://www.iana.org/')
        self._assert_basic_text(resp)

        assert '20140127171238 http://www.iana.org/ warc/revisit - OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB' in resp
        # check for 3 cdx lines (strip final newline)
        actual_len = len(str(resp.body).rstrip().split('\n'))
        assert actual_len == 3, actual_len


    def test_replay_1(self):
        resp = self.testapp.get('/pywb/20140127171238/http://www.iana.org/')
        self._assert_basic_html(resp)

        assert 'Mon, Jan 27 2014 17:12:38' in resp.body
        assert 'wb.js' in resp.body
        assert '/pywb/20140127171238/http://www.iana.org/time-zones' in resp.body


    def test_redirect_1(self):
        resp = self.testapp.get('/pywb/20140127171237/http://www.iana.org/')
        assert resp.status_int == 302

        assert resp.headers['Location'].endswith('/pywb/20140127171238/http://iana.org')


    def test_redirect_replay_2(self):
        resp = self.testapp.get('/pywb/http://example.com/')
        assert resp.status_int == 302

        assert resp.headers['Location'].endswith('/20140127171251/http://example.com')
        resp = resp.follow()

        #check resp
        self._assert_basic_html(resp)
        assert 'Mon, Jan 27 2014 17:12:51' in resp.body
        assert '/pywb/20140127171251/http://www.iana.org/domains/example' in resp.body

    def test_cdx_server_filters(self):
        resp = self.testapp.get('/pywb-cdx?url=http://www.iana.org/_css/2013.1/screen.css&filter=mimetype:warc/revisit&filter=filename:dupes.warc.gz')
        self._assert_basic_text(resp)
        actual_len = len(resp.body.rstrip().split('\n'))
        assert actual_len == 1, actual_len

    def test_cdx_server_advanced(self):
        # combine collapsing, reversing and revisit resolving
        resp = self.testapp.get('/pywb-cdx?url=http://www.iana.org/_css/2013.1/print.css&collapse_time=11&resolve_revisits=true&reverse=true')

        # convert back to CDXCaptureResult
        cdxs = map(CDXCaptureResult, resp.body.rstrip().split('\n'))
        assert len(cdxs) == 3, len(cdxs)

        # verify timestamps
        timestamps = map(lambda cdx: cdx['timestamp'], cdxs)
        assert timestamps == ['20140127171239', '20140126201054', '20140126200625']

        # verify orig filenames (2 revisits, one non)
        origfilenames = map(lambda cdx: cdx['orig.filename'], cdxs)
        assert origfilenames == ['iana.warc.gz', 'iana.warc.gz', '-']


    def test_error(self):
        resp = self.testapp.get('/pywb/?abc', status = 400)
        assert resp.status_int == 400
        assert 'Bad Request Url: http://?abc' in resp.body


