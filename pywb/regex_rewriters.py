import re
import sys
import itertools

from url_rewriter import UrlRewriter

#=================================================================
class RegexRewriter:
    """
    # Test https->http converter (other tests below in subclasses)
    >>> RegexRewriter([(RegexRewriter.HTTPX_MATCH_STR, RegexRewriter.remove_https, 0)]).rewrite('a = https://example.com; b = http://example.com; c = https://some-url/path/https://embedded.example.com')
    'a = http://example.com; b = http://example.com; c = http://some-url/path/http://embedded.example.com'
    """

    @staticmethod
    def comment_out(string):
        return '/*' + string + '*/'

    @staticmethod
    def remove_https(string):
        return string.replace("https", "http")

    @staticmethod
    def add_prefix(prefix):
        return lambda string: prefix + string

    @staticmethod
    def archival_rewrite(rewriter):
        return lambda x: rewriter.rewrite(x)

    @staticmethod
    def replacer(string):
        return lambda x: string

    HTTPX_MATCH_STR = r'https?:\\?/\\?/[A-Za-z0-9:_@.-]+'



    DEFAULT_OP = add_prefix


    def __init__(self, rules):
        #rules = self.create_rules(http_prefix)

        # Build regexstr, concatenating regex list
        regex_str = '|'.join(['(' + rx + ')' for rx, op, count in rules])

        # ensure it's not middle of a word, wrap in non-capture group
        regex_str = '(?<!\w)(?:' + regex_str + ')'

        self.regex = re.compile(regex_str, re.M)
        self.rules = rules

    def filter(self, m):
        return True

    def rewrite(self, string):
        return self.regex.sub(lambda x: self.replace(x), string)

    def close(self):
        return ''

    def replace(self, m):
        i = 0
        for _, op, count in self.rules:
            i += 1

            full_m = i
            while count > 0:
                i += 1
                count -= 1

            if not m.group(i):
                continue

            # Optional filter to skip matches
            if not self.filter(m):
                return m.group(0)

            # Custom func
            if not hasattr(op, '__call__'):
                op = RegexRewriter.DEFAULT_OP(op)

            result = op(m.group(i))

            # if extracting partial match
            if i != full_m:
                result = m.string[m.start(full_m):m.start(i)] + result + m.string[m.end(i):m.end(full_m)]

            return result



#=================================================================
class JSRewriter(RegexRewriter):
    """
    >>> test_js('location = "http://example.com/abc.html"')
    'WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"'

    >>> test_js(r'location = "http:\/\/example.com/abc.html"')
    'WB_wombat_location = "/web/20131010im_/http:\\\\/\\\\/example.com/abc.html"'

    >>> test_js(r'location = "http:\\/\\/example.com/abc.html"')
    'WB_wombat_location = "/web/20131010im_/http:\\\\/\\\\/example.com/abc.html"'

    >>> test_js(r"location = 'http://example.com/abc.html/'")
    "WB_wombat_location = '/web/20131010im_/http://example.com/abc.html/'"

    >>> test_js(r'location = http://example.com/abc.html/')
    'WB_wombat_location = http://example.com/abc.html/'

    >>> test_js(r'location = /http:\/\/example.com/abc.html/')
    'WB_wombat_location = /http:\\\\/\\\\/example.com/abc.html/'

    >>> test_js('"/location" == some_location_val; locations = location;')
    '"/location" == some_location_val; locations = WB_wombat_location;'

    >>> test_js('cool_Location = "http://example.com/abc.html"')
    'cool_Location = "/web/20131010im_/http://example.com/abc.html"'

    >>> test_js('window.location = "http://example.com/abc.html" document.domain = "anotherdomain.com"')
    'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html" document.WB_wombat_domain = "anotherdomain.com"'

    >>> test_js('document_domain = "anotherdomain.com"; window.document.domain = "example.com"')
    'document_domain = "anotherdomain.com"; window.document.WB_wombat_domain = "example.com"'

    # custom rules added
    >>> test_js('window.location = "http://example.com/abc.html"; some_func(); ', [('some_func\(\).*', RegexRewriter.comment_out, 0)])
    'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"; /*some_func(); */'

    # scheme-agnostic
    >>> test_js('cool_Location = "//example.com/abc.html" //comment')
    'cool_Location = "/web/20131010im_///example.com/abc.html" //comment'

    """

    JS_HTTPX = r'(?<="|\')(?:https?:)?\\?/\\?/[A-Za-z0-9:_@.-]+'

    def __init__(self, rewriter, extra = []):
        rules = self._create_rules(rewriter.get_abs_url())
        rules.extend(extra)

        RegexRewriter.__init__(self, rules)


    def _create_rules(self, http_prefix):
        return [
             (self.JS_HTTPX, http_prefix, 0),
             (r'(?<!/)\blocation\b', 'WB_wombat_', 0),
             (r'(?<=document\.)domain', 'WB_wombat_', 0),
        ]


#=================================================================
class XMLRewriter(RegexRewriter):
    """
    >>> test_xml('<tag xmlns="http://www.example.com/ns" attr="http://example.com"></tag>')
    '<tag xmlns="http://www.example.com/ns" attr="/web/20131010im_/http://example.com"></tag>'

    >>> test_xml('<tag xmlns:xsi="http://www.example.com/ns" attr=" http://example.com"></tag>')
    '<tag xmlns:xsi="http://www.example.com/ns" attr=" /web/20131010im_/http://example.com"></tag>'

    >>> test_xml('<tag> http://example.com<other>abchttp://example.com</other></tag>')
    '<tag> /web/20131010im_/http://example.com<other>abchttp://example.com</other></tag>'

    >>> test_xml('<main>   http://www.example.com/blah</tag> <other xmlns:abcdef= " http://example.com"/> http://example.com </main>')
    '<main>   /web/20131010im_/http://www.example.com/blah</tag> <other xmlns:abcdef= " http://example.com"/> /web/20131010im_/http://example.com </main>'

    """

    def __init__(self, rewriter, extra = []):
        rules = self._create_rules(rewriter.get_abs_url())

        RegexRewriter.__init__(self, rules)

    # custom filter to reject 'xmlns' attr
    def filter(self, m):
        attr = m.group(1)
        if attr and attr.startswith('xmlns'):
            return False

        return True

    def _create_rules(self, http_prefix):
        return [
             ('([A-Za-z:]+[\s=]+)?["\'\s]*(' + RegexRewriter.HTTPX_MATCH_STR + ')', http_prefix, 2),
        ]

#=================================================================
class CSSRewriter(RegexRewriter):
    r"""
    >>> test_css("background: url('/some/path.html')")
    "background: url('/web/20131010im_/http://example.com/some/path.html')"

    >>> test_css("background: url('../path.html')")
    "background: url('/web/20131010im_/http://example.com/path.html')"

    >>> test_css("background: url(\"http://domain.com/path.html\")")
    'background: url("/web/20131010im_/http://domain.com/path.html")'

    >>> test_css("background: url(file.jpeg)")
    'background: url(/web/20131010im_/http://example.com/file.jpeg)'

    >>> test_css("background: url('')")
    "background: url('')"

    >>> test_css("background: url (\"weirdpath\')")
    'background: url ("/web/20131010im_/http://example.com/weirdpath\')'

    >>> test_css("@import   url ('path.css')")
    "@import   url ('/web/20131010im_/http://example.com/path.css')"

    >>> test_css("@import url('path.css')")
    "@import url('/web/20131010im_/http://example.com/path.css')"

    >>> test_css("@import ( 'path.css')")
    "@import ( '/web/20131010im_/http://example.com/path.css')"

    >>> test_css("@import  \"path.css\"")
    '@import  "/web/20131010im_/http://example.com/path.css"'

    >>> test_css("@import ('../path.css\"")
    '@import (\'/web/20131010im_/http://example.com/path.css"'

    >>> test_css("@import ('../url.css\"")
    '@import (\'/web/20131010im_/http://example.com/url.css"'

    >>> test_css("@import (\"url.css\")")
    '@import ("/web/20131010im_/http://example.com/url.css")'

    >>> test_css("@import url(/url.css)\n@import  url(/anotherurl.css)\n @import  url(/and_a_third.css)")
    '@import url(/web/20131010im_/http://example.com/url.css)\n@import  url(/web/20131010im_/http://example.com/anotherurl.css)\n @import  url(/web/20131010im_/http://example.com/and_a_third.css)'

    """

    CSS_URL_REGEX = "url\\s*\\(\\s*[\\\\\"']*([^)'\"]+)[\\\\\"']*\\s*\\)"
    CSS_IMPORT_NO_URL_REGEX = "@import\\s+(?!url)\\(?\\s*['\"]?(?!url[\\s\\(])([\w.:/\\\\-]+)"

    def __init__(self, rewriter):
        rules = self._create_rules(rewriter)

        RegexRewriter.__init__(self, rules)


    def _create_rules(self, rewriter):
        return [
             (CSSRewriter.CSS_URL_REGEX, RegexRewriter.archival_rewrite(rewriter), 1),
             (CSSRewriter.CSS_IMPORT_NO_URL_REGEX, RegexRewriter.archival_rewrite(rewriter), 1),
        ]

import utils
if __name__ == "__main__" or utils.enable_doctests():
    arcrw = UrlRewriter('20131010im_/http://example.com/', '/web/')

    def test_js(string, extra = []):
        return JSRewriter(arcrw, extra).rewrite(string)

    def test_xml(string):
        return XMLRewriter(arcrw).rewrite(string)

    def test_css(string):
        return CSSRewriter(arcrw).rewrite(string)


    import doctest
    doctest.testmod()



