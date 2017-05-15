#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""

#=================================================================
# HTML Rewriting (using native HTMLParser)
#=================================================================

>>> parse('<HTML><A Href="page.html">Text</a></hTmL>')
<html><a href="page.html">Text</a></html>

>>> parse('<body x="y"><img src="../img.gif"/><br/></body>')
<body x="y"><img src="/web/20131226101010im_/http://example.com/some/img.gif"/><br/></body>

>>> parse('<body x="y"><img src="/img.gif"/><br/></body>')
<body x="y"><img src="/web/20131226101010im_/http://example.com/img.gif"/><br/></body>

>>> parse('<table background="/img.gif">')
<table background="/web/20131226101010im_/http://example.com/img.gif">

# malformed html -- (2.6 parser raises exception)
#>>> parse('<input "selected"><img src></div>')
#<input "selected"=""><img src=""></div>

# Base Tests -- w/ rewrite (default)
>>> parse('<html><head><base href="http://example.com/diff/path/file.html"/>')
<html><head><base href="/web/20131226101010/http://example.com/diff/path/file.html"/>

# Full Path
>>> parse('<html><head><base href="http://example.com/diff/path/file.html"/>', urlrewriter=full_path_urlrewriter)
<html><head><base href="http://localhost:80/web/20131226101010/http://example.com/diff/path/file.html"/>

# Full Path Scheme Rel Base
>>> parse('<base href="//example.com"/><img src="/foo.gif"/>', urlrewriter=full_path_urlrewriter)
<base href="//localhost:80/web/20131226101010///example.com/"/><img src="/web/20131226101010im_/http://example.com/foo.gif"/>

# Rel Base
>>> parse('<html><head><base href="/other/file.html"/>', urlrewriter=full_path_urlrewriter)
<html><head><base href="/web/20131226101010/http://example.com/other/file.html"/>

# Rel Base + example
>>> parse('<html><head><base href="/other/file.html"/><a href="/path.html">', urlrewriter=full_path_urlrewriter)
<html><head><base href="/web/20131226101010/http://example.com/other/file.html"/><a href="/web/20131226101010/http://example.com/path.html">

# Rel Base
>>> parse('<base href="./static/"/><img src="image.gif"/>', urlrewriter=full_path_urlrewriter)
<base href="./static/"/><img src="image.gif"/>

# Rel Base
>>> parse('<base href="./static/"/><a href="/static/"/>', urlrewriter=full_path_urlrewriter)
<base href="./static/"/><a href="/web/20131226101010/http://example.com/static/"/>

# ensure trailing slash added
>>> parse('<base href="http://example.com"/>')
<base href="/web/20131226101010/http://example.com/"/>

# Base Tests -- no rewrite
>>> parse('<html><head><base href="http://example.com/diff/path/file.html"/>', urlrewriter=no_base_canon_rewriter)
<html><head><base href="http://example.com/diff/path/file.html"/>

>>> parse('<base href="static/"/><img src="image.gif"/>', urlrewriter=no_base_canon_rewriter)
<base href="static/"/><img src="image.gif"/>

# Empty url
>>> parse('<base href="">')
<base href="">

>>> parse('<base href>')
<base href>

# href on other tags
>>> parse('<HTML><div Href="page.html">Text</div></hTmL>')
<html><div href="page.html">Text</div></html>

# HTML Entities
>>> parse('<a href="">&rsaquo; &nbsp; &#62; &#63</div>')
<a href="">&rsaquo; &nbsp; &#62; &#63</div>

>>> parse('<div>X&Y</div> </div>X&Y;</div>')
<div>X&Y</div> </div>X&Y;</div>

# Don't rewrite anchors
>>> parse('<HTML><A Href="#abc">Text</a></hTmL>')
<html><a href="#abc">Text</a></html>

# Ensure attr values are not unescaped
>>> parse('<input value="&amp;X&amp;&quot;">X</input>')
<input value="&amp;X&amp;&quot;">X</input>

# Empty values should be ignored
>>> parse('<input name="foo" value>')
<input name="foo" value>

# SKIPPED
# Unicode -- default with %-encoding
#>>> parse(u'<a href="http://испытание.испытание/">испытание</a>')
#<a href="/web/20131226101010/http://испытание.испытание/">испытание</a>

#<a href="/web/20131226101010/http://%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/">испытание</a>

#>>> parse(u'<a href="http://испытание.испытание/">испытание</a>', urlrewriter=urlrewriter_pencode)
#<a href="/web/20131226101010/http://испытание.испытание/">испытание</a>

# entity unescaping
#>>> parse('<a href="http&#x3a;&#x2f;&#x2f;www&#x2e;example&#x2e;com&#x2f;path&#x2f;file.html">')
<a href="/web/20131226101010/http://www.example.com/path/file.html">


# Meta tag
>>> parse('<META http-equiv="refresh" content="10; URL=/abc/def.html">')
<meta http-equiv="refresh" content="10; URL=/web/20131226101010/http://example.com/abc/def.html">

>>> parse('<meta http-equiv="Content-type" content="text/html; charset=utf-8" />')
<meta http-equiv="Content-type" content="text/html; charset=utf-8"/>

>>> parse('<meta http-equiv="refresh" content="text/html; charset=utf-8" />')
<meta http-equiv="refresh" content="text/html; charset=utf-8"/>

>>> parse('<META http-equiv="refresh" content>')
<meta http-equiv="refresh" content>

>>> parse('<meta property="og:image" content="http://example.com/example.jpg">')
<meta property="og:image" content="/web/20131226101010/http://example.com/example.jpg">

>>> parse('<meta property="og:image" content="example.jpg">')
<meta property="og:image" content="example.jpg">

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
<img srcset="/web/20131226101010///example.com/1x 1x,/web/20131226101010///example.com/foo 2x,/web/20131226101010/https://example.com/bar 4x">

# empty srcset attrib
>>> parse('<img srcset="">')
<img srcset="">

# Script tag
>>> parse('<script>window.location = "http://example.com/a/b/c.html"</script>')
<script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script>

# Script tag with JS-type 1
>>> parse('<script type="application/javascript">window.location = "http://example.com/a/b/c.html"</script>')
<script type="application/javascript">window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script>

# Script tag with JS-type 2
>>> parse('<script type="text/ecmascript">window.location = "http://example.com/a/b/c.html"</script>')
<script type="text/ecmascript">window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script>

# Script tag with JS-type 3
>>> parse('<script type="JavaScript">window.location = "http://example.com/a/b/c.html"</script>')
<script type="JavaScript">window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script>

# Script tag with JS-type 4
>>> parse('<script type="text/javascript">{"embed top test": "http://example.com/a/b/c.html"}</script>')
<script type="text/javascript">{"embed WB_wombat_top test": "/web/20131226101010/http://example.com/a/b/c.html"}</script>

# Script tag with NON-JS type
>>> parse('<script type="application/json">{"embed top test": "http://example.com/a/b/c.html"}</script>')
<script type="application/json">{"embed top test": "http://example.com/a/b/c.html"}</script>

# Script tag + crossorigin + integrity
>>> parse('<script src="/js/scripts.js" crossorigin="anonymous" integrity="ABC"></script>')
<script src="/web/20131226101010js_/http://example.com/js/scripts.js" _crossorigin="anonymous" _integrity="ABC"></script>

# Unterminated script tag, handle and auto-terminate
>>> parse('<script>window.location = "http://example.com/a/b/c.html"</sc>')
<script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</sc></script>

>>> parse('<script>/*<![CDATA[*/window.location = "http://example.com/a/b/c.html;/*]]>*/"</script>')
<script>/*<![CDATA[*/window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html;/*]]>*/"</script>

>>> parse('<div style="background: url(\'abc.html\')" onblah onclick="location = \'redirect.html\'"></div>')
<div style="background: url('abc.html')" onblah onclick="window.WB_wombat_location = 'redirect.html'"></div>

>>> parse('<div style="background: url(\'/other_path/abc.html\')" onblah onclick="window.location = \'redirect.html\'"></div>')
<div style="background: url('/web/20131226101010/http://example.com/other_path/abc.html')" onblah onclick="window.WB_wombat_location = 'redirect.html'"></div>

>>> parse('<i style="background-image: url(http://foo-.bar_.example.com/)"></i>')
<i style="background-image: url(/web/20131226101010/http://foo-.bar_.example.com/)"></i>

>>> parse('<i style=\'background-image: url("http://foo.example.com/")\'></i>')
<i style="background-image: url(&quot;/web/20131226101010/http://foo.example.com/&quot;)"></i>

>>> parse('<i style=\'background-image: url(&quot;http://foo.example.com/&quot;)\'></i>')
<i style="background-image: url(&quot;/web/20131226101010/http://foo.example.com/&quot;)"></i>

>>> parse("<i style='background-image: url(&apos;http://foo.example.com/&apos;)'></i>")
<i style="background-image: url(&apos;/web/20131226101010/http://foo.example.com/&apos;)"></i>

#>>> parse('<i style=\'background-image: url(&quot;http://исп/&quot;)\'></i>')
<i style="background-image: url(&quot;/web/20131226101010/http://%D0%B8%D1%81%D0%BF/&quot;)"></i>

# Style
>>> parse('<style>@import "/styles.css" .a { font-face: url(\'../myfont.ttf\') }</style>')
<style>@import "/web/20131226101010/http://example.com/styles.css" .a { font-face: url('/web/20131226101010/http://example.com/some/myfont.ttf') }</style>

# Unterminated style tag, handle and auto-terminate
>>> parse('<style>@import url(styles.css)')
<style>@import url(styles.css)</style>

# Head Insertion
>>> parse('<html><head><script src="/other.js"></script></head><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script><script src="/web/20131226101010js_/http://example.com/other.js"></script></head><body>Test</body></html>

>>> parse('<html><script src="other.js"></script></html>', head_insert = '<script src="cool.js"></script>')
<html><script src="cool.js"></script><script src="other.js"></script></html>

>>> parse('<html><head/><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script></head><body>Test</body></html>

>>> parse('<body><div style="">SomeTest</div>', head_insert = '/* Insert */')
/* Insert */<body><div style="">SomeTest</div>

>>> parse('<link href="/some/path/abc.txt"><div>SomeTest</div>', head_insert = '<script>load_stuff();</script>')
<script>load_stuff();</script><link href="/web/20131226101010oe_/http://example.com/some/path/abc.txt"><div>SomeTest</div>

>>> parse('<!DOCTYPE html>Some Text without any tags <!-- comments -->', head_insert = '<script>load_stuff();</script>')
<!DOCTYPE html>Some Text without any tags <!-- comments --><script>load_stuff();</script>

# no parse comments
>>> parse('<html><!-- <a href="/foo.html"> --></html>')
<html><!-- <a href="/foo.html"> --></html>

# with parse comments
>>> parse('<html><!-- <a href="/foo.html"> --></html>', parse_comments=True)
<html><!-- <a href="/web/20131226101010/http://example.com/foo.html"> --></html>

# rel=canonical: rewrite (default)
>>> parse('<link rel=canonical href="http://example.com/">')
<link rel="canonical" href="/web/20131226101010oe_/http://example.com/">

# rel=canonical: no_rewrite
>>> parse('<link rel=canonical href="http://example.com/canon/path">', urlrewriter=no_base_canon_rewriter)
<link rel="canonical" href="http://example.com/canon/path">

# rel=canonical: no_rewrite
>>> parse('<link rel=canonical href="/relative/path">', urlrewriter=no_base_canon_rewriter)
<link rel="canonical" href="http://example.com/relative/path">

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

# remove extra spaces
>>> parse('<HTML><A Href="  page.html  ">Text</a></hTmL>')
<html><a href="page.html">Text</a></html>

>>> parse('<HTML><A Href="  ">Text</a></hTmL>')
<html><a href="">Text</a></html>

>>> parse('<HTML><A Href="">Text</a></hTmL>')
<html><a href="">Text</a></html>




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
import six

ORIGINAL_URL = 'http://example.com/some/path/index.html'

def new_rewriter(prefix='/web/', rewrite_opts=dict()):
    PROXY_PATH = '20131226101010/{0}'.format(ORIGINAL_URL)
    return UrlRewriter(PROXY_PATH, prefix, rewrite_opts=rewrite_opts)

urlrewriter = new_rewriter(rewrite_opts=dict(punycode_links=False))

full_path_urlrewriter = new_rewriter(prefix='http://localhost:80/web/',
                                     rewrite_opts=dict(punycode_links=False))

urlrewriter_pencode = new_rewriter(rewrite_opts=dict(punycode_links=True))

no_base_canon_rewriter = new_rewriter(rewrite_opts=dict(rewrite_rel_canon=False,
                                                        rewrite_base=False))

def parse(data, head_insert=None, urlrewriter=urlrewriter, parse_comments=False):
    parser = HTMLRewriter(urlrewriter, head_insert=head_insert,
                          url=ORIGINAL_URL,
                          parse_comments=parse_comments)

    if six.PY2 and isinstance(data, six.text_type):
        data = data.encode('utf-8')

    result = parser.rewrite(data) + parser.close()

    if six.PY2:
        # decode only for printing
        result = result.decode('utf-8')

    print(result)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
