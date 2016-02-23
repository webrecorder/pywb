from pytest import raises
from pywb.cdx.cdxobject import CDXObject
from pywb.utils.timeutils import timestamp_now

from .server_mock import make_setup_module, BaseIntegration

setup_module = make_setup_module('tests/test_config.yaml')

class TestWbIntegration(BaseIntegration):
    #def setup(self):
    #    self.app = app
    #    self.testapp = testapp

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
        assert '/pywb' in resp.text

    def test_pywb_root(self):
        resp = self.testapp.get('/pywb/')
        self._assert_basic_html(resp)
        assert 'Search' in resp.text

    def test_pywb_root_head(self):
        resp = self.testapp.head('/pywb/')
        assert resp.content_type == 'text/html'
        assert resp.status_int == 200

    def test_pywb_invalid_path(self):
        resp = self.testapp.head('/blah/', status=404)
        assert resp.content_type == 'text/html'
        assert resp.status_int == 404

    def test_calendar_query(self):
        resp = self.testapp.get('/pywb/*/iana.org')
        self._assert_basic_html(resp)
        # 3 Captures + header
        assert len(resp.html.find_all('tr')) == 4

    def test_calendar_query_filtered(self):
        # unfiltered collection
        resp = self.testapp.get('/pywb/*/http://www.iana.org/_css/2013.1/screen.css')
        self._assert_basic_html(resp)
        # 17 Captures + header
        assert len(resp.html.find_all('tr')) == 18

        # filtered collection
        resp = self.testapp.get('/pywb-filt/*/http://www.iana.org/_css/2013.1/screen.css')
        self._assert_basic_html(resp)
        # 1 Capture (filtered) + header
        assert len(resp.html.find_all('tr')) == 2

    def test_calendar_query_fuzzy_match(self):
        # fuzzy match removing _= according to standard rules.yaml
        resp = self.testapp.get('/pywb/*/http://www.iana.org/_css/2013.1/screen.css?_=3141592653')
        self._assert_basic_html(resp)
        # 17 Captures + header
        assert len(resp.html.find_all('tr')) == 18

    def test_calendar_not_found(self):
        # query with no results
        resp = self.testapp.get('/pywb/*/http://not-exist.example.com')
        self._assert_basic_html(resp)
        assert 'No captures found' in resp.text, resp.text
        assert len(resp.html.find_all('tr')) == 0

    def test_cdx_query(self):
        resp = self.testapp.get('/pywb/cdx_/*/http://www.iana.org/')
        self._assert_basic_text(resp)

        assert '20140127171238 http://www.iana.org/ warc/revisit - OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB' in resp
        # check for 3 cdx lines (strip final newline)
        actual_len = len(str(resp.text).rstrip().split('\n'))
        assert actual_len == 3, actual_len

    def test_replay_top_frame(self):
        resp = self.testapp.get('/pywb/20140127171238tf_/http://www.iana.org/')

        assert '<iframe ' in resp.text
        assert '/pywb/20140127171238/http://www.iana.org/' in resp.text, resp.text

    def test_replay_content(self):
        resp = self.testapp.get('/pywb/20140127171238/http://www.iana.org/')
        self._assert_basic_html(resp)

        assert '"20140127171238"' in resp.text
        assert 'wb.js' in resp.text
        assert 'new _WBWombat' in resp.text, resp.text
        assert '/pywb/20140127171238/http://www.iana.org/time-zones"' in resp.text

    def test_replay_non_frame_content(self):
        resp = self.testapp.get('/pywb-nonframe/20140127171238/http://www.iana.org/')
        self._assert_basic_html(resp)

        assert '"20140127171238"' in resp.text
        assert 'wb.js' in resp.text
        assert '/pywb-nonframe/20140127171238/http://www.iana.org/time-zones"' in resp.text

    def test_replay_non_surt(self):
        resp = self.testapp.get('/pywb-nosurt/20140103030321/http://example.com?example=1')
        self._assert_basic_html(resp)

        assert '"20140103030321"' in resp.text
        assert 'wb.js' in resp.text
        assert '/pywb-nosurt/20140103030321/http://www.iana.org/domains/example' in resp.text

    def test_replay_cdxj(self):
        resp = self.testapp.get('/pywb-cdxj/20140103030321/http://example.com?example=1')
        self._assert_basic_html(resp)

        assert '"20140103030321"' in resp.text
        assert 'wb.js' in resp.text
        assert '/pywb-cdxj/20140103030321/http://www.iana.org/domains/example' in resp.text

    def test_replay_cdxj_revisit(self):
        resp = self.testapp.get('/pywb-cdxj/20140103030341/http://example.com?example=1')
        self._assert_basic_html(resp)

        assert '"20140103030341"' in resp.text
        assert 'wb.js' in resp.text
        assert '/pywb-cdxj/20140103030341/http://www.iana.org/domains/example' in resp.text

    def test_zero_len_revisit(self):
        resp = self.testapp.get('/pywb/20140603030341/http://example.com?example=2')
        self._assert_basic_html(resp)

        assert '"20140603030341"' in resp.text
        assert 'wb.js' in resp.text
        assert '/pywb/20140603030341/http://www.iana.org/domains/example' in resp.text

    def test_replay_url_agnostic_revisit(self):
        resp = self.testapp.get('/pywb/20130729195151/http://www.example.com/')
        self._assert_basic_html(resp)

        assert '"20130729195151"' in resp.text
        assert 'wb.js' in resp.text
        assert '/pywb/20130729195151/http://www.iana.org/domains/example"' in resp.text

    def test_video_info_not_found(self):
        # not actually archived, but ensure video info path is tested
        resp = self.testapp.get('/pywb/vi_/https://www.youtube.com/watch?v=DjFZyFWSt1M', status=404)
        assert resp.status_int == 404

    def test_replay_cdx_mod(self):
        resp = self.testapp.get('/pywb/20140127171239cdx_/http://www.iana.org/_css/2013.1/print.css')
        self._assert_basic_text(resp)

        lines = resp.text.rstrip().split('\n')
        assert len(lines) == 17
        assert lines[0].startswith('org,iana)/_css/2013.1/print.css 20140127171239')


    def test_replay_banner_only(self):
        resp = self.testapp.get('/pywb/20140126201054bn_/http://www.iana.org/domains/reserved')

        # wb.js header insertion
        assert 'wb.js' in resp.text

        # no wombat present
        assert '_WBWombat' not in resp.text

        # url not rewritten
        #assert '"http://www.iana.org/domains/example"' in resp.text
        assert '"/_css/2013.1/screen.css"' in resp.text

    def test_replay_identity_1(self):
        resp = self.testapp.get('/pywb/20140127171251id_/http://example.com')

        # no wb header insertion
        assert 'wb.js' not in resp.text

        assert resp.content_length == 1270, resp.content_length

        # original unrewritten url present
        assert '"http://www.iana.org/domains/example"' in resp.text

    def test_replay_range_cache_content(self):
        headers = [('Range', 'bytes=0-200')]
        resp = self.testapp.get('/pywb/20140127171250id_/http://example.com', headers=headers)

        assert resp.status_int == 206
        assert resp.headers['Accept-Ranges'] == 'bytes'
        assert resp.headers['Content-Range'] == 'bytes 0-200/1270', resp.headers['Content-Range']
        assert resp.content_length == 201, resp.content_length

        assert 'wb.js' not in resp.text

    def test_replay_content_ignore_range(self):
        headers = [('Range', 'bytes=0-200')]
        resp = self.testapp.get('/pywb-norange/20140127171251id_/http://example.com', headers=headers)

        # range request ignored
        assert resp.status_int == 200

        # full response
        assert resp.content_length == 1270, resp.content_length

        # identity, no header insertion
        assert 'wb.js' not in resp.text

    def test_replay_range_cache_content_bound_end(self):
        headers = [('Range', 'bytes=10-10000')]
        resp = self.testapp.get('/pywb/20140127171251id_/http://example.com', headers=headers)

        assert resp.status_int == 206
        assert resp.headers['Accept-Ranges'] == 'bytes'
        assert resp.headers['Content-Range'] == 'bytes 10-1269/1270', resp.headers['Content-Range']
        assert resp.content_length == 1260, resp.content_length
        assert len(resp.text) == resp.content_length

        assert 'wb.js' not in resp.text

    def test_replay_redir_no_cache(self):
        headers = [('Range', 'bytes=10-10000')]
        # Range ignored
        resp = self.testapp.get('/pywb/20140126200927/http://www.iana.org/domains/root/db/', headers=headers)
        assert resp.content_length == 0
        assert resp.status_int == 302

    def test_replay_identity_2_arcgz(self):
        resp = self.testapp.get('/pywb/20140216050221id_/http://arc.gz.test.example.com')

        # no wb header insertion
        assert 'wb.js' not in resp.text

        # original unrewritten url present
        assert '"http://www.iana.org/domains/example"' in resp.text

    def test_replay_identity_2_arc(self):
        resp = self.testapp.get('/pywb/20140216050221id_/http://arc.test.example.com')

        # no wb header insertion
        assert 'wb.js' not in resp.text

        # original unrewritten url present
        assert '"http://www.iana.org/domains/example"' in resp.text

    def test_replay_content_length_1(self):
        # test larger file, rewritten file (svg!)
        resp = self.testapp.get('/pywb/20140126200654/http://www.iana.org/_img/2013.1/rir-map.svg')
        assert resp.headers['Content-Length'] == str(len(resp.text))

    def test_replay_css_mod(self):
        resp = self.testapp.get('/pywb/20140127171239cs_/http://www.iana.org/_css/2013.1/screen.css')
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'

    def test_replay_js_mod(self):
        # an empty js file
        resp = self.testapp.get('/pywb/20140126201054js_/http://www.iana.org/_js/2013.1/iana.js')
        assert resp.status_int == 200
        assert resp.content_length == 0
        assert resp.content_type == 'application/x-javascript'

    def test_redirect_exact(self):
        resp = self.testapp.get('/pywb/20140127171237/http://www.iana.org/')
        assert resp.status_int == 302

        assert resp.headers['Location'].endswith('/pywb/20140127171238/http://iana.org')

    def test_no_redirect_non_exact(self):
        # non-exact mode, don't redirect to exact capture
        resp = self.testapp.get('/pywb-non-exact/20140127171237/http://www.iana.org/')
        assert resp.status_int == 200

        self._assert_basic_html(resp)
        assert '"20140127171237"' in resp.text
        # actual timestamp set in JS
        assert 'timestamp = "20140127171238"' in resp.text
        assert '/pywb-non-exact/20140127171237/http://www.iana.org/about/' in resp.text

    def test_redirect_latest_replay(self):
        resp = self.testapp.get('/pywb/http://example.com/')
        assert resp.status_int == 302

        assert resp.headers['Location'].endswith('/20140127171251/http://example.com')
        resp = resp.follow()

        #check resp
        self._assert_basic_html(resp)
        assert '"20140127171251"' in resp.text
        assert '/pywb/20140127171251/http://www.iana.org/domains/example' in resp.text

    def test_redirect_non_exact_latest_replay_ts(self):
        resp = self.testapp.get('/pywb-non-exact/http://example.com/')
        assert resp.status_int == 200

        assert resp.headers['Content-Location'].endswith('/http://example.com')

        # extract ts, which should be current time
        ts = resp.headers['Content-Location'].rsplit('/http://')[0].rsplit('/', 1)[-1]
        assert ts == '20140127171251'
        #resp = resp.follow()

        #self._assert_basic_html(resp)

        # ensure the current ts is present in the links
        assert '"{0}"'.format(ts) in resp.text
        assert '/pywb-non-exact/http://www.iana.org/domains/example' in resp.text

        # ensure ts is current ts
        #assert timestamp_now() >= ts, ts

    def test_redirect_relative_3(self):
        # webtest uses Host: localhost:80 by default
        # first two requests should result in same redirect
        target = 'http://localhost:80/pywb/2014/http://iana.org/_css/2013.1/screen.css'

        # without timestamp
        resp = self.testapp.get('/_css/2013.1/screen.css', headers = [('Referer', 'http://localhost:80/pywb/2014/http://iana.org/')])
        assert resp.status_int == 302
        assert resp.headers['Location'] == target, resp.headers['Location']

        # with timestamp
        resp = self.testapp.get('/2014/_css/2013.1/screen.css', headers = [('Referer', 'http://localhost:80/pywb/2014/http://iana.org/')])
        assert resp.status_int == 302
        assert resp.headers['Location'] == target, resp.headers['Location']


        resp = resp.follow()
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/pywb/20140127171239/http://www.iana.org/_css/2013.1/screen.css')

        resp = resp.follow()
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'

    def test_rel_self_redirect(self):
        uri = '/pywb/20140126200927/http://www.iana.org/domains/root/db'
        resp = self.testapp.get(uri, status=302)
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/pywb/20140126200928/http://www.iana.org/domains/root/db')

    #def test_referrer_self_redirect(self):
    #    uri = '/pywb/20140127171239/http://www.iana.org/_css/2013.1/screen.css'
    #    host = 'somehost:8082'
    #    referrer = 'http://' + host + uri

        # capture is normally a 200
    #    resp = self.testapp.get(uri)
    #    assert resp.status_int == 200

        # redirect causes skip of this capture, redirect to next
    #    resp = self.testapp.get(uri, headers = [('Referer', referrer), ('Host', host)], status = 302)
    #    assert resp.status_int == 302

    def test_not_existant_warc_other_capture(self):
        resp = self.testapp.get('/pywb/20140703030321/http://example.com?example=2')
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/pywb/20140603030341/http://example.com?example=2')

    def test_missing_revisit_other_capture(self):
        resp = self.testapp.get('/pywb/20140603030351/http://example.com?example=2')
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/pywb/20140603030341/http://example.com?example=2')

    def test_not_existant_warc_no_other(self):
        resp = self.testapp.get('/pywb/20140703030321/http://example.com?example=3', status = 503)
        assert resp.status_int == 503

    def test_missing_revisit_no_other(self):
        resp = self.testapp.get('/pywb/20140603030351/http://example.com?example=3', status = 503)
        assert resp.status_int == 503

    def test_live_frame(self):
        resp = self.testapp.get('/live/http://example.com/?test=test')
        assert resp.status_int == 200

    def test_live_redir_1(self):
        resp = self.testapp.get('/live/*/http://example.com/?test=test')
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/live/http://example.com/?test=test')

    def test_live_redir_2(self):
        resp = self.testapp.get('/live/2010-2011/http://example.com/?test=test')
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/live/http://example.com/?test=test')

    def test_live_fallback(self):
        resp = self.testapp.get('/pywb-fallback//http://example.com/?test=test')
        assert resp.status_int == 200

    def test_post_1(self):
        resp = self.testapp.post('/pywb/httpbin.org/post', {'foo': 'bar', 'test': 'abc'})

        # no redirects for POST, as some browsers (FF) show modal confirmation dialog!
        #assert resp.status_int == 307
        #assert resp.headers['Location'].endswith('/pywb/20140610000859/http://httpbin.org/post')

        # XX webtest doesn't support 307 redirect of post
        #resp = resp.follow()
        #resp = self.testapp.post(resp.headers['Location'], {'foo': 'bar', 'test': 'abc'})

        assert resp.status_int == 200
        assert '"foo": "bar"' in resp.text
        assert '"test": "abc"' in resp.text

    def test_post_2(self):
        resp = self.testapp.post('/pywb/20140610001255/http://httpbin.org/post?foo=bar', {'data': '^'})
        assert resp.status_int == 200
        assert '"data": "^"' in resp.text

    def test_post_invalid(self):
        # not json
        resp = self.testapp.post_json('/pywb/20140610001255/http://httpbin.org/post?foo=bar', {'data': '^'}, status=404)
        assert resp.status_int == 404

    def test_post_redirect(self):
        # post handled without redirect (since 307 not allowed)
        resp = self.testapp.post('/post', {'foo': 'bar', 'test': 'abc'}, headers=[('Referer', 'http://localhost:80/pywb/2014/http://httpbin.org/post')])
        assert resp.status_int == 200
        assert '"foo": "bar"' in resp.text
        assert '"test": "abc"' in resp.text

    def test_excluded_content(self):
        resp = self.testapp.get('/pywb/http://www.iana.org/_img/bookmark_icon.ico', status=403)
        assert resp.status_int == 403
        assert 'Excluded' in resp.text

    def test_replay_not_found(self):
        resp = self.testapp.head('/pywb/http://not-exist.example.com', status=404)
        assert resp.content_type == 'text/html'
        assert resp.status_int == 404

    def test_static_content(self):
        resp = self.testapp.get('/static/test/route/wb.css')
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'
        assert resp.content_length > 0

    def test_static_content_filewrapper(self):
        from wsgiref.util import FileWrapper
        resp = self.testapp.get('/static/test/route/wb.css', extra_environ = {'wsgi.file_wrapper': FileWrapper})
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'
        assert resp.content_length > 0

    def test_static_not_found(self):
        resp = self.testapp.get('/static/test/route/notfound.css', status = 404)
        assert resp.status_int == 404

    def test_cdx_server_filters(self):
        resp = self.testapp.get('/pywb-cdx?url=http://www.iana.org/_css/2013.1/screen.css&filter=mime:warc/revisit&filter=filename:dupes.warc.gz')
        self._assert_basic_text(resp)
        actual_len = len(resp.text.rstrip().split('\n'))
        assert actual_len == 1, actual_len

    def test_cdx_server_advanced(self):
        # combine collapsing, reversing and revisit resolving
        resp = self.testapp.get('/pywb-cdx?url=http://www.iana.org/_css/2013.1/print.css&collapseTime=11&resolveRevisits=true&reverse=true')

        # convert back to CDXObject
        cdxs = list(map(CDXObject, resp.body.rstrip().split(b'\n')))
        assert len(cdxs) == 3, len(cdxs)

        # verify timestamps
        timestamps = list(map(lambda cdx: cdx['timestamp'], cdxs))
        assert timestamps == ['20140127171239', '20140126201054', '20140126200625']

        # verify orig filenames (2 revisits, one non)
        origfilenames = list(map(lambda cdx: cdx['orig.filename'], cdxs))
        assert origfilenames == ['iana.warc.gz', 'iana.warc.gz', '-']


    # surt() no longer errors on this in 0.3b
    #def test_error(self):
    #    resp = self.testapp.get('/pywb/?abc', status = 400)
    #    assert resp.status_int == 400
    #    assert 'Invalid Url: http://?abc' in resp.text


    def test_coll_info_json(self):
        resp = self.testapp.get('/collinfo.json')
        assert resp.content_type == 'application/json'
        assert len(resp.json) == 9

   #def test_invalid_config(self):
    #    with raises(IOError):
    #        init_app(create_wb_router,
    #                 load_yaml=True,
    #                 config_file='x-invalid-x')


