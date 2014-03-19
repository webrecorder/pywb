#!/usr/bin/env python
# -*- coding: utf-8 -*-

ur"""

#=================================================================
# HTML Rewriting (using native HTMLParser)
#=================================================================

>>> parse('<HTML><A Href="page.html">Text</a></hTmL>')
<HTML><a href="/web/20131226101010/http://example.com/some/path/page.html">Text</a></html>

>>> parse('<body x="y"><img src="../img.gif"/><br/></body>')
<body x="y"><img src="/web/20131226101010im_/http://example.com/some/img.gif"/><br/></body>

>>> parse('<body x="y"><img src="/img.gif"/><br/></body>')
<body x="y"><img src="/web/20131226101010im_/http://example.com/img.gif"/><br/></body>

# malformed html -- (2.6 parser raises exception)
#>>> parse('<input "selected"><img src></div>')
#<input "selected"=""><img src=""></div>

>>> parse('<html><head><base href="http://example.com/some/path/index.html"/>')
<html><head><base href="/web/20131226101010/http://example.com/some/path/index.html"/>

# HTML Entities
>>> parse('<a href="">&rsaquo; &nbsp; &#62;</div>')
<a href="">&rsaquo; &nbsp; &#62;</div>

# Don't rewrite anchors
>>> parse('<HTML><A Href="#abc">Text</a></hTmL>')
<HTML><a href="#abc">Text</a></html>

# Ensure attr values are not unescaped
>>> parse('<input value="&quot;X&quot;">X</input>')
<input value="&quot;X&quot;">X</input>

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
<script>window.WB_wombat_location = "/web/20131226101010em_/http://example.com/a/b/c.html"</script>

# Unterminated script tag, handle and auto-terminate
>>> parse('<script>window.location = "http://example.com/a/b/c.html"</sc>')
<script>window.WB_wombat_location = "/web/20131226101010em_/http://example.com/a/b/c.html"</sc></script>

>>> parse('<script>/*<![CDATA[*/window.location = "http://example.com/a/b/c.html;/*]]>*/"</script>')
<script>/*<![CDATA[*/window.WB_wombat_location = "/web/20131226101010em_/http://example.com/a/b/c.html;/*]]>*/"</script>

>>> parse('<div style="background: url(\'abc.html\')" onblah onclick="location = \'redirect.html\'"></div>')
<div style="background: url('/web/20131226101010em_/http://example.com/some/path/abc.html')" onblah="" onclick="WB_wombat_location = 'redirect.html'"></div>

>>> parse('<style>@import "styles.css" .a { font-face: url(\'myfont.ttf\') }</style>')
<style>@import "/web/20131226101010em_/http://example.com/some/path/styles.css" .a { font-face: url('/web/20131226101010em_/http://example.com/some/path/myfont.ttf') }</style>

# Unterminated style tag, handle and auto-terminate
>>> parse('<style>@import url(styles.css)')
<style>@import url(/web/20131226101010em_/http://example.com/some/path/styles.css)</style>

# Head Insertion
>>> parse('<html><head><script src="other.js"></script></head><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script><script src="/web/20131226101010js_/http://example.com/some/path/other.js"></script></head><body>Test</body></html>

>>> parse('<html><head/><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script></head><body>Test</body></html>

>>> parse('<body><div>SomeTest</div>', head_insert = '/* Insert */')
/* Insert */<body><div>SomeTest</div>

>>> parse('<link href="abc.txt"><div>SomeTest</div>', head_insert = '<script>load_stuff();</script>')
<link href="/web/20131226101010oe_/http://example.com/some/path/abc.txt"><script>load_stuff();</script><div>SomeTest</div>
"""

from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.html_rewriter import HTMLRewriter

import pprint

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/web/')

def parse(data, head_insert = None):
    parser = HTMLRewriter(urlrewriter, head_insert = head_insert)
    data = data.decode('utf-8')
    print parser.rewrite(data) + parser.close()

if __name__ == "__main__":
    import doctest
    doctest.testmod()
