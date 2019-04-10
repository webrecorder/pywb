from pywb.rewrite.jsonp_rewriter import JSONPRewriter
from pywb.rewrite.url_rewriter import UrlRewriter

class TestJSONPRewriter(object):
    @classmethod
    def setup_class(cls):
        urlrewriter = UrlRewriter('20161226/http://example.com/?callback=jQuery_ABC', '/web/', 'https://localhost/web/')
        cls.rewriter = JSONPRewriter(urlrewriter)

        urlrewriter = UrlRewriter('20161226/http://example.com/', '/web/', 'https://localhost/web/')
        cls.rewriter_missing_cb = JSONPRewriter(urlrewriter)

    def test_jsonp_rewrite_1(self):
        string = 'jQuery_1234({"foo": "bar", "some": "data"})'
        expect = 'jQuery_ABC({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == expect

    def test_jsonp_rewrite_1_with_whitespace(self):
        string = '    jQuery_1234({"foo": "bar", "some": "data"})'
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

    def test_jsonp_rewrite_4(self):
        string = """// some comment
 jQuery_1234({"foo": "bar", "some": "data"})"""
        expect = 'jQuery_ABC({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == expect

    def test_jsonp_rewrite_5(self):
        string = """// some comment
 // blah = 4;
 jQuery_1234({"foo": "bar", "some": "data"})"""
        expect = 'jQuery_ABC({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == expect

# JSONP valid but 'callback=' missing in url tests
    def test_no_jsonp_rewrite_missing_callback_1(self):
        """ JSONP valid but callback is missing in url
        """
        string = 'jQuery_1234({"foo": "bar", "some": "data"})'
        assert self.rewriter_missing_cb.rewrite(string) == string

    def test_no_jsonp_rewrite_missing_callback_2(self):
        string = """// some comment
 jQuery_1234({"foo": "bar", "some": "data"})"""
        expect = 'jQuery_ABC({"foo": "bar", "some": "data"})'
        assert self.rewriter_missing_cb.rewrite(string) == string


# Invalid JSONP Tests
    def test_no_jsonp_rewrite_1(self):
        string = ' /* comment jQuery_1234({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == string

    def test_no_jsonp_rewrite_2(self):
        string = 'function jQuery_1234({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == string

    def test_no_jsonp_rewrite_3(self):
        string = 'var foo = ({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == string

    def test_jsonp_rewrite_3(self):
        string = ' abc /* some comment */ jQuery_1234({"foo": "bar", "some": "data"})'
        assert self.rewriter.rewrite(string) == string

    def test_no_jsonp_multiline_rewrite_2(self):
        string = """// some comment
 blah = 4;
 jQuery_1234({"foo": "bar", "some": "data"})"""
        assert self.rewriter.rewrite(string) == string


