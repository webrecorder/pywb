#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re

from HTMLParser import HTMLParser
from url_rewriter import ArchivalUrlRewriter
from regex_rewriters import JSRewriter, CSSRewriter

#=================================================================
# WBHtml --html parser for custom rewriting, also handlers for script and css
#=================================================================
class WBHtml(HTMLParser):
    r"""
    >>> parse('<HTML><A Href="page.html">Text</a></hTmL>')
    <HTML><a href="/web/20131226101010/http://example.com/some/path/page.html">Text</a></html>

    >>> parse('<body x="y"><img src="../img.gif"/><br/></body>')
    <body x="y"><img src="/web/20131226101010im_/http://example.com/some/img.gif"/><br/></body>

    >>> parse('<body x="y"><img src="/img.gif"/><br/></body>')
    <body x="y"><img src="/web/20131226101010im_/http://example.com/img.gif"/><br/></body>

    >>> parse('<input "selected"><img src></div>')
    <input "selected"><img src></div>

    >>> parse('<html><head><base href="http://example.com/some/path/index.html"/>')
    <html><head><base href="/web/20131226101010/http://example.com/some/path/index.html"/>

    >>> parse('<a href="">&rsaquo; &nbsp; &#62;</div>')
    <a href>&rsaquo; &nbsp; &#62;</div>

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
    <meta http-equiv="refresh" content>

    # Script tag
    >>> parse('<script>window.location = "http://example.com/a/b/c.html"</script>')
    <script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script>

    # Unterminated script tag auto-terminate
    >>> parse('<script>window.location = "http://example.com/a/b/c.html"</sc>')
    <script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</sc></script>

    >>> parse('<script>/*<![CDATA[*/window.location = "http://example.com/a/b/c.html;/*]]>*/"</script>')
    <script>/*<![CDATA[*/window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html;/*]]>*/"</script>

    >>> parse('<div style="background: url(\'abc.html\')" onblah onclick="location = \'redirect.html\'"></div>')
    <div style="background: url('/web/20131226101010/http://example.com/some/path/abc.html')" onblah onclick="WB_wombat_location = 'redirect.html'"></div>

    >>> parse('<style>@import "styles.css" .a { font-face: url(\'myfont.ttf\') }</style>')
    <style>@import "/web/20131226101010/http://example.com/some/path/styles.css" .a { font-face: url('/web/20131226101010/http://example.com/some/path/myfont.ttf') }</style>

    # Unterminated style tag auto-terminate
    >>> parse('<style>@import url(styles.css)')
    <style>@import url(/web/20131226101010/http://example.com/some/path/styles.css)</style>

    # Head Insertion
    >>> parse('<html><head><script src="other.js"></script></head><body>Test</body></html>', headInsert = '<script src="cool.js"></script>')
    <html><head><script src="cool.js"></script><script src="/web/20131226101010js_/http://example.com/some/path/other.js"></script></head><body>Test</body></html>

    >>> parse('<body><div>SomeTest</div>', headInsert = '/* Insert */')
    /* Insert */<body><div>SomeTest</div>

    >>> parse('<link href="abc.txt"><div>SomeTest</div>', headInsert = '<script>load_stuff();</script>')
    <link href="/web/20131226101010oe_/http://example.com/some/path/abc.txt"><script>load_stuff();</script><div>SomeTest</div>

    """

    REWRITE_TAGS = {
        'a':       {'href': ''},
        'applet':  {'codebase': 'oe_',
                    'archive': 'oe_'},
        'area':    {'href': ''},
        'base':    {'href': ''},
        'blockquote': {'cite': ''},
        'body':    {'background': 'im_'},
        'del':     {'cite': ''},
        'embed':   {'src': 'oe_'},
        'head':    {'': ''}, # for head rewriting
        'iframe':  {'src': 'if_'},
        'img':     {'src': 'im_'},
        'ins':     {'cite': ''},
        'input':   {'src': 'im_'},
        'form':    {'action': ''},
        'frame':   {'src': 'fr_'},
        'link':    {'href': 'oe_'},
        'meta':    {'content': ''},
        'object':  {'codebase': 'oe_',
                    'data': 'oe_'},
        'q':       {'cite': ''},
        'ref':     {'href': 'oe_'},
        'script':  {'src': 'js_'},
        'div':     {'data-src' : '',
                    'data-uri' : ''},
        'li':      {'data-src' : '',
                    'data-uri' : ''},
    }

    STATE_TAGS = ['script', 'style']

    HEAD_TAGS = ['html', 'head', 'base', 'link', 'meta', 'title', 'style', 'script', 'object', 'bgsound']

    class AccumBuff:
        def __init__(self):
            self.buff = ''

        def write(self, string):
            self.buff += string


    def __init__(self, url_rewriter, outstream = None, headInsert = None, jsRewriterClass = JSRewriter, cssRewriterClass = CSSRewriter):
        HTMLParser.__init__(self)

        self.url_rewriter = url_rewriter
        self._wbParseContext = None
        self.out = outstream if outstream else WBHtml.AccumBuff()

        self.jsRewriter = jsRewriterClass(url_rewriter)
        self.cssRewriter = cssRewriterClass(url_rewriter)

        self.headInsert = headInsert


    # ===========================
    META_REFRESH_REGEX = re.compile('^[\\d.]+\\s*;\\s*url\\s*=\\s*(.+?)\\s*$', re.IGNORECASE | re.MULTILINE)

    def _rewriteMetaRefresh(self, metaRefresh):
        if not metaRefresh:
            return None

        m = WBHtml.META_REFRESH_REGEX.match(metaRefresh)
        if not m:
            return metaRefresh

        try:
            metaRefresh = metaRefresh[:m.start(1)] + self._rewriteURL(m.group(1)) + metaRefresh[m.end(1):]
        except Exception:
            pass

        return metaRefresh
    # ===========================

    def _rewriteURL(self, value, mod = None):
        return self.url_rewriter.rewrite(value, mod) if value else None


    def _rewriteCSS(self, cssContent):
        return self.cssRewriter.rewrite(cssContent) if cssContent else None

    def _rewriteScript(self, scriptContent):
        return self.jsRewriter.rewrite(scriptContent) if scriptContent else None

    def hasAttr(self, tagAttrs, attr):
        name, value = attr
        for attrName, attrValue in tagAttrs:
            if attrName == name:
                return value.lower() == attrValue.lower()
        return False

    def rewriteTagAttrs(self, tag, tagAttrs, isStartEnd):
        # special case: script or style parse context
        if (tag in WBHtml.STATE_TAGS) and (self._wbParseContext == None):
            self._wbParseContext = tag

        # special case: head insertion, non-head tags
        elif (self.headInsert and (self._wbParseContext == None) and (tag not in WBHtml.HEAD_TAGS)):
            self.out.write(self.headInsert)
            self.headInsert = None

        # attr rewriting
        handler = WBHtml.REWRITE_TAGS.get(tag)
        if not handler:
            handler = WBHtml.REWRITE_TAGS.get('')

        if not handler:
            return False

        self.out.write('<' + tag)

        for attr in tagAttrs:
            attrName, attrValue = attr

            # special case: inline JS/event handler
            if (attrValue and attrValue.startswith('javascript:')) or attrName.startswith('on'):
                attrValue = self._rewriteScript(attrValue)

            # special case: inline CSS/style attribute
            elif attrName == 'style':
                attrValue = self._rewriteCSS(attrValue)

            # special case: meta tag
            elif (tag == 'meta') and (attrName == 'content'):
                if self.hasAttr(tagAttrs, ('http-equiv', 'refresh')):
                    attrValue = self._rewriteMetaRefresh(attrValue)

            else:
                # special case: base tag
                if (tag == 'base') and (attrName == 'href') and attrValue:
                    self.url_rewriter.setBaseUrl(attrValue)

                rwMod = handler.get(attrName)
                if rwMod is not None:
                    attrValue = self._rewriteURL(attrValue, rwMod)

            if attrValue is not None:
                #self.out.write(' {0}="{1}"'.format(attrName, attrValue))
                self.out.write(' ' + attrName + '="' + attrValue + '"')
            else:
                self.out.write(' ' + attrName)

        self.out.write('/>' if isStartEnd else '>')

        # special case: head tag
        if (self.headInsert) and (self._wbParseContext == None) and (tag == 'head'):
            self.out.write(self.headInsert)
            self.headInsert = None

        return True


    def parseData(self, data):
        if self._wbParseContext == 'script':
            data = self._rewriteScript(data)
        elif self._wbParseContext == 'style':
            data = self._rewriteCSS(data)

        self.out.write(data)

    def rewrite(self, string):
        if not self.out:
            self.out = WBHtml.AccumBuff()

        self.feed(string)

        result = self.out.buff
        # Clear buffer to create new one for next rewrite()
        self.out = None

        return result

    # HTMLParser overrides below
    def close(self):
        if (self._wbParseContext):
            result = self.rewrite('</' + self._wbParseContext + '>')
            self._wbParseContext = None
        else:
            result = ''

        HTMLParser.close(self)
        return result

    def handle_starttag(self, tag, attrs):
        if not self.rewriteTagAttrs(tag, attrs, False):
            self.out.write(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if not self.rewriteTagAttrs(tag, attrs, True):
            self.out.write(self.get_starttag_text())

    def handle_endtag(self, tag):
        if (tag == self._wbParseContext):
            self._wbParseContext = None

        self.out.write('</' + tag + '>')

    def handle_data(self, data):
        self.parseData(data)

    def handle_entityref(self, data):
        self.out.write('&' + data + ';')

    def handle_charref(self, data):
        self.out.write('&#' + data + ';')

    def handle_comment(self, data):
        self.out.write('<!--')
        self.parseData(data)
        self.out.write('-->')

    def handle_decl(self, data):
        self.out.write('<!' + data + '>')

    def handle_pi(self, data):
        self.out.write('<?' + data + '>')

    def unknown_decl(self, data):
        self.out.write('<![')
        self.parseData(data)
        self.out.write(']>')


# instantiate the parser and fed it some HTML
#parser = WBHtml()
#instr = '<HTML X=\'a\' B=\'234\' some="other"><a href="Test"><BR/><head><title>Test</title></head>\n<body><h1>Parse me!</h1></body></HTML>'
#print instr
#print
#parser.feed(instr)
#print
import utils
if __name__ == "__main__" or utils.enable_doctests():

    url_rewriter = ArchivalUrlRewriter('/20131226101010/http://example.com/some/path/index.html', '/web/')

    def parse(data, headInsert = None):
        parser = WBHtml(url_rewriter, headInsert = headInsert)
        print parser.rewrite(data) + parser.close()

    import doctest
    doctest.testmod()


