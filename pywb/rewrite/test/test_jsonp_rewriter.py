from pywb.rewrite.jsonp_rewriter import JSONPRewriter
from pywb.rewrite.url_rewriter import UrlRewriter

class TestJSONPRewriter(object):
    @classmethod
    def setup_class(cls):
        urlrewriter = UrlRewriter('20161226/http://example.com/?callback=jQuery_ABC', '/web/', 'https://localhost/web/')
        cls.rewriter = JSONPRewriter(urlrewriter)

        urlrewriter = UrlRewriter('20161226/http://example.com/', '/web/', 'https://localhost/web/')
        cls.rewriter_no_cb = JSONPRewriter(urlrewriter)

    def test_jsonp_rewrite_1(self):
        string = 'jQuery_1234({"foo": "bar", "some": "data"})'
        expect = 'jQuery_ABC({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == expect

    def test_jsonp_rewrite_2(self):
        string = ' /**/ jQuery_1234({"foo": "bar", "some": "data"})'
        expect = 'jQuery_ABC({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == expect

    def test_jsonp_rewrite_3(self):
        string = ' /* some comment */ jQuery_1234({"foo": "bar", "some": "data"})'
        expect = 'jQuery_ABC({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == expect

    def test_no_jsonp_rewrite_1(self):
        string = ' /* comment jQuery_1234({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == string

    def test_no_jsonp_rewrite_2(self):
        string = 'function jQuery_1234({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == string

    def test_no_jsonp_rewrite_3(self):
        string = 'var foo = ({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == string

    def test_no_jsonp_rewrite_no_callback_1(self):
        string = 'jQuery_1234({"foo": "bar", "some": "data"})'
        assert self.rewriter_no_cb.rewrite(string) == string


