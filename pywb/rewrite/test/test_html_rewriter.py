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

# Ensure url is rewritten, but is not unescaped
>>> parse('<a href="http&#x3a;&#x2f;&#x2f;example.com&#x2f;path&#x2f;">')
<a href="/web/20131226101010/http&#x3a;&#x2f;&#x2f;example.com&#x2f;path&#x2f;">

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
>>> parse('<a href="http&#x3a;&#x2f;&#x2f;www&#x2e;example&#x2e;com&#x2f;path&#x2f;file.html">')
<a href="/web/20131226101010/http&#x3a;&#x2f;&#x2f;www&#x2e;example&#x2e;com&#x2f;path&#x2f;file.html">

>>> parse('<a href="&#x2f;&#x2f;www&#x2e;example&#x2e;com&#x2f;path&#x2f;file.html">')
<a href="/web/20131226101010/&#x2f;&#x2f;www&#x2e;example&#x2e;com&#x2f;path&#x2f;file.html">

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

>>> parse('<meta name="referrer" content="origin">')
<meta name="referrer" content="no-referrer-when-downgrade">

>>> parse('<meta http-equiv="Content-Security-Policy" content="default-src http://example.com" />')
<meta http-equiv="Content-Security-Policy" _content="default-src http://example.com"/>

# Don't rewrite Custom -data attribs
>>> parse('<div data-url="http://example.com/a/b/c.html" data-some-other-value="http://example.com/img.gif">')
<div data-url="http://example.com/a/b/c.html" data-some-other-value="http://example.com/img.gif">

# param tag -- rewrite conditionally if url
>>> parse('<param value="http://example.com/"/>')
<param value="/web/20131226101010oe_/http://example.com/"/>

>>> parse('<param value="foo bar"/>')
<param value="foo bar"/>

# srcset attrib: simple
>>> parse('<img srcset="http://example.com">')
<img srcset="/web/20131226101010/http://example.com">

# srcset attrib: single comma-containing
>>> parse('<img srcset="http://example.com/123,foo">')
<img srcset="/web/20131226101010/http://example.com/123,foo">

# srcset attrib: single comma-containing plus descriptor
>>> parse('<img srcset="http://example.com/123,foo 2w">')
<img srcset="/web/20131226101010/http://example.com/123,foo 2w">

# srcset attrib: comma-containing absolute url and relative url, separated by comma and space
>>> parse('<img srcset="http://example.com/123,foo, /bar,bar 2w">')
<img srcset="/web/20131226101010/http://example.com/123,foo, /web/20131226101010/http://example.com/bar,bar 2w">

# srcset attrib: comma-containing relative url and absolute url, separated by comma and space
>>> parse('<img srcset="/bar,bar 2w, http://example.com/123,foo">')
<img srcset="/web/20131226101010/http://example.com/bar,bar 2w, /web/20131226101010/http://example.com/123,foo">

# srcset attrib: absolute urls with descriptors, separated by comma (no space)
>>> parse('<img srcset="http://example.com/123 2w,http://example.com/ 4w">')
<img srcset="/web/20131226101010/http://example.com/123 2w, /web/20131226101010/http://example.com/ 4w">

# srcset attrib: absolute url with descriptor, separated by comma (no space) from absolute url without descriptor
>>> parse('<img srcset="http://example.com/123 2x,http://example.com/">')
<img srcset="/web/20131226101010/http://example.com/123 2x, /web/20131226101010/http://example.com/">

# srcset attrib: absolute url without descriptor, separated by comma (no space) from absolute url with descriptor
>>> parse('<img srcset="http://example.com/123,http://example.com/ 2x">')
<img srcset="/web/20131226101010/http://example.com/123, /web/20131226101010/http://example.com/ 2x">

# complex srcset attrib
>>> parse('<img srcset="//example.com/1x,1x 2w, //example1.com/foo 2x, http://example.com/bar,bar 4x">')
<img srcset="/web/20131226101010///example.com/1x,1x 2w, /web/20131226101010///example1.com/foo 2x, /web/20131226101010/http://example.com/bar,bar 4x">

# complex srcset attrib
>>> parse('<img srcset="http://test.com/yaşar-kunduz.jpg 320w, http://test.com/yaşar-konçalves-273x300.jpg 273w">')
<img srcset="/web/20131226101010/http://test.com/ya%C5%9Far-kunduz.jpg 320w, /web/20131226101010/http://test.com/ya%C5%9Far-konc%CC%A7alves-273x300.jpg 273w">

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

# Script tag with super relative src
>>> parse('<script src="js/fun.js"></script>')
<script __wb_orig_src="js/fun.js" src="/web/20131226101010js_/http://example.com/some/path/js/fun.js"></script>

# Script tag + crossorigin + integrity
>>> parse('<script src="/js/scripts.js" crossorigin="anonymous" integrity="ABC"></script>')
<script src="/web/20131226101010js_/http://example.com/js/scripts.js" _crossorigin="anonymous" _integrity="ABC"></script>

# Unterminated script tag, handle and auto-terminate
>>> parse('<script>window.location = "http://example.com/a/b/c.html"</sc>')
<script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</sc></script>

# SVG Script tag
>>> parse('<script xlink:href="/js/scripts.js"/>')
<script xlink:href="/web/20131226101010js_/http://example.com/js/scripts.js"/>

# SVG Script tag with other elements
>>> parse('<svg><defs><script xlink:href="/js/scripts.js"/><defs/><title>I\'m a title tag in svg!</title></svg>')
<svg><defs><script xlink:href="/web/20131226101010js_/http://example.com/js/scripts.js"/><defs/><title>I'm a title tag in svg!</title></svg>

>>> parse('<script>/*<![CDATA[*/window.location = "http://example.com/a/b/c.html;/*]]>*/"</script>')
<script>/*<![CDATA[*/window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html;/*]]>*/"</script>

>>> parse('<div style="background: url(\'abc.html\')" onblah onclick="location = \'redirect.html\'"></div>')
<div style="background: url('abc.html')" onblah onclick="window.WB_wombat_location = 'redirect.html'"></div>

# on- not rewritten
>>> parse('<div style="background: url(\'abc.html\')" onblah on-click="location = \'redirect.html\'"></div>')
<div style="background: url('abc.html')" onblah on-click="location = 'redirect.html'"></div>

>>> parse('<div style="background: url(\'/other_path/abc.html\')" onblah onclick="window.location = \'redirect.html\'"></div>')
<div style="background: url('/web/20131226101010oe_/http://example.com/other_path/abc.html')" onblah onclick="window.WB_wombat_location = 'redirect.html'"></div>

>>> parse('<i style="background-image: url(http://foo-.bar_.example.com/)"></i>')
<i style="background-image: url(/web/20131226101010oe_/http://foo-.bar_.example.com/)"></i>

>>> parse('<i style=\'background-image: url("http://foo.example.com/")\'></i>')
<i style="background-image: url(&quot;/web/20131226101010oe_/http://foo.example.com/&quot;)"></i>

>>> parse('<i style=\'background-image: url(&quot;http://foo.example.com/&quot;)\'></i>')
<i style="background-image: url(&quot;/web/20131226101010oe_/http://foo.example.com/&quot;)"></i>

>>> parse('<i style=\'background-image: url(&#x27;http://foo.example.com/&#x27;)\'></i>')
<i style="background-image: url('/web/20131226101010oe_/http://foo.example.com/')"></i>

>>> parse("<i style='background-image: url(&apos;http://foo.example.com/&apos;)'></i>")
<i style="background-image: url(&apos;/web/20131226101010oe_/http://foo.example.com/&apos;)"></i>

#>>> parse('<i style=\'background-image: url(&quot;http://исп/&quot;)\'></i>')
<i style="background-image: url(&quot;/web/20131226101010/http://%D0%B8%D1%81%D0%BF/&quot;)"></i>

# Style
>>> parse('<style>@import "/styles.css" .a { font-face: url(\'../myfont.ttf\') }</style>')
<style>@import "/web/20131226101010cs_/http://example.com/styles.css" .a { font-face: url('/web/20131226101010oe_/http://example.com/some/myfont.ttf') }</style>

# Unterminated style tag, handle and auto-terminate
>>> parse('<style>@import url(styles.css)')
<style>@import url(styles.css)</style>

# Head Insertion
>>> parse('<html><head><script src="/other.js"></script></head><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script><script src="/web/20131226101010js_/http://example.com/other.js"></script></head><body>Test</body></html>

>>> parse('<html><script src="other.js"></script></html>', head_insert = '<script src="cool.js"></script>')
<html><script src="cool.js"></script><script __wb_orig_src="other.js" src="/web/20131226101010js_/http://example.com/some/path/other.js"></script></html>

>>> parse('<html><head/><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
<html><head><script src="cool.js"></script></head><body>Test</body></html>

>>> parse('<body><div style="">SomeTest</div>', head_insert = '/* Insert */')
/* Insert */<body><div style="">SomeTest</div>

>>> parse('<link href="/some/path/abc.txt"><div>SomeTest</div>', head_insert = '<script>load_stuff();</script>')
<script>load_stuff();</script><link href="/web/20131226101010oe_/http://example.com/some/path/abc.txt"><div>SomeTest</div>

>>> parse('<!DOCTYPE html>Some Text without any tags <!-- comments -->', head_insert = '<script>load_stuff();</script>')
<!DOCTYPE html>Some Text without any tags <!-- comments --><script>load_stuff();</script>

# UTF-8 BOM
>>> parse('\ufeff<!DOCTYPE html>Some Text without any tags <!-- comments -->', head_insert = '<script>load_stuff();</script>')
\ufeff<!DOCTYPE html>Some Text without any tags <!-- comments --><script>load_stuff();</script>

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

# Preload tests
>>> parse('<link rel="preload" as="script" href="http://example.com/some/other/path">')
<link rel="preload" as="script" href="/web/20131226101010js_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="style" href="http://example.com/some/other/path">')
<link rel="preload" as="style" href="/web/20131226101010cs_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="image" href="http://example.com/some/other/path">')
<link rel="preload" as="image" href="/web/20131226101010im_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="document" href="http://example.com/some/other/path">')
<link rel="preload" as="document" href="/web/20131226101010if_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="video" href="http://example.com/some/other/path">')
<link rel="preload" as="video" href="/web/20131226101010oe_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="worker" href="http://example.com/some/other/path">')
<link rel="preload" as="worker" href="/web/20131226101010js_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="font" href="http://example.com/some/other/path">')
<link rel="preload" as="font" href="/web/20131226101010oe_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="audio" href="http://example.com/some/other/path">')
<link rel="preload" as="audio" href="/web/20131226101010oe_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="embed" href="http://example.com/some/other/path">')
<link rel="preload" as="embed" href="/web/20131226101010oe_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="object" href="http://example.com/some/other/path">')
<link rel="preload" as="object" href="/web/20131226101010oe_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="track" href="http://example.com/some/other/path">')
<link rel="preload" as="track" href="/web/20131226101010oe_/http://example.com/some/other/path">

>>> parse('<link rel="preload" as="fetch" href="http://example.com/some/other/path">')
<link rel="preload" as="fetch" href="/web/20131226101010mp_/http://example.com/some/other/path">

# stylesheet
>>> parse('<link rel="stylesheet" href="http://example.com/some/other/path">')
<link rel="stylesheet" href="/web/20131226101010cs_/http://example.com/some/other/path">

# rel='import'
>>> parse('<link rel="import" href="http://example.com/componemts/app.html">')
<link rel="import" href="/web/20131226101010mp_/http://example.com/componemts/app.html">

>>> parse('<link rel="import" as="document" href="http://example.com/componemts/app.html">')
<link rel="import" as="document" href="/web/20131226101010mp_/http://example.com/componemts/app.html">

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

# parse attr with js proxy, rewrite location assignment
>>> parse('<html><a href="javascript:location=\'foo.html\'"></a></html>', js_proxy=True)
<html><a href="javascript:{ location=((self.__WB_check_loc && self.__WB_check_loc(location, arguments)) || {}).href = 'foo.html' }"></a></html>

# parse attr with js proxy, assigning to location.href, no location assignment rewrite needed
>>> parse('<html><a href="javascript:location.href=\'foo.html\'"></a></html>', js_proxy=True)
<html><a href="javascript:{ location.href='foo.html' }"></a></html>

# parse attr with js proxy, no rewrite needed
>>> parse('<html><a href="javascript:alert()"></a></html>', js_proxy=True)
<html><a href="javascript:alert()"></a></html>

# IE conditional
>>> parse('<!--[if !IE]><html><![endif]--><a href="http://example.com/"><!--[if IE]><![endif]--><a href="http://example.com/"></html>')
<!--[if !IE]><html><![endif]--><a href="/web/20131226101010/http://example.com/"><!--[if IE]><![endif]--><a href="/web/20131226101010/http://example.com/"></html>

# IE conditional with invalid ']-->' ending, rewritten as ']>'
>>> parse('<!--[if !IE]> --><html><![endif]--><a href="http://example.com/"><!--[if IE]><![endif]--><a href="http://example.com/"></html>')
<!--[if !IE]> --><html><![endif]><a href="/web/20131226101010/http://example.com/"><!--[if IE]><![endif]--><a href="/web/20131226101010/http://example.com/"></html>

# Test tag with a target
>>> parse('<HTML><A Href=\"page.html\" target=\"_blank\">Text</a></hTmL>')
<html><a href="page.html" target="___wb_replay_top_frame">Text</a></html>

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
from pywb.rewrite.regex_rewriters import JSWombatProxyRewriter

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

def parse(data, head_insert=None, urlrewriter=urlrewriter, parse_comments=False,
          js_proxy=False):

    if js_proxy:
        js_rewriter_class = JSWombatProxyRewriter
    else:
        js_rewriter_class = None

    parser = HTMLRewriter(urlrewriter, head_insert=head_insert,
                          url=ORIGINAL_URL,
                          js_rewriter_class=js_rewriter_class,
                          parse_comments=parse_comments)

    if js_proxy:
        parser.js_rewriter.first_buff = '{ '
        parser.js_rewriter.last_buff = ' }'

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
