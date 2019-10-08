from pywb.warcserver.index.fuzzymatcher import FuzzyMatcher
from pywb.utils.canonicalize import canonicalize

from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.indexsource import BaseIndexSource


# ============================================================================
class EchoParamsSource(BaseIndexSource):
    def load_index(self, params):
        # return nothing for exact match to force fuzzy
        if params.get('matchType', 'exact') == 'exact':
            return iter([])

        assert params.get('is_fuzzy') == '1'
        assert params.get('limit') == '100'

        cdx = {'urlkey': canonicalize(params.get('cdx_url')),
               'mime': params.get('mime'),
               'filter': params.get('filter'),
               'url': params.get('cdx_url'),
              }

        return iter([cdx])


# ============================================================================
class TestFuzzy(object):
    @classmethod
    def setup_class(cls):
        cls.source = SimpleAggregator({'source': EchoParamsSource()})
        cls.fuzzy = FuzzyMatcher()

    def get_params(self, url, actual_url, mime='text/html'):
        params = {'url': url,
                  'cdx_url': actual_url,
                  'key': canonicalize(url),
                  'mime': mime}
        return params

    def get_expected(self, url, mime='text/html', filters=None):
        filters = filters or {'urlkey:'}
        exp = [{'filter': filters,
               'is_fuzzy': '1',
               'urlkey': canonicalize(url),
               'source': 'source',
               'source-coll': 'source',
               'url': url,
               'mime': mime}]

        return exp

    def test_no_fuzzy(self):
        params = self.get_params('http://example.com/', 'http://example.com/foo')
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_fuzzy_no_ext_ts(self):
        url = 'http://example.com/?_=123'
        actual_url = 'http://example.com/'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_allowed_ext(self):
        url = 'http://example.com/somefile.html?a=b'
        actual_url = 'http://example.com/somefile.html'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_php_ts(self):
        url = 'http://example.com/somefile.php?_=123'
        actual_url = 'http://example.com/somefile.php'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_mime_swf(self):
        url = 'http://example.com/somefile.php?a=b'
        actual_url = 'http://example.com/somefile.php'
        mime = 'application/x-shockwave-flash'
        params = self.get_params(url, actual_url, mime)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url, mime)

    def test_fuzzy_ga_utm(self):
        url = 'http://example.com/someresponse?_=1234&utm_A=123&id=xyz&utm_robot=blue&utm_foo=bar&A=B&utm_id=xyz'
        actual_url = 'http://example.com/someresponse?utm_B=234&id=xyz&utm_bar=foo&utm_foo=bar&_=789&A=B'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_jquery(self):
        url = 'http://example.com/someresponse?a=b&foocallbackname=jQuery123_456&foo=bar&_=12345&'
        actual_url = 'http://example.com/someresponse?a=b&foocallbackname=jQuery789_000&foo=bar&_=789&'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_jquery_2(self):
        # test removal of two adjacent params
        url = 'http://example.com/someresponse?_=1234&callbackname=jQuery123_456&foo=bar'
        actual_url = 'http://example.com/someresponse?_=123&callbackname=jQuery789_000&foo=bar'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_custom_rule_yt(self):
        url = 'http://youtube.com/get_video_info?a=b&html5=true&___abc=123&video_id=ABCD&id=1234'
        actual_url = 'http://youtube.com/get_video_info?a=d&html5=true&___abc=125&video_id=ABCD&id=1234'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        filters = {'urlkey:html5=true', 'urlkey:video_id=abcd'}
        assert list(cdx_iter) == self.get_expected(url=actual_url, filters=filters)

    def test_fuzzy_custom_rule_yt_2(self):
        url = 'https://r1---sn-xyz.googlevideo.com/videoplayback?id=ABCDEFG&itag=22&food=abc'
        actual_url = 'https://r1---sn-abcdefg.googlevideo.com/videoplayback?id=ABCDEFG&itag=22&foo=abc&_1=2'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        filters = {'urlkey:id=abcdefg',
                   'urlkey:itag=22',
                   '!mimetype:text/plain'}

        assert list(cdx_iter) == self.get_expected(url=actual_url, filters=filters)

    def test_fuzzy_find_all_rule(self):
        url = 'http://facebook.com/ajax/pagelet/generic.php/photoviewerpagelet?data={"cursor":"ABC","food":"bar","cursorindex":6,"A":12345,"B":"foo"}'
        actual_url = 'http://facebook.com/ajax/pagelet/generic.php/photoviewerpagelet?data={"some":data","cursor":"ABC","foo":"bar","cursorindex":6}'

        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        filters = {'urlkey:"cursor":"abc"',
                   'urlkey:"cursorindex":6'}

        assert list(cdx_iter) == self.get_expected(url=actual_url, filters=filters)

    def test_fuzzy_bar_baz_with_ext(self):
        url = 'http://example.com/foo/bar.png?abc'
        actual_url = 'http://example.com/foo/bar.png'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(url=actual_url)

    def test_fuzzy_bar_baz_with_ext_2(self):
        url = 'http://example.com/foo/bar.png?abc'
        actual_url = 'http://example.com/foo/bar.png?def'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(url=actual_url)

    def test_fuzzy_bar_baz_with_ext_3(self):
        url = 'http://example.com/foo/bar.png'
        actual_url = 'http://example.com/foo/bar.png?xyz'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(url=actual_url)

    def test_no_fuzzy_bar_baz_with_ext(self):
        url = 'http://example.com/foo/bar.png?abc'
        actual_url = 'http://example.com/foo/bar'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_disabled(self):
        url = 'http://example.com/?_=123'
        actual_url = 'http://example.com/'
        params = self.get_params(url, actual_url)
        params['allowFuzzy'] = 0
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_custom_rule_video_id_diff(self):
        url = 'http://youtube.com/get_video_info?a=b&html=true&___abc=123&video_id=ABCD&id=1234'
        actual_url = 'http://youtube.com/get_video_info?a=d&html=true&___abc=125&video_id=ABCE&id=1234'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_custom_rule_arg_missing(self):
        url = 'http://youtube.com/get_video_info?a=b&html5=&___abc=123&video_id=ABCD&id=1234'
        actual_url = 'http://youtube.com/get_video_info?a=d&html5=&___abc=125&video_id=ABCD&id=1234'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_ext_restrict(self):
        url = 'http://example.com/somefile.php?a=b'
        actual_url = 'http://example.com/'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_ga_utm(self):
        url = 'http://example.com/someresponse?_=1234&utm_A=123&id=xyz&utm_robot=blue&utm_foo=bar&A=B&utm_id=xyz'
        actual_url = 'http://example.com/someresponse?utm_B=234&id=xyw&utm_bar=foo&utm_foo=bar&_=789&A=B'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_jquery_1(self):
        url = 'http://example.com/someresponse?a=b&foocallback=jQuer123_456&foo=bar&_=1234'
        actual_url = 'http://example.com/someresponse?a=b&foocallback=jQuery789_000&foo=bar&_=123'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_jquery_callback_arg_mismatch(self):
        url = 'http://example.com/someresponse?a=b&foodcallback=jQuery123_456&foo=bar&_=1234'
        actual_url = 'http://example.com/someresponse?a=b&foocallback=jQuery789_000&foo=bar&_=123'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_jquery_other_arg_mismatch(self):
        url = 'http://example.com/someresponse?a=b&foocallback=jQuery123_456&foo=bard&_=1234'
        actual_url = 'http://example.com/someresponse?a=b&foocallback=jQuery789_000&foo=bar&_=123'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_no_fuzzy_bar_baz(self):
        url = 'http://example.com/foo/bar'
        actual_url = 'http://example.com/foo/bas'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_fuzzy_no_deep_path_mime_match(self):
        url = 'http://www.website.co.br/~dinosaurs/t'
        actual_url = 'http://www.website.co.br/~dinosaurs/t/path2/deep-down/what.swf'
        params = self.get_params(url, actual_url, mime='application/x-shockwave-flash')
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []
