#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""

#=================================================================
# HTML Rewriting
#=================================================================

>>> parse('<HTML><A Href="page.html">Text</a></hTmL>')
<HTML><a href="/web/20131226101010/http://example.com/some/path/page.html">Text</a></html>

>>> parse('<body x="y"><img src="../img.gif"/><br/></body>')
<body x="y"><img src="/web/20131226101010im_/http://example.com/some/img.gif"/><br/></body>

>>> parse('<body x="y"><img src="/img.gif"/><br/></body>')
<body x="y"><img src="/web/20131226101010im_/http://example.com/img.gif"/><br/></body>

>>> parse('<input "selected"><img src></div>')
<input "selected"=""><img src=""></div>

>>> parse('<html><head><base href="http://example.com/some/path/index.html"/>')
<html><head><base href="/web/20131226101010/http://example.com/some/path/index.html"/>

# HTML Entities
>>> parse('<a href="">&rsaquo; &nbsp; &#62;</div>')
<a href="">&rsaquo; &nbsp; &#62;</div>

# Don't rewrite anchors
>>> parse('<HTML><A Href="#abc">Text</a></hTmL>')
<HTML><a href="#abc">Text</a></html>

# Unicode
>>> parse('<a href="http://испытание.испытание/">испытание</a>')
<a href="/web/20131226101010/http://испытание.испытание/">испытание</a>

# Meta tag
>>> parse('<META http-equiv="refresh" content="10; URL=/abc/def.html">')
<meta http-equiv="refresh" content="10; URL=/web/20131226101010/http://example.com/abc/def.html">

>>> parse('<meta http-equiv="Content-type" content="text/html; charset=utf-8" />')
<meta http-equiv="Content-type" content="text/html; charset=utf-8"/>

>>> parse('<META http-equiv="refresh" content>')
<meta http-equiv="refresh" content="">

# Script tag
>>> parse('<script>window.location = "http://example.com/a/b/c.html"</script>')
<script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script>

# Unterminated script tag auto-terminate
>>> parse('<script>window.location = "http://example.com/a/b/c.html"</sc>')
<script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</sc></script>

>>> parse('<script>/*<![CDATA[*/window.location = "http://example.com/a/b/c.html;/*]]>*/"</script>')
<script>/*<![CDATA[*/window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html;/*]]>*/"</script>

>>> parse('<div style="background: url(\'abc.html\')" onblah onclick="location = \'redirect.html\'"></div>')
<div style="background: url('/web/20131226101010/http://example.com/some/path/abc.html')" onblah="" onclick="WB_wombat_location = 'redirect.html'"></div>

>>> parse('<style>@import "styles.css" .a { font-face: url(\'myfont.ttf\') }</style>')
<style>@import "/web/20131226101010/http://example.com/some/path/styles.css" .a { font-face: url('/web/20131226101010/http://example.com/some/path/myfont.ttf') }</style>

# Unterminated style tag auto-terminate
>>> parse('<style>@import url(styles.css)')
<style>@import url(/web/20131226101010/http://example.com/some/path/styles.css)</style>

# Head Insertion
>>> parse('<html><head><script src="other.js"></script></head><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script><script src="/web/20131226101010js_/http://example.com/some/path/other.js"></script></head><body>Test</body></html>

>>> parse('<body><div>SomeTest</div>', head_insert = '/* Insert */')
/* Insert */<body><div>SomeTest</div>

>>> parse('<link href="abc.txt"><div>SomeTest</div>', head_insert = '<script>load_stuff();</script>')
<link href="/web/20131226101010oe_/http://example.com/some/path/abc.txt"><script>load_stuff();</script><div>SomeTest</div>

#=================================================================
# Custom Regex
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
{'text_type': 'html', 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
  ('X-Archive-Orig-Content-Length', '5'),
  ('Content-Type', 'text/html;charset=UTF-8')]), 'removed_header_dict': {}, 'charset': 'utf-8'}

# Redirect
>>> _test_headers([('Connection', 'close'), ('Location', '/other.html')], '302 Redirect')
{'text_type': None, 'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect', headers = [ ('X-Archive-Orig-Connection', 'close'),
  ('Location', '/web/20131226101010/http://example.com/other.html')]), 'removed_header_dict': {}, 'charset': None}

# gzip
>>> _test_headers([('Content-Length', '199999'), ('Content-Type', 'text/javascript'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
{'text_type': 'js', 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Content-Length', '199999'),
  ('Content-Type', 'text/javascript')]), 'removed_header_dict': {'transfer-encoding': 'chunked', 'content-encoding': 'gzip'}, 'charset': None}

# Binary
>>> _test_headers([('Content-Length', '200000'), ('Content-Type', 'image/png'), ('Cookie', 'blah'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
{'text_type': None, 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('Content-Length', '200000'),
  ('Content-Type', 'image/png'),
  ('X-Archive-Orig-Cookie', 'blah'),
  ('Content-Encoding', 'gzip')]), 'removed_header_dict': {'transfer-encoding': 'chunked'}, 'charset': None}

Removing Transfer-Encoding always, Was:
  ('Content-Encoding', 'gzip'),
  ('Transfer-Encoding', 'chunked')]), 'charset': None, 'text_type': None, 'removed_header_dict': {}}


"""

#=================================================================
from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.html_rewriter import HTMLRewriter
from pywb.rewrite.regex_rewriters import RegexRewriter, JSRewriter, CSSRewriter, XMLRewriter
from pywb.rewrite.header_rewriter import HeaderRewriter

from pywb.utils.statusandheaders import StatusAndHeaders


urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/web/')

def parse(data, head_insert = None):
    parser = HTMLRewriter(urlrewriter, head_insert = head_insert)
    print parser.rewrite(data) + parser.close()

arcrw = UrlRewriter('20131010im_/http://example.com/', '/web/')


def _test_js(string, extra = []):
    return JSRewriter(arcrw, extra).rewrite(string)

def _test_xml(string):
    return XMLRewriter(arcrw).rewrite(string)

def _test_css(string):
    return CSSRewriter(arcrw).rewrite(string)

headerrewriter = HeaderRewriter()

def _test_headers(headers, status = '200 OK'):
    rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers), urlrewriter)
    return vars(rewritten)


if __name__ == "__main__":
    import doctest
    doctest.testmod()


