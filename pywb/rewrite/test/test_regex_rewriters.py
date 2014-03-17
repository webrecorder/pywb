r"""
#=================================================================
# Custom Regex
#=================================================================
# Test https->http converter (other tests below in subclasses)
>>> RegexRewriter([(RegexRewriter.HTTPX_MATCH_STR, RegexRewriter.remove_https, 0)]).rewrite('a = https://example.com; b = http://example.com; c = https://some-url/path/https://embedded.example.com')
'a = http://example.com; b = http://example.com; c = http://some-url/path/http://embedded.example.com'


#=================================================================
# JS Rewriting
#=================================================================

>>> _test_js('location = "http://example.com/abc.html"')
'WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"'

>>> _test_js(r'location = "http:\/\/example.com/abc.html"')
'WB_wombat_location = "/web/20131010im_/http:\\/\\/example.com/abc.html"'

>>> _test_js(r'location = "http:\\/\\/example.com/abc.html"')
'WB_wombat_location = "/web/20131010im_/http:\\\\/\\\\/example.com/abc.html"'

>>> _test_js(r"location = 'http://example.com/abc.html/'")
"WB_wombat_location = '/web/20131010im_/http://example.com/abc.html/'"

>>> _test_js(r'location = http://example.com/abc.html/')
'WB_wombat_location = http://example.com/abc.html/'

# not rewritten -- to be handled on client side
>>> _test_js(r'location = "/abc.html"')
'WB_wombat_location = "/abc.html"'

>>> _test_js(r'location = /http:\/\/example.com/abc.html/')
'WB_wombat_location = /http:\\/\\/example.com/abc.html/'

>>> _test_js('"/location" == some_location_val; locations = location;')
'"/location" == some_location_val; locations = WB_wombat_location;'

>>> _test_js('cool_Location = "http://example.com/abc.html"')
'cool_Location = "/web/20131010im_/http://example.com/abc.html"'

>>> _test_js('window.location = "http://example.com/abc.html" document.domain = "anotherdomain.com"')
'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html" document.WB_wombat_domain = "anotherdomain.com"'

>>> _test_js('document_domain = "anotherdomain.com"; window.document.domain = "example.com"')
'document_domain = "anotherdomain.com"; window.document.WB_wombat_domain = "example.com"'

# custom rules added
>>> _test_js('window.location = "http://example.com/abc.html"; some_func(); ', [('some_func\(\).*', RegexRewriter.format('/*{0}*/'), 0)])
'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"; /*some_func(); */'

# scheme-agnostic
>>> _test_js('cool_Location = "//example.com/abc.html" //comment')
'cool_Location = "/web/20131010im_///example.com/abc.html" //comment'


#=================================================================
# XML Rewriting
#=================================================================

>>> _test_xml('<tag xmlns="http://www.example.com/ns" attr="http://example.com"></tag>')
'<tag xmlns="http://www.example.com/ns" attr="/web/20131010im_/http://example.com"></tag>'

>>> _test_xml('<tag xmlns:xsi="http://www.example.com/ns" attr=" http://example.com"></tag>')
'<tag xmlns:xsi="http://www.example.com/ns" attr=" /web/20131010im_/http://example.com"></tag>'

>>> _test_xml('<tag> http://example.com<other>abchttp://example.com</other></tag>')
'<tag> /web/20131010im_/http://example.com<other>abchttp://example.com</other></tag>'

>>> _test_xml('<main>   http://www.example.com/blah</tag> <other xmlns:abcdef= " http://example.com"/> http://example.com </main>')
'<main>   /web/20131010im_/http://www.example.com/blah</tag> <other xmlns:abcdef= " http://example.com"/> /web/20131010im_/http://example.com </main>'

#=================================================================
# CSS Rewriting
#=================================================================

>>> _test_css("background: url('/some/path.html')")
"background: url('/web/20131010im_/http://example.com/some/path.html')"

>>> _test_css("background: url('../path.html')")
"background: url('/web/20131010im_/http://example.com/path.html')"

>>> _test_css("background: url(\"http://domain.com/path.html\")")
'background: url("/web/20131010im_/http://domain.com/path.html")'

>>> _test_css("background: url(file.jpeg)")
'background: url(/web/20131010im_/http://example.com/file.jpeg)'

>>> _test_css("background: url('')")
"background: url('')"

>>> _test_css("background: url (\"weirdpath\')")
'background: url ("/web/20131010im_/http://example.com/weirdpath\')'

>>> _test_css("@import   url ('path.css')")
"@import   url ('/web/20131010im_/http://example.com/path.css')"

>>> _test_css("@import url('path.css')")
"@import url('/web/20131010im_/http://example.com/path.css')"

>>> _test_css("@import ( 'path.css')")
"@import ( '/web/20131010im_/http://example.com/path.css')"

>>> _test_css("@import  \"path.css\"")
'@import  "/web/20131010im_/http://example.com/path.css"'

>>> _test_css("@import ('../path.css\"")
'@import (\'/web/20131010im_/http://example.com/path.css"'

>>> _test_css("@import ('../url.css\"")
'@import (\'/web/20131010im_/http://example.com/url.css"'

>>> _test_css("@import (\"url.css\")")
'@import ("/web/20131010im_/http://example.com/url.css")'

>>> _test_css("@import url(/url.css)\n@import  url(/anotherurl.css)\n @import  url(/and_a_third.css)")
'@import url(/web/20131010im_/http://example.com/url.css)\n@import  url(/web/20131010im_/http://example.com/anotherurl.css)\n @import  url(/web/20131010im_/http://example.com/and_a_third.css)'

#=================================================================
HTTP Headers Rewriting
#=================================================================

# Text with charset
>>> _test_headers([('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'), ('Content-Length', '5'), ('Content-Type', 'text/html;charset=UTF-8')])
{'charset': 'utf-8',
 'removed_header_dict': {},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
  ('X-Archive-Orig-Content-Length', '5'),
  ('Content-Type', 'text/html;charset=UTF-8')]),
 'text_type': 'html'}

# Redirect
>>> _test_headers([('Connection', 'close'), ('Location', '/other.html')], '302 Redirect')
{'charset': None,
 'removed_header_dict': {},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect', headers = [ ('X-Archive-Orig-Connection', 'close'),
  ('Location', '/web/20131010im_/http://example.com/other.html')]),
 'text_type': None}

# gzip
>>> _test_headers([('Content-Length', '199999'), ('Content-Type', 'text/javascript'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
{'charset': None,
 'removed_header_dict': {'content-encoding': 'gzip',
                         'transfer-encoding': 'chunked'},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Content-Length', '199999'),
  ('Content-Type', 'text/javascript')]),
 'text_type': 'js'}

# Binary
>>> _test_headers([('Content-Length', '200000'), ('Content-Type', 'image/png'), ('Cookie', 'blah'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
{'charset': None,
 'removed_header_dict': {'transfer-encoding': 'chunked'},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('Content-Length', '200000'),
  ('Content-Type', 'image/png'),
  ('X-Archive-Orig-Cookie', 'blah'),
  ('Content-Encoding', 'gzip')]),
 'text_type': None}

Removing Transfer-Encoding always, Was:
  ('Content-Encoding', 'gzip'),
  ('Transfer-Encoding', 'chunked')]), 'charset': None, 'text_type': None, 'removed_header_dict': {}}


"""

#=================================================================
from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.regex_rewriters import RegexRewriter, JSRewriter, CSSRewriter, XMLRewriter
from pywb.rewrite.header_rewriter import HeaderRewriter

from pywb.utils.statusandheaders import StatusAndHeaders

import pprint

urlrewriter = UrlRewriter('20131010im_/http://example.com/', '/web/')


def _test_js(string, extra = []):
    return JSRewriter(urlrewriter, extra).rewrite(string)

def _test_xml(string):
    return XMLRewriter(urlrewriter).rewrite(string)

def _test_css(string):
    return CSSRewriter(urlrewriter).rewrite(string)

headerrewriter = HeaderRewriter()

def _test_headers(headers, status = '200 OK'):
    rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers), urlrewriter)
    return pprint.pprint(vars(rewritten))


if __name__ == "__main__":
    import doctest
    doctest.testmod()


