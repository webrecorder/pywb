from pywb.warcserver.index.fuzzymatcher import FuzzyMatcher
from pywb.utils.canonicalize import canonicalize

class EchoParamsSource(object):
    def __call__(self, params):
        # return nothing for exact match to force fuzzy
        if not params.get('matchType'):
            return iter([]), None

        obj = {'key': params.get('key'),
               'mime': params.get('mime'),
               'filter': params.get('filter')
              }
        return iter([obj]), None






class TestFuzzy(object):
    @classmethod
    def setup_class(cls):
        cls.source = EchoParamsSource()
        cls.fuzzy = FuzzyMatcher('pkg://pywb/rules.yaml')

    def get_params(self, url, mime='text/html'):
        params = {'url': url,
                  'key': canonicalize(url),
                  'mime': mime}
        return params

    def get_expected(self, url, mime='text/html', filters=None):
        filters = filters or ['~urlkey:']
        exp = [{'filter': filters,
               'is_fuzzy': True,
               'key': canonicalize(url),
               'mime': mime}]

        return exp

    def test_no_fuzzy(self):
        params = self.get_params('http://example.com/')
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []

    def test_fuzzy_1(self):
        url = 'http://example.com/?_=123'
        params = self.get_params(url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(url)

    def test_fuzzy_2(self):
        url = 'http://example.com/somefile.html?a=b'
        params = self.get_params(url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(url)

    def test_fuzzy_php_cache(self):
        url = 'http://example.com/somefile.php?_=123'
        params = self.get_params(url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(url)

    def test_fuzzy_swf(self):
        url = 'http://example.com/somefile.php?a=b'
        mime = 'application/x-shockwave-flash'
        params = self.get_params(url, mime)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == self.get_expected(url, mime)

    def test_fuzzy_custom_rule(self):
        url = 'http://youtube.com/get_video_info?a=b&html5=true&___abc=123&video_id=ABCD&id=1234'
        params = self.get_params(url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        filters = ['~urlkey:html5=true', '~urlkey:video_id=abcd']
        assert list(cdx_iter) == self.get_expected(url=url, filters=filters)

    def test_no_fuzzy_ext_restrict(self):
        url = 'http://example.com/somefile.php?a=b'
        params = self.get_params(url)
        cdx_iter, errs = self.fuzzy(self.source, params)
        assert list(cdx_iter) == []







