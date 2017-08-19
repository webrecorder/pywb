from pywb.warcserver.index.fuzzymatcher import FuzzyMatcher
from pywb.utils.canonicalize import canonicalize


# ============================================================================
class EchoParamsSource(object):
    def __call__(self, params):
        # return nothing for exact match to force fuzzy
        if not params.get('matchType'):
            return iter([]), None

        cdx = {'urlkey': canonicalize(params.get('cdx_url')),
               'mime': params.get('mime'),
               'filter': params.get('filter'),
              }

        return iter([cdx]), None


# ============================================================================
class TestFuzzy(object):
    @classmethod
    def setup_class(cls):
        cls.source = EchoParamsSource()
        cls.fuzzy = FuzzyMatcher('pkg://pywb/rules.yaml')

    def get_params(self, url, actual_url, mime='text/html'):
        params = {'url': url,
                  'cdx_url': actual_url,
                  'key': canonicalize(url),
                  'mime': mime}
        return params

    def get_expected(self, url, mime='text/html', filters=None):
        filters = filters or ['~urlkey:']
        exp = [{'filter': filters,
               'is_fuzzy': True,
               'urlkey': canonicalize(url),
               'mime': mime}]

        return exp

    def test_no_fuzzy(self):
        params = self.get_params('http://example.com/', 'http://example.com/foo')
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_fuzzy_1(self):
        url = 'http://example.com/?_=123'
        actual_url = 'http://example.com/'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_2(self):
        url = 'http://example.com/somefile.html?a=b'
        actual_url = 'http://example.com/somefile.html'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_php_cache(self):
        url = 'http://example.com/somefile.php?_=123'
        actual_url = 'http://example.com/somefile.php'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url)

    def test_fuzzy_swf(self):
        url = 'http://example.com/somefile.php?a=b'
        actual_url = 'http://example.com/somefile.php'
        mime = 'application/x-shockwave-flash'
        params = self.get_params(url, actual_url, mime)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(actual_url, mime)

    def test_fuzzy_custom_rule(self):
        url = 'http://youtube.com/get_video_info?a=b&html5=true&___abc=123&video_id=ABCD&id=1234'
        params = self.get_params(url, url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        filters = ['~urlkey:html5=true', '~urlkey:video_id=abcd']
        assert list(cdx_iter) == self.get_expected(url=url, filters=filters)

    def test_no_fuzzy_ext_restrict(self):
        url = 'http://example.com/somefile.php?a=b'
        actual_url = 'http://example.com/'
        params = self.get_params(url, actual_url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

