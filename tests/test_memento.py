import webtest
import re
from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app
from pywb.cdx.cdxobject import CDXObject
from pywb.utils.timeutils import timestamp_now

from .memento_fixture import *

from .server_mock import make_setup_module, BaseIntegration

setup_module = make_setup_module('tests/test_config_memento.yaml')


class TestMemento(MementoMixin, BaseIntegration):
    # Below functionality is for archival (non-proxy) mode
    # It is designed to conform to Memento protocol Pattern 2.1
    # http://www.mementoweb.org/guide/rfc/#Pattern2.1

    def test_timegate_latest(self):
        """
        TimeGate with no Accept-Datetime header
        """

        dt = 'Mon, 27 Jan 2014 17:12:39 GMT'
        resp = self.testapp.get('/pywb/http://www.iana.org/_css/2013.1/screen.css')

        assert resp.status_int == 302

        assert resp.headers[VARY] == 'accept-datetime'

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links
        assert self.make_memento_link('http://www.iana.org/_css/2013.1/screen.css', '20140127171239', dt) in links

        assert MEMENTO_DATETIME not in resp.headers

        assert '/pywb/20140127171239/http://www.iana.org/_css/2013.1/screen.css' in resp.headers['Location']


    # timegate with latest memento, but no redirect
    def test_timegate_memento_no_redir_latest(self):
        """
        TimeGate with no Accept-Datetime header
        """

        dt = 'Mon, 27 Jan 2014 17:12:39 GMT'
        resp = self.testapp.get('/pywb-no-redir/http://www.iana.org/_css/2013.1/screen.css')

        assert resp.status_int == 200

        assert resp.headers[VARY] == 'accept-datetime'

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css', coll='pywb-no-redir') in links
        assert self.make_memento_link('http://www.iana.org/_css/2013.1/screen.css', '20140127171239', dt, coll='pywb-no-redir') in links

        assert MEMENTO_DATETIME in resp.headers

        assert '/pywb-no-redir/' in resp.headers['Content-Location']

        wburl = resp.headers['Content-Location'].split('/pywb-no-redir/')[-1]
        ts = wburl.split('/')[0]
        assert len(ts) == 14
        assert timestamp_now() >= ts

    def test_timegate_accept_datetime_exact(self):
        """
        TimeGate with Accept-Datetime header, matching exactly
        """
        dt = 'Sun, 26 Jan 2014 20:08:04 GMT'
        headers = {ACCEPT_DATETIME: dt}
        resp = self.testapp.get('/pywb//http://www.iana.org/_css/2013.1/screen.css', headers=headers)

        assert resp.status_int == 302

        assert resp.headers[VARY] == 'accept-datetime'

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links
        assert self.make_memento_link('http://www.iana.org/_css/2013.1/screen.css', '20140126200804', dt) == links[0], links[0]

        assert MEMENTO_DATETIME not in resp.headers

        assert '/pywb/20140126200804/http://www.iana.org/_css/2013.1/screen.css' in resp.headers['Location']

    def test_timegate_accept_datetime_inexact(self):
        """
        TimeGate with Accept-Datetime header, not matching a memento exactly
        """
        dt = 'Sun, 26 Jan 2014 20:08:04 GMT'
        request_dt = 'Sun, 26 Jan 2014 20:08:00 GMT'
        headers = {ACCEPT_DATETIME: request_dt}
        resp = self.testapp.get('/pywb//http://www.iana.org/_css/2013.1/screen.css', headers=headers)

        assert resp.status_int == 302

        assert resp.headers[VARY] == 'accept-datetime'

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links
        assert self.make_memento_link('http://www.iana.org/_css/2013.1/screen.css', '20140126200804', dt) == links[0], links[0]

        assert MEMENTO_DATETIME not in resp.headers

        assert '/pywb/20140126200804/http://www.iana.org/_css/2013.1/screen.css' in resp.headers['Location']


    def test_timegate_memento_no_redir_accept_datetime_inexact(self):
        """
        TimeGate with Accept-Datetime header, not matching a memento exactly, no redirect
        """
        dt = 'Sun, 26 Jan 2014 20:08:04 GMT'
        request_dt = 'Sun, 26 Jan 2014 20:08:00 GMT'
        headers = {ACCEPT_DATETIME: request_dt}
        resp = self.testapp.get('/pywb-no-redir/http://www.iana.org/_css/2013.1/screen.css', headers=headers)

        assert resp.status_int == 200

        assert resp.headers[VARY] == 'accept-datetime'

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css', coll='pywb-no-redir') in links
        assert self.make_memento_link('http://www.iana.org/_css/2013.1/screen.css', '20140126200804', dt, coll='pywb-no-redir') == links[0], links[0]

        assert MEMENTO_DATETIME in resp.headers

        assert '/pywb-no-redir/20140126200804/http://www.iana.org/_css/2013.1/screen.css' in resp.headers['Content-Location']

    def test_non_timegate_intermediate_redir(self):
        """
        Not a timegate, but an 'intermediate resource', redirect to closest timestamp
        """
        headers = {ACCEPT_DATETIME: 'Sun, 26 Jan 2014 20:08:04 GMT'}
        # not a timegate, partial timestamp /2014/ present
        resp = self.testapp.get('/pywb/2014/http://www.iana.org/_css/2013.1/screen.css', headers=headers)

        assert resp.status_int == 302

        # no vary header
        assert VARY not in resp.headers

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links

        assert MEMENTO_DATETIME not in resp.headers


        # redirect to latest, not negotiation via Accept-Datetime
        assert '/pywb/20140127171239/' in resp.headers['Location']


    def test_top_frame(self):
        """
        A top-frame request with no date, not returning memento-datetime
        Include timemap, timegate, original headers
        """

        resp = self.testapp.get('/pywb/tf_/http://www.iana.org/_css/2013.1/screen.css')

        assert resp.status_int == 200

        # no vary header
        assert VARY not in resp.headers

        # not memento-datetime
        assert MEMENTO_DATETIME not in resp.headers

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert '<http://localhost:80/pywb/http://www.iana.org/_css/2013.1/screen.css>; rel="timegate"' in links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links

    def test_top_frame_no_date_accept_datetime(self):
        """
        A top-frame request with no date, reflects back accept-datetime date
        Include timemap, timegate, original headers, and memento-datetime
        """

        dt = 'Sun, 26 Jan 2014 20:08:04 GMT'
        headers = {ACCEPT_DATETIME: dt}

        # not a timegate, but use ACCEPT_DATETIME to infer memento for top frame
        resp = self.testapp.get('/pywb/tf_/http://www.iana.org/_css/2013.1/screen.css', headers=headers)

        assert resp.status_int == 200

        # no vary header
        assert VARY not in resp.headers

        # memento-datetime matches
        assert resp.headers[MEMENTO_DATETIME] == dt

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert '<http://localhost:80/pywb/http://www.iana.org/_css/2013.1/screen.css>; rel="timegate"' in links
        assert self.make_memento_link('http://www.iana.org/_css/2013.1/screen.css', '20140126200804', dt) in links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links

    def test_top_frame_with_date(self):
        """
        A top-frame request with date, treat as memento
        Include timemap, timegate, original headers, memento and memento-datetime
        """

        dt = 'Sun, 26 Jan 2014 20:08:04 GMT'
        headers = {ACCEPT_DATETIME: dt}

        # not a timegate, ignore ACCEPT_DATETIME, but use provided timestamp as memento-datetime
        resp = self.testapp.get('/pywb/20141012000000tf_/http://www.iana.org/_css/2013.1/screen.css', headers=headers)

        assert resp.status_int == 200

        # no vary header
        assert VARY not in resp.headers

        dt = 'Sun, 12 Oct 2014 00:00:00 GMT'
        # memento-datetime matches
        assert resp.headers[MEMENTO_DATETIME] == dt

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert '<http://localhost:80/pywb/http://www.iana.org/_css/2013.1/screen.css>; rel="timegate"' in links
        assert self.make_memento_link('http://www.iana.org/_css/2013.1/screen.css', '20141012000000', dt) in links, links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links

    def test_memento_url(self):
        """
        Memento response, 200 capture
        """
        resp = self.testapp.get('/pywb/20140126200804/http://www.iana.org/_css/2013.1/screen.css')

        assert resp.status_int == 200

        assert VARY not in resp.headers

        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original"' in links
        assert '<http://localhost:80/pywb/http://www.iana.org/_css/2013.1/screen.css>; rel="timegate"' in links
        assert self.make_memento_link('http://www.iana.org/_css/2013.1/screen.css', '20140126200804', 'Sun, 26 Jan 2014 20:08:04 GMT') in links
        assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links

        assert resp.headers[MEMENTO_DATETIME] == 'Sun, 26 Jan 2014 20:08:04 GMT'


    def test_302_memento(self):
        """
        Memento (capture) of a 302 response
        """
        resp = self.testapp.get('/pywb/20140128051539/http://www.iana.org/domains/example')

        assert resp.status_int == 302

        assert VARY not in resp.headers

        links = self.get_links(resp)
        assert '<http://www.iana.org/domains/example>; rel="original"' in links
        assert '<http://localhost:80/pywb/http://www.iana.org/domains/example>; rel="timegate"' in links
        assert self.make_memento_link('http://www.iana.org/domains/example', '20140128051539', 'Tue, 28 Jan 2014 05:15:39 GMT') in links
        assert self.make_timemap_link('http://www.iana.org/domains/example') in links

        assert resp.headers[MEMENTO_DATETIME] == 'Tue, 28 Jan 2014 05:15:39 GMT'


    def test_timemap(self):
        """
        Test application/link-format timemap
        """

        resp = self.testapp.get('/pywb/timemap/*/http://example.com?example=1')
        assert resp.status_int == 200
        assert resp.content_type == LINK_FORMAT

        resp.charset = 'utf-8'
        lines = resp.text.split('\n')

        assert len(lines) == 5

        assert lines[0] == '<http://localhost:80/pywb/timemap/*/http://example.com?example=1>; \
rel="self"; type="application/link-format"; from="Fri, 03 Jan 2014 03:03:21 GMT",'

        assert lines[1] == '<http://example.com?example=1>; rel="original",'

        assert lines[2] == '<http://localhost:80/pywb/http://example.com?example=1>; rel="timegate",'

        assert lines[3] == '<http://localhost:80/pywb/20140103030321/http://example.com?example=1>; \
rel="memento"; datetime="Fri, 03 Jan 2014 03:03:21 GMT",'

        assert lines[4] == '<http://localhost:80/pywb/20140103030341/http://example.com?example=1>; \
rel="memento"; datetime="Fri, 03 Jan 2014 03:03:41 GMT"'

    def test_timemap_2(self):
        """
        Test application/link-format timemap total count
        """

        resp = self.testapp.get('/pywb/timemap/*/http://example.com')
        assert resp.status_int == 200
        assert resp.content_type == LINK_FORMAT

        lines = resp.content.split('\n')

        assert len(lines) == 3 + 3


    def test_timemap_not_found(self):
        """
        Test application/link-format timemap
        """

        resp = self.testapp.get('/pywb/timemap/*/http://example.com/blah/not_found')
        assert resp.status_int == 200
        assert resp.content_type == LINK_FORMAT

        resp.charset = 'utf-8'
        lines = resp.text.split('\n')

        assert len(lines) == 3

        assert lines[0] == '<http://example.com/blah/not_found>; rel="original",'

        assert lines[1] == '<http://localhost:80/pywb/http://example.com/blah/not_found>; rel="timegate",'

        assert lines[2] == '<http://localhost:80/pywb/timemap/*/http://example.com/blah/not_found>; \
rel="self"; type="application/link-format"'


    def test_timemap_2(self):
        """
        Test application/link-format timemap total count
        """

        resp = self.testapp.get('/pywb/timemap/*/http://example.com')
        assert resp.status_int == 200
        assert resp.content_type == LINK_FORMAT

        resp.charset = 'utf-8'
        lines = resp.text.split('\n')

        assert len(lines) == 3 + 3




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
        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original timegate"' in links
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="memento"; datetime="Mon, 27 Jan 2014 17:12:39 GMT"' in links
        #assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links

        assert resp.headers[MEMENTO_DATETIME] == 'Mon, 27 Jan 2014 17:12:39 GMT'


    def test_proxy_accept_datetime_memento(self):
        """
        Proxy Mode memento with specific Accept-Datetime
        Both a timegate and a memento
        """
        # simulate proxy mode by setting REQUEST_URI
        request_uri = 'http://www.iana.org/_css/2013.1/screen.css'
        extra = dict(REQUEST_URI=request_uri, SCRIPT_NAME='')
        headers = {ACCEPT_DATETIME: 'Sun, 26 Jan 2014 20:08:04 GMT'}

        resp = self.testapp.get('/x-ignore-this-x', extra_environ=extra, headers=headers)

        assert resp.status_int == 200

        # for timegate
        assert resp.headers[VARY] == 'accept-datetime'

        # for memento
        links = self.get_links(resp)
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="original timegate"' in links
        assert '<http://www.iana.org/_css/2013.1/screen.css>; rel="memento"; datetime="Sun, 26 Jan 2014 20:08:04 GMT"' in links
        #assert self.make_timemap_link('http://www.iana.org/_css/2013.1/screen.css') in links

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

    def test_non_memento_path(self):
        """
        Non WbUrl memento path -- just ignore ACCEPT_DATETIME
        """
        headers = {ACCEPT_DATETIME: 'Sun, 26 Jan 2014 20:08:04 GMT'}
        resp = self.testapp.get('/pywb/', headers=headers)
        assert resp.status_int == 200

    def test_non_memento_cdx_path(self):
        """
        CDX API Path -- different api, ignore ACCEPT_DATETIME for this
        """
        headers = {ACCEPT_DATETIME: 'Sun, 26 Jan 2014 20:08:04'}
        resp = self.testapp.get('/pywb-cdx', headers=headers, status=400)
        assert resp.status_int == 400
