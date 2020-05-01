from .base_config_test import BaseConfigTest, fmod

from pywb.warcserver.index.cdxobject import CDXObject


# ============================================================================
class TestWbIntegration(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestWbIntegration, cls).setup_class('config_test.yaml')

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

    def test_pywb_invalid_collection(self):
        resp = self.testapp.get('/blah/http://example.com/', status=404)
        assert resp.content_type == 'text/html'
        assert resp.status_int == 404

        assert 'Collection not found: <b>blah</b>' in resp.text

    def test_calendar_query(self):
        resp = self.testapp.get('/pywb/*/iana.org')
        self._assert_basic_html(resp)
        # 3 Captures + header
        #assert len(resp.html.find_all('tr')) == 4

    def test_calendar_query_2(self):
        # unfiltered collection
        resp = self.testapp.get('/pywb/*/http://www.iana.org/_css/2013.1/screen.css')
        self._assert_basic_html(resp)
        # 17 Captures + header
        #assert len(resp.html.find_all('tr')) == 18

        # filtered collection
        #resp = self.testapp.get('/pywb-filt/*/http://www.iana.org/_css/2013.1/screen.css')
        #self._assert_basic_html(resp)
        # 1 Capture (filtered) + header
        #assert len(resp.html.find_all('tr')) == 2

    def test_cdxj_query_fuzzy_match(self):
        # fuzzy match removing _= according to standard rules.yaml
        resp = self.testapp.get('/pywb/cdx?url=http://www.iana.org/_css/2013.1/screen.css%3F_=3141592653')
        assert len(resp.text.rstrip().split('\n')) == 17

    def test_cdxj_query_fuzzy_match_add_slash(self):
        # fuzzy match removing _= according to standard rules.yaml
        resp = self.testapp.get('/pywb/cdx?url=http://www.iana.org/_css/2013.1/screen.css/%3F_=3141592653')
        # 17 Captures + header
        assert len(resp.text.rstrip().split('\n')) == 17

    def test_cdxj_not_found(self):
        # query with no results
        resp = self.testapp.get('/pywb/cdx?url=http://not-exist.example.com')
        assert resp.text == ''

    def test_cdxj_query(self):
        resp = self.testapp.get('/pywb/cdx?url=http://www.iana.org/')

        assert 'org,iana)/ 20140126200624 {"url": "http://www.iana.org/", "mime": "text/html", "status": "200", "digest": "OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB"' in resp.text

        # check for 3 cdx lines (strip final newline)
        assert len(resp.text.rstrip().split('\n')) == 3

    def test_replay_top_frame(self):
        resp = self.testapp.get('/pywb/20140127171238/http://www.iana.org/')

        assert 'new ContentFrame' in resp.text
        assert '"20140127171238"' in resp.text
        assert 'http://www.iana.org/' in resp.text, resp.text

        assert 'Content-Security-Policy' not in resp.headers

    def test_replay_content_head(self, fmod):
        resp = self.head('/pywb/20140127171238{0}/http://www.iana.org/', fmod, status=200)
        assert not resp.headers.get('Content-Length')

    def test_replay_content_head_non_zero_content_length_match(self):
        resp = self.testapp.get('/pywb/id_/http://www.iana.org/_js/2013.1/jquery.js', status=200)
        length = resp.content_length

        # Content-Length included if non-zero
        resp = self.testapp.head('/pywb/id_/http://www.iana.org/_js/2013.1/jquery.js', status=200)

        #assert resp.headers['Content-Length'] == length
        assert resp.content_length == length

    def test_replay_content(self, fmod):
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/', fmod)
        self._assert_basic_html(resp)

        assert '"20140127171238"' in resp.text, resp.text
        assert 'wombat.js' in resp.text
        assert 'transclusions.js' in resp.text
        assert '_WBWombatInit' in resp.text, resp.text
        assert 'wbinfo.enable_auto_fetch = false;' in resp.text
        assert '/pywb/20140127171238{0}/http://www.iana.org/time-zones"'.format(fmod) in resp.text

        if fmod == 'mp_':
            assert 'window == window.top' in resp.text
            assert 'wbinfo.is_framed = true' in resp.text
        else:
            assert 'window == window.top' not in resp.text
            assert 'wbinfo.is_framed = false' in resp.text

        csp = "default-src 'unsafe-eval' 'unsafe-inline' 'self' data: blob: mediastream: ws: wss: ; form-action 'self'"
        assert resp.headers['Content-Security-Policy'] == csp

    def test_replay_resource(self, fmod):
        resp = self.get('/pywb/20171122230223{0}/http://httpbin.org/anything/resource.json', fmod)
        assert resp.headers['Content-Type'] == 'application/json'

    def test_replay_redirect(self, fmod):
        resp = self.get('/pywb/2014{0}/http://www.iana.org/domains/example', fmod)
        assert resp.headers['Location'].startswith('/pywb/2014{0}/'.format(fmod))
        assert resp.status_code == 302

    def test_replay_fuzzy_1(self, fmod):
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/?_=123', fmod)
        assert resp.status_int == 200
        assert resp.headers['Content-Location'].endswith('/pywb/20140126200624{0}/http://www.iana.org/'.format(fmod))

    def test_replay_no_fuzzy_match(self, fmod):
        resp = self.get('/pywb/20140127171238{0}/http://www.iana.org/?foo=bar', fmod, status=404)
        assert resp.status_int == 404

    def test_no_slash_redir_1(self, fmod):
        resp = self.get('/pywb/20140103030321{0}/http://example.com', fmod)
        assert resp.status_int == 307
        assert resp.headers['Location'].endswith('/pywb/20140103030321{0}/http://example.com/'.format(fmod))

    def test_no_slash_redir_2(self, fmod):
        resp = self.get('/pywb/20140103030321{0}/http://example.com?example=1', fmod)
        assert resp.status_int == 307
        assert resp.headers['Location'].endswith('/pywb/20140103030321{0}/http://example.com/?example=1'.format(fmod))

    def test_replay_cdxj(self, fmod):
        resp = self.get('/pywb-cdxj/20140103030321{0}/http://example.com/?example=1', fmod)
        self._assert_basic_html(resp)

        assert '"20140103030321"' in resp.text
        assert 'wombat.js' in resp.text
        assert '/pywb-cdxj/20140103030321{0}/http://www.iana.org/domains/example'.format(fmod) in resp.text

    def test_replay_cdxj_revisit(self, fmod):
        resp = self.get('/pywb-cdxj/20140103030341{0}/http://example.com/?example=1', fmod)
        self._assert_basic_html(resp)

        assert '"20140103030341"' in resp.text
        assert 'wombat.js' in resp.text
        assert '/pywb-cdxj/20140103030341{0}/http://www.iana.org/domains/example'.format(fmod) in resp.text

    def test_zero_len_revisit(self, fmod):
        resp = self.get('/pywb/20140603030341{0}/http://example.com/?example=2', fmod)
        self._assert_basic_html(resp)

        assert '"20140603030341"' in resp.text
        assert 'wombat.js' in resp.text
        assert '/pywb/20140603030341{0}/http://www.iana.org/domains/example'.format(fmod) in resp.text

    def test_replay_url_agnostic_revisit(self, fmod):
        resp = self.get('/pywb/20130729195151{0}/http://www.example.com/', fmod)
        self._assert_basic_html(resp)

        assert '"20130729195151"' in resp.text
        assert 'wombat.js' in resp.text
        assert '/pywb/20130729195151{0}/http://www.iana.org/domains/example"'.format(fmod) in resp.text

    def test_video_info_not_found(self):
        # not actually archived, but ensure video info path is tested
        resp = self.testapp.get('/pywb/vi_/https://www.youtube.com/watch?v=DjFZyFWSt1M', status=404)
        assert resp.status_int == 404

    def test_replay_banner_only(self):
        resp = self.testapp.get('/pywb/20140126201054bn_/http://www.iana.org/domains/reserved')

        # wombat.js header not inserted
        assert 'wombat.js' not in resp.text

        # no wombat present
        assert '_WBWombat' not in resp.text

        # top-frame redirect check
        assert 'window == window.top' in resp.text

        # url not rewritten
        #assert '"http://www.iana.org/domains/example"' in resp.text
        assert '"/_css/2013.1/screen.css"' in resp.text

    def test_replay_identity_1(self):
        resp = self.testapp.get('/pywb/20140127171251id_/http://example.com/')

        # no wb header insertion
        assert 'wombat.js' not in resp.text

        assert resp.content_length == 1270, resp.content_length

        # original unrewritten url present
        assert '"http://www.iana.org/domains/example"' in resp.text

    def test_replay_identity_2_arcgz(self):
        resp = self.testapp.get('/pywb/20140216050221id_/http://arc.gz.test.example.com/')

        # no wb header insertion
        assert 'wombat.js' not in resp.text

        # original unrewritten url present
        assert '"http://www.iana.org/domains/example"' in resp.text

    def test_replay_identity_2_arc(self):
        resp = self.testapp.get('/pywb/20140216050221id_/http://arc.test.example.com/')

        # no wb header insertion
        assert 'wombat.js' not in resp.text

        # original unrewritten url present
        assert '"http://www.iana.org/domains/example"' in resp.text

    def test_replay_content_length_1(self, fmod):
        # test larger file, rewritten file (svg!)
        resp = self.get('/pywb/20140126200654{0}/http://www.iana.org/_img/2013.1/rir-map.svg', fmod)
        assert resp.headers['Content-Length'] == str(len(resp.text))

    def test_replay_css_mod(self):
        resp = self.testapp.get('/pywb/20140127171239cs_/http://www.iana.org/_css/2013.1/screen.css')
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'

    def test_replay_js_mod_no_obj_proxy(self):
        # an empty js file, (ie11 UA no js obj proxy)
        resp = self.testapp.get('/pywb/20140126201054js_/http://www.iana.org/_js/2013.1/iana.js',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko'})

        assert resp.status_int == 200
        assert resp.content_length == 0
        assert resp.content_type == 'application/x-javascript'

    def test_replay_js_obj_proxy(self, fmod):
        # test js proxy obj with jquery -- no user agent
        resp = self.get('/pywb/20140126200625{0}/http://www.iana.org/_js/2013.1/jquery.js', fmod)

        assert resp.status_int == 200
        assert resp.content_length != 0
        assert resp.content_type == 'application/x-javascript'

        # test with Chrome user agent
        resp = self.get('/pywb/20140126200625{0}/http://www.iana.org/_js/2013.1/jquery.js', fmod,
                        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'})
        assert 'let window = _____WB$wombat$assign$function_____(' in resp.text

    def test_replay_js_ie11_no_obj_proxy(self, fmod):
        # IE11 user-agent, no proxy
        resp = self.get('/pywb/20140126200625{0}/http://www.iana.org/_js/2013.1/jquery.js', fmod,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko'})

        assert 'let window = _____WB$wombat$assign$function_____(' not in resp.text

    def test_replay_non_exact(self, fmod):
        # non-exact mode, don't redirect to exact capture
        resp = self.get('/pywb/20140127171237{0}/http://www.iana.org/', fmod)
        assert resp.status_int == 200

        self._assert_basic_html(resp)
        assert '"20140127171237"' in resp.text
        # actual timestamp set in JS
        assert 'timestamp = "20140127171238"' in resp.text
        assert '/pywb/20140127171237{0}/http://www.iana.org/about/'.format(fmod) in resp.text

    def test_latest_replay(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/{0}http://example.com/', fmod_slash)
        self._assert_basic_html(resp)

        assert resp.headers['Content-Location'].endswith('/20140127171251{0}/http://example.com'.format(fmod))

        assert '"20140127171251"' in resp.text
        assert '/pywb/{0}http://www.iana.org/domains/example'.format(fmod_slash) in resp.text, resp.text

    def test_replay_content_bad_status_text(self, fmod):
        # test larger file, rewritten file (svg!)
        resp = self.get('/pywb/20140127171238{0}/https://iana.org/bads', fmod)
        assert resp.headers['Content-Length'] == str(len(resp.text))

    def test_replay_non_latest_content_location_ts(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/{0}http://example.com/', fmod_slash)
        assert resp.status_int == 200

        assert resp.headers['Content-Location'].endswith('/http://example.com')

        # extract ts, which should be current time
        ts = resp.headers['Content-Location'].rsplit('/http://')[0].rsplit('/', 1)[-1]
        assert ts == '20140127171251{0}'.format(fmod)

        if fmod:
            ts = ts.replace(fmod, '')

        # ensure the current ts is present in the links
        assert '"{0}"'.format(ts) in resp.text
        assert '/pywb/{0}http://www.iana.org/domains/example'.format(fmod_slash) in resp.text

        # ensure ts is current ts
        #assert timestamp_now() >= ts, ts

    def test_refer_redirect(self, fmod):
        # webtest uses Host: localhost:80 by default
        target = 'http://localhost:80/pywb/2014{0}/http://iana.org/_css/2013.1/screen.css'.format(fmod)

        resp = self.get('/_css/2013.1/screen.css', fmod, headers=[('Referer', 'http://localhost:80/pywb/2014{0}/http://iana.org/'.format(fmod))])
        assert resp.status_int == 307
        assert resp.headers['Location'] == target, resp.headers['Location']

        resp = resp.follow()
        assert resp.status_int == 200
        assert resp.headers['Content-Location'].endswith('/pywb/20140127171239{0}/http://www.iana.org/_css/2013.1/screen.css'.format(fmod))
        assert resp.content_type == 'text/css'

    def test_non_exact_replay_skip_self_redir(self, fmod):
        uri = '/pywb/20140126200927{0}/http://www.iana.org/domains/root/db'
        resp = self.get(uri, fmod)
        assert resp.status_int == 200
        assert resp.headers['Content-Location'].endswith('/pywb/20140126200928{0}/http://www.iana.org/domains/root/db'.format(fmod))

    def test_non_exact_replay_skip_self_redir_slash(self, fmod):
        uri = '/pywb/20140126200927{0}/http://www.iana.org/domains/root/db/'
        resp = self.get(uri, fmod)
        assert resp.status_int == 200
        assert resp.headers['Content-Location'].endswith('/pywb/20140126200928{0}/http://www.iana.org/domains/root/db'.format(fmod))

    def test_not_existant_warc_other_capture(self, fmod):
        resp = self.get('/pywb/20140703030321{0}/http://example.com/?example=2', fmod)
        assert resp.status_int == 200
        assert resp.headers['Content-Location'].endswith('/pywb/20140603030341{0}/http://example.com?example=2'.format(fmod))

    def test_missing_revisit_other_capture(self, fmod):
        resp = self.get('/pywb/20140603030351{0}/http://example.com/?example=2', fmod)
        assert resp.status_int == 200
        assert resp.headers['Content-Location'].endswith('/pywb/20140603030341{0}/http://example.com?example=2'.format(fmod))

    def test_not_existant_warc_no_other(self, fmod):
        resp = self.get('/pywb/20140703030321{0}/http://example.com/?example=3', fmod, status=503)
        assert resp.status_int == 503

    def test_missing_revisit_no_other(self, fmod):
        resp = self.get('/pywb/20140603030351{0}/http://example.com/?example=3', fmod, status=503)
        assert resp.status_int == 503

    def test_live_frame(self):
        resp = self.testapp.get('/live/http://example.com/?test=test')
        assert resp.status_int == 200

    def _test_live_redir_1(self):
        resp = self.testapp.get('/live/*/http://example.com/?test=test')
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/live/http://example.com/?test=test')

    def _test_live_redir_2(self):
        resp = self.testapp.get('/live/2010-2011/http://example.com/?test=test')
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/live/http://example.com/?test=test')

    def test_live_fallback(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb-fallback/{0}http://example.com/?test=test', fmod_slash)
        assert resp.status_int == 200

    def test_post_1(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.post('/pywb/{0}httpbin.org/post', fmod_slash, {'foo': 'bar', 'test': 'abc'})

        assert resp.status_int == 200
        assert '"foo": "bar"' in resp.text
        assert '"test": "abc"' in resp.text

    def test_post_2(self, fmod):
        resp = self.post('/pywb/20140610001255{0}/http://httpbin.org/post?foo=bar', fmod, {'data': '^'})
        assert resp.status_int == 200
        assert '"data": "^"' in resp.text

    def test_post_invalid(self, fmod):
        # not json
        resp = self.post_json('/pywb/20140610001255{0}/http://httpbin.org/post?foo=bar', fmod, {'data': '^'}, status=404)
        assert resp.status_int == 404

    def test_post_referer_redirect(self, fmod):
        # allowing 307 redirects
        resp = self.post('/post', fmod,
                         {'foo': 'bar', 'test': 'abc'},
                         headers=[('Referer', 'http://localhost:80/pywb/2014{0}/http://httpbin.org/foo'.format(fmod))])

        assert resp.status_int == 307
        assert resp.headers['Location'].endswith('/pywb/2014{0}/http://httpbin.org/post'.format(fmod))

    def test_get_referer_redirect(self, fmod):
        resp = self.get('/get', fmod,
                         headers=[('Referer', 'http://localhost:80/pywb/2014{0}/http://httpbin.org/foo'.format(fmod))])

        assert resp.status_int == 307
        assert resp.headers['Location'].endswith('/pywb/2014{0}/http://httpbin.org/get'.format(fmod))

    def _test_excluded_content(self):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/{0}http://www.iana.org/_img/bookmark_icon.ico', fmod_slash, status=403)
        assert resp.status_int == 403
        assert 'Excluded' in resp.text

    def test_replay_not_found(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        resp = self.get('/pywb/{0}http://not-exist.example.com/path?A=B', fmod_slash, status=404)
        assert resp.content_type == 'text/html'
        assert resp.status_int == 404

        assert 'URL Not Found' in resp.text, resp.text
        assert 'The url <b>http://not-exist.example.com/path?A=B</b> could not be found in this collection.' in resp.text

    def test_static_content(self):
        resp = self.testapp.get('/static/default_banner.css')
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'
        assert resp.content_length > 0

    def test_static_content_filewrapper(self):
        from wsgiref.util import FileWrapper
        resp = self.testapp.get('/static/default_banner.css', extra_environ = {'wsgi.file_wrapper': FileWrapper})
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'
        assert resp.content_length > 0

    def test_static_nested_dir(self):
        resp = self.testapp.get('/static/fonts/font-awesome/fa-brands-400.eot')
        assert resp.status_int == 200
        assert resp.content_length > 0

    def test_static_not_found(self):
        resp = self.testapp.get('/static/notfound.css', status = 404)
        assert resp.status_int == 404

        assert 'Static file not found: <b>notfound.css</b>' in resp.text

    def test_cdx_server_filters(self):
        resp = self.testapp.get('/pywb/cdx?url=http://www.iana.org/_css/2013.1/screen.css&filter=mime:warc/revisit&filter=filename:dupes.warc.gz')
        assert resp.content_type == 'text/x-cdxj'
        actual_len = len(resp.text.rstrip().split('\n'))
        assert actual_len == 1, actual_len

    def test_cdx_server_advanced(self):
        # combine collapsing, reversing and revisit resolving
        resp = self.testapp.get('/pywb/cdx?url=http://www.iana.org/_css/2013.1/print.css&collapseTime=11&resolveRevisits=true&reverse=true')

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
        value = resp.json
        assert len(value['fixed']) == 4
        assert len(value['dynamic']) == 0

   #def test_invalid_config(self):
    #    with raises(IOError):
    #        init_app(create_wb_router,
    #                 load_yaml=True,
    #                 config_file='x-invalid-x')


