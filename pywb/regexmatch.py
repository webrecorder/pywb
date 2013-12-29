import re
import sys
import itertools

from wburlrewriter import ArchivalUrlRewriter

class RegexRewriter:
    """
    # Test https->http converter (other tests below in subclasses)
    >>> RegexRewriter([(RegexRewriter.HTTPX_MATCH_REGEX, RegexRewriter.removeHttps, 0)]).replaceAll('a = https://example.com; b = http://example.com; c = https://some-url/path/https://embedded.example.com')
    'a = http://example.com; b = http://example.com; c = http://some-url/path/http://embedded.example.com'
    """

    @staticmethod
    def commentOut(string):
        return '/*' + string + '*/'

    @staticmethod
    def removeHttps(string):
        return string.replace("https", "http")

    @staticmethod
    def addPrefix(prefix):
        return lambda string: prefix + string

    @staticmethod
    def archivalRewrite(rewriter):
        return lambda x: rewriter.rewrite(x)

    HTTPX_MATCH_REGEX = 'https?:\\\\?/\\\\?/[A-Za-z0-9:_@.-]+'

    DEFAULT_OP = addPrefix


    def __init__(self, rules):
        #rules = self.createRules(httpPrefix)

        # Build regexstr, concatenating regex list
        regexStr = '|'.join(['(' + rx + ')' for rx, op, count in rules])

        # ensure it's not middle of a word, wrap in non-capture group
        regexStr = '(?<!\w)(?:' + regexStr + ')'

        self.regex = re.compile(regexStr, re.M)
        self.rules = rules

    def replaceAll(self, string):
        return self.regex.sub(lambda x: self.replace(x), string)

    def replace(self, m):
        i = 0
        for _, op, count in self.rules:
            i += 1

            fullM = i
            while count > 0:
                i += 1
                count -= 1

            if not m.group(i):
                continue

            # Custom func
            if not hasattr(op, '__call__'):
                op = RegexRewriter.DEFAULT_OP(op)

            result = op(m.group(i))

            # if extracting partial match
            if i != fullM:
                result = m.string[m.start(fullM):m.start(i)] + result + m.string[m.end(i):m.end(fullM)]

            return result



class JSRewriter(RegexRewriter):
    """
    >>> test_js('location = "http://example.com/abc.html"')
    'WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"'

    >>> test_js('cool_Location = "http://example.com/abc.html"')
    'cool_Location = "/web/20131010im_/http://example.com/abc.html"'

    >>> test_js('window.location = "http://example.com/abc.html" document.domain = "anotherdomain.com"')
    'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html" document.WB_wombat_domain = "anotherdomain.com"'

    # custom rules added
    >>> test_js('window.location = "http://example.com/abc.html"; some_func(); ', [('some_func\(\).*', RegexRewriter.commentOut, 0)])
    'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"; /*some_func(); */'

    """

    def __init__(self, rewriter, extra = []):
        rules = self._createRules(rewriter.getAbsUrl())
        rules.extend(extra)

        RegexRewriter.__init__(self, rules)


    def _createRules(self, httpPrefix):
        return [
             (RegexRewriter.HTTPX_MATCH_REGEX, httpPrefix, 0),
             ('location|domain', 'WB_wombat_', 0),
        ]


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

    """

    CSS_URL_REGEX = "url\\s*\\(\\s*[\\\\\"']*([^'\"]+)[\\\\\"']*\\s*\\)"
    CSS_IMPORT_NO_URL_REGEX = "@import\\s+(?!url)\\(?\\s*['\"]?(?!url[\\s\\(])([\w.:/\\\\-]+)"

    def __init__(self, rewriter):
        rules = self._createRules(rewriter)

        RegexRewriter.__init__(self, rules)


    def _createRules(self, rewriter):
        return [
             (CSSRewriter.CSS_URL_REGEX, RegexRewriter.archivalRewrite(rewriter), 1),
             (CSSRewriter.CSS_IMPORT_NO_URL_REGEX, RegexRewriter.archivalRewrite(rewriter), 1),
        ]


if __name__ == "__main__":
    import doctest

    arcrw = ArchivalUrlRewriter('/20131010im_/http://example.com/', '/web/')

    def test_js(string, extra = []):
        return JSRewriter(arcrw, extra).replaceAll(string)

    def test_css(string):
        return CSSRewriter(arcrw).replaceAll(string)



    doctest.testmod()



