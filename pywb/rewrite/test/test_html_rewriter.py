#!/usr/bin/env python
# -*- coding: utf-8 -*-

ur"""

#=================================================================
# HTML Rewriting (using native HTMLParser)
#=================================================================

>>> parse('<HTML><A Href="page.html">Text</a></hTmL>')
<html><a href="/web/20131226101010/http://example.com/some/path/page.html">Text</a></html>

>>> parse('<body x="y"><img src="../img.gif"/><br/></body>')
<body x="y"><img src="/web/20131226101010im_/http://example.com/some/img.gif"/><br/></body>

>>> parse('<body x="y"><img src="/img.gif"/><br/></body>')
<body x="y"><img src="/web/20131226101010im_/http://example.com/img.gif"/><br/></body>

# malformed html -- (2.6 parser raises exception)
#>>> parse('<input "selected"><img src></div>')
#<input "selected"=""><img src=""></div>

# Base Tests -- w/ rewrite (default)
>>> parse('<html><head><base href="http://example.com/diff/path/file.html"/>')
<html><head><base href="/web/20131226101010/http://example.com/diff/path/file.html"/>

>>> parse('<base href="static/"/><img src="image.gif"/>')
<base href="/web/20131226101010/http://example.com/some/path/static/"/><img src="/web/20131226101010im_/http://example.com/some/path/static/image.gif"/>

# Base Tests -- no rewrite
>>> parse('<html><head><base href="http://example.com/diff/path/file.html"/>', urlrewriter=no_base_canon_rewriter)
<html><head><base href="http://example.com/diff/path/file.html"/>

>>> parse('<base href="static/"/><img src="image.gif"/>', urlrewriter=no_base_canon_rewriter)
<base href="static/"/><img src="/web/20131226101010im_/http://example.com/some/path/static/image.gif"/>



# HTML Entities
>>> parse('<a href="">&rsaquo; &nbsp; &#62; &#63</div>')
<a href="">&rsaquo; &nbsp; &#62; &#63</div>

>>> parse('<div>X&Y</div> </div>X&Y;</div>')
<div>X&Y</div> </div>X&Y;</div>

# Don't rewrite anchors
>>> parse('<HTML><A Href="#abc">Text</a></hTmL>')
<html><a href="#abc">Text</a></html>

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

>>> parse('<meta http-equiv="refresh" content="text/html; charset=utf-8" />')
<meta http-equiv="refresh" content="text/html; charset=utf-8"/>

>>> parse('<META http-equiv="refresh" content>')
<meta http-equiv="refresh" content="">

# Custom -data attribs
>>> parse('<div data-url="http://example.com/a/b/c.html" data-some-other-value="http://example.com/img.gif">')
<div data-url="/web/20131226101010oe_/http://example.com/a/b/c.html" data-some-other-value="/web/20131226101010oe_/http://example.com/img.gif">

# param tag -- rewrite conditionally if url
>>> parse('<param value="http://example.com/"/>')
<param value="/web/20131226101010oe_/http://example.com/"/>

>>> parse('<param value="foo bar"/>')
<param value="foo bar"/>

# srcset attrib
>>> parse('<img srcset="//example.com/1x 1x, //example.com/foo 2x, https://example.com/bar 4x">')
<img srcset="/web/20131226101010/http://example.com/1x 1x, /web/20131226101010/http://example.com/foo 2x, /web/20131226101010/https://example.com/bar 4x">

# Script tag
>>> parse('<script>window.location = "http://example.com/a/b/c.html"</script>')
<script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script>

# Script tag + crossorigin
>>> parse('<script src="/js/scripts.js" crossorigin="anonymous"></script>')
<script src="/web/20131226101010js_/http://example.com/js/scripts.js" _crossorigin="anonymous"></script>

# Unterminated script tag, handle and auto-terminate
>>> parse('<script>window.location = "http://example.com/a/b/c.html"</sc>')
<script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</sc></script>

>>> parse('<script>/*<![CDATA[*/window.location = "http://example.com/a/b/c.html;/*]]>*/"</script>')
<script>/*<![CDATA[*/window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html;/*]]>*/"</script>

>>> parse('<div style="background: url(\'abc.html\')" onblah onclick="location = \'redirect.html\'"></div>')
<div style="background: url('/web/20131226101010/http://example.com/some/path/abc.html')" onblah="" onclick="WB_wombat_location = 'redirect.html'"></div>

>>> parse('<i style="background-image: url(http://foo-.bar_.example.com/)"></i>')
<i style="background-image: url(/web/20131226101010/http://foo-.bar_.example.com/)"></i>

# Style
>>> parse('<style>@import "styles.css" .a { font-face: url(\'myfont.ttf\') }</style>')
<style>@import "/web/20131226101010/http://example.com/some/path/styles.css" .a { font-face: url('/web/20131226101010/http://example.com/some/path/myfont.ttf') }</style>

# Unterminated style tag, handle and auto-terminate
>>> parse('<style>@import url(styles.css)')
<style>@import url(/web/20131226101010/http://example.com/some/path/styles.css)</style>

# Head Insertion
>>> parse('<html><head><script src="other.js"></script></head><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script><script src="/web/20131226101010js_/http://example.com/some/path/other.js"></script></head><body>Test</body></html>

>>> parse('<html><head/><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script></head><body>Test</body></html>

>>> parse('<body><div style="">SomeTest</div>', head_insert = '/* Insert */')
/* Insert */<body><div style="">SomeTest</div>

>>> parse('<link href="abc.txt"><div>SomeTest</div>', head_insert = '<script>load_stuff();</script>')
<link href="/web/20131226101010oe_/http://example.com/some/path/abc.txt"><script>load_stuff();</script><div>SomeTest</div>

# rel=canonical: rewrite (default)
>>> parse('<link rel=canonical href="http://example.com/">')
<link rel="canonical" href="/web/20131226101010oe_/http://example.com/">

# rel=canonical: no_rewrite
>>> parse('<link rel=canonical href="http://example.com/">', urlrewriter=no_base_canon_rewriter)
<link rel="canonical" href="http://example.com/">

# doctype
>>> parse('<!doctype html PUBLIC "public">')
<!doctype html PUBLIC "public">

# uncommon markup
>>> parse('<?test content?>')
<?test content?>

# no special cdata treatment, preserved in <script>
>>> parse('<script><![CDATA[ <a href="path.html"></a> ]]></script>')
<script><![CDATA[ <a href="path.html"></a> ]]></script>

# CDATA outside of <script> parsed and *not* rewritten
>>> parse('<?test content><![CDATA[ <a href="http://example.com"></a> ]]>')
<?test content><![CDATA[ <a href="http://example.com"></a> ]>

>>> parse('<!-- <a href="http://example.com"></a> -->')
<!-- <a href="http://example.com"></a> -->

# Test blank
>>> parse('')
<BLANKLINE>

# Test no parsing at all
>>> p = HTMLRewriter(urlrewriter)
>>> p.close()
''

"""

from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.html_rewriter import HTMLRewriter

import pprint

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/web/')

no_base_canon_rewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html',
                                     '/web/',
                                     rewrite_opts=dict(rewrite_rel_canon=False,
                                                       rewrite_base=False))

def parse(data, head_insert=None, urlrewriter=urlrewriter):
    parser = HTMLRewriter(urlrewriter, head_insert = head_insert)
    #data = data.decode('utf-8')
    result = parser.rewrite(data) + parser.close()
    # decode only for printing
    print result.decode('utf-8')

if __name__ == "__main__":
    import doctest
    doctest.testmod()
