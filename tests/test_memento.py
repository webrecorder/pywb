import webtest
from pywb.core.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app
from pywb.cdx.cdxobject import CDXObject

MEMENTO_DATETIME = 'Memento-Datetime'
ACCEPT_DATETIME = 'Accept-Datetime'
LINK = 'Link'
VARY = 'Vary'

class TestWb:
    TEST_CONFIG = 'tests/test_config_memento.yaml'

    def setup(self):
        self.app = init_app(create_wb_router,
                            load_yaml=True,
                            config_file=self.TEST_CONFIG)

        self.testapp = webtest.TestApp(self.app)

    # Below functionality is for archival (non-proxy) mode
    # It is designed to conform to Memento protocol Pattern 2.1
    # http://www.mementoweb.org/guide/rfc/#Pattern2.1

    def test_timegate_latest(self):
        """
        TimeGate with no Accept-Datetime header
        """
        resp = self.testapp.get('/pywb/http://www.iana.org/_css/2013.1/screen.css')

        assert resp.status_int == 302

        assert resp.headers[VARY] == 'accept-datetime'
        assert resp.headers[LINK] == '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"'
        assert MEMENTO_DATETIME not in resp.headers

        assert '/pywb/20140127171239/http://www.iana.org/_css/2013.1/screen.css' in resp.headers['Location']


    def test_timegate_accept_datetime(self):
        """
        TimeGate with Accept-Datetime header
        """
        headers = {ACCEPT_DATETIME: 'Sun, 26 Jan 2014 20:08:04'}
        resp = self.testapp.get('/pywb/http://www.iana.org/_css/2013.1/screen.css', headers=headers)

        assert resp.status_int == 302

        assert resp.headers[VARY] == 'accept-datetime'
        assert resp.headers[LINK] == '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"'
        assert MEMENTO_DATETIME not in resp.headers

        assert '/pywb/20140126200804/http://www.iana.org/_css/2013.1/screen.css' in resp.headers['Location']


    def test_non_timegate_intermediate_redir(self):
        """
        Not a timegate, but an 'intermediate resource', redirect to closest timestamp
        """
        headers = {ACCEPT_DATETIME: 'Sun, 26 Jan 2014 20:08:04'}
        # not a timegate, partial timestamp /2014/ present
        resp = self.testapp.get('/pywb/2014/http://www.iana.org/_css/2013.1/screen.css', headers=headers)

        assert resp.status_int == 302

        # no vary header
        assert VARY not in resp.headers
        assert resp.headers[LINK] == '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"'
        assert MEMENTO_DATETIME not in resp.headers


        # redirect to latest, not negotiation via Accept-Datetime
        assert '/pywb/20140127171239/' in resp.headers['Location']


    def test_memento_url(self):
        """
        Memento response, 200 capture
        """
        resp = self.testapp.get('/pywb/20140126200804/http://www.iana.org/_css/2013.1/screen.css')

        assert resp.status_int == 200

        assert VARY not in resp.headers

        assert resp.headers[LINK] == '<http://www.iana.org/_css/2013.1/screen.css>; rel="original", \
<http://localhost:80/pywb/http://www.iana.org/_css/2013.1/screen.css>; rel="timegate"'

        assert resp.headers[MEMENTO_DATETIME] == 'Sun, 26 Jan 2014 20:08:04 GMT'


    def test_302_memento(self):
        """
        Memento (capture) of a 302 response
        """
        resp = self.testapp.get('/pywb/20140128051539/http://www.iana.org/domains/example')

        assert resp.status_int == 302

        assert VARY not in resp.headers

        assert resp.headers[LINK] == '<http://www.iana.org/domains/example>; rel="original", \
<http://localhost:80/pywb/http://www.iana.org/domains/example>; rel="timegate"'

        assert resp.headers[MEMENTO_DATETIME] == 'Tue, 28 Jan 2014 05:15:39 GMT'


    # Below functions test pywb proxy mode behavior
    # They are designed to roughly conform to Memento protocol Pattern 1.3
    # with the exception that the original resource is not available

    def test_proxy_latest_memento(self):
        """
        Proxy Mode memento with no Accept-Datetime
        Both a timegate and a memento
        """
        # simulate proxy mode by setting REQUEST_URI
        request_uri = 'http://www.iana.org/_css/2013.1/screen.css'
        extra = dict(REQUEST_URI=request_uri, SCRIPT_NAME='')

        resp = self.testapp.get('/x-ignore-this-x', extra_environ=extra)

        assert resp.status_int == 200

        # for timegate
        assert resp.headers[VARY] == 'accept-datetime'

        # for memento
        assert resp.headers[LINK] == '<http://www.iana.org/_css/2013.1/screen.css>; rel="original timegate"'
        assert resp.headers[MEMENTO_DATETIME] == 'Mon, 27 Jan 2014 17:12:39 GMT'


    def test_proxy_accept_datetime_memento(self):
        """
        Proxy Mode memento with specific Accept-Datetime
        Both a timegate and a memento
        """
        # simulate proxy mode by setting REQUEST_URI
        request_uri = 'http://www.iana.org/_css/2013.1/screen.css'
        extra = dict(REQUEST_URI=request_uri, SCRIPT_NAME='')
        headers = {ACCEPT_DATETIME: 'Sun, 26 Jan 2014 20:08:04'}

        resp = self.testapp.get('/x-ignore-this-x', extra_environ=extra, headers=headers)

        assert resp.status_int == 200

        # for timegate
        assert resp.headers[VARY] == 'accept-datetime'

        # for memento
        assert resp.headers[LINK] == '<http://www.iana.org/_css/2013.1/screen.css>; rel="original timegate"'
        assert resp.headers[MEMENTO_DATETIME] == 'Sun, 26 Jan 2014 20:08:04 GMT'


    def test_error_bad_accept_datetime(self):
        """
        400 response for bad accept_datetime
        """
        headers = {ACCEPT_DATETIME: 'Sun'}
        resp = self.testapp.get('/pywb/http://www.iana.org/_css/2013.1/screen.css', headers=headers, status=400)
        assert resp.status_int == 400


    def test_error_bad_accept_datetime_proxy(self):
        """
        400 response for bad accept_datetime
        with proxy mode
        """
        request_uri = 'http://www.iana.org/_css/2013.1/screen.css'
        extra = dict(REQUEST_URI=request_uri, SCRIPT_NAME='')
        headers = {ACCEPT_DATETIME: 'Sun, abc'}

        resp = self.testapp.get('/x-ignore-this-x', extra_environ=extra, headers=headers, status=400)

        assert resp.status_int == 400
