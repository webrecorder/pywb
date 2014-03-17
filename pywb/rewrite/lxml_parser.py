#!/usr/bin/env python
# -*- coding: utf-8 -*-

import lxml.html
import lxml.etree
import cgi

from regex_rewriters import JSRewriter, CSSRewriter
from url_rewriter import UrlRewriter
from html_rewriter import HTMLRewriterMixin
from StringIO import StringIO


class LXMLHTMLRewriter(HTMLRewriterMixin):
    r"""
    >>> parse('<HTML><A Href="page.html">Text</a></hTmL>')
    <html><body><a href="/web/20131226101010/http://example.com/some/path/page.html">Text</a></body></html>

    >>> parse('<body x="y"><img src="../img.gif"/><br/></body>')
    <html><body x="y"><img src="/web/20131226101010im_/http://example.com/some/img.gif"/><br/></body></html>

    >>> parse('<body x="y"><img src="/img.gif"/><br/></body>')
    <html><body x="y"><img src="/web/20131226101010im_/http://example.com/img.gif"/><br/></body></html>

    # malformed html -- "selected" attrib dropped
    >>> parse('<input "selected"><img src></div>')
    <html><body><input/><img src=""/></body></html>

    >>> parse('<html><head><base href="http://example.com/some/path/index.html"/>')
    <html><head><base href="/web/20131226101010/http://example.com/some/path/index.html"/></head></html>

    # Don't rewrite anchors
    >>> parse('<HTML><A Href="#abc">Text</a></hTmL>')
    <html><body><a href="#abc">Text</a></body></html>

    # Ensure attr values are not unescaped
    >>> parse('<p data-value="&quot;X&quot;">data</p>')
    <html><body><p data-value="&quot;X&quot;">data</p></body></html>

    # text moved out of input
    >>> parse('<input value="val">data</input>')
    <html><body><input value="val"/>data</body></html>

    >>> parse('<script src="abc.js"></script>')
    <html><head><script src="/web/20131226101010js_/http://example.com/some/path/abc.js"></script></head></html>

    # Unicode
    >>> parse('<a href="http://испытание.испытание/">испытание</a>')
    <html><body><a href="/web/20131226101010/http://испытание.испытание/">испытание</a></body></html>

    # Meta tag
    >>> parse('<META http-equiv="refresh" content="10; URL=/abc/def.html">')
    <html><head><meta content="10; URL=/web/20131226101010/http://example.com/abc/def.html" http-equiv="refresh"/></head></html>

    >>> parse('<meta http-equiv="Content-type" content="text/html; charset=utf-8" />')
    <html><head><meta content="text/html; charset=utf-8" http-equiv="Content-type"/></head></html>

    >>> parse('<META http-equiv="refresh" content>')
    <html><head><meta content="" http-equiv="refresh"/></head></html>

    # Script tag
    >>> parse('<script>window.location = "http://example.com/a/b/c.html"</script>')
    <html><head><script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script></head></html>

    # Unterminated script tag, will auto-terminate
    >>> parse('<script>window.location = "http://example.com/a/b/c.html"</sc>')
    <html><head><script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</sc></script></head></html>

    >>> parse('<script>/*<![CDATA[*/window.location = "http://example.com/a/b/c.html;/*]]>*/"</script>')
    <html><head><script>/*<![CDATA[*/window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html;/*]]>*/"</script></head></html>

    >>> parse('<div style="background: url(\'abc.html\')" onblah onclick="location = \'redirect.html\'"></div>')
    <html><body><div style="background: url('/web/20131226101010/http://example.com/some/path/abc.html')" onblah="" onclick="WB_wombat_location = 'redirect.html'"/></body></html>

    >>> parse('<style>@import "styles.css" .a { font-face: url(\'myfont.ttf\') }</style>')
    <html><head><style>@import "/web/20131226101010/http://example.com/some/path/styles.css" .a { font-face: url('/web/20131226101010/http://example.com/some/path/myfont.ttf') }</style></head></html>

    # Unterminated style tag, handle but don't auto-terminate
    >>> parse('<style>@import url(styles.css)')
    <html><head><style>@import url(/web/20131226101010/http://example.com/some/path/styles.css)</style></head></html>

    # Head Insertion
    >>> parse('<html><head><script src="other.js"></script></head><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
    <html><head><script src="cool.js"></script><script src="/web/20131226101010js_/http://example.com/some/path/other.js"></script></head><body>Test</body></html>

    >>> parse('<html><head/><body>Test</body></html>', head_insert = '<script src="cool.js"></script>')
    <html><head><script src="cool.js"></script></head><body>Test</body></html>

    >>> parse('<body><div>SomeTest</div>', head_insert = '/* Insert */')
    <html>/* Insert */<body><div>SomeTest</div></body></html>

    >>> parse('<link href="abc.txt"><div>SomeTest</div>', head_insert = '<script>load_stuff();</script>')
    <html><head><script>load_stuff();</script><link href="/web/20131226101010oe_/http://example.com/some/path/abc.txt"/></head><body><div>SomeTest</div></body></html>


    """

    def __init__(self, url_rewriter,
                 head_insert=None,
                 js_rewriter_class=JSRewriter,
                 css_rewriter_class=CSSRewriter):

        super(LXMLHTMLRewriter, self).__init__(url_rewriter,
                                               head_insert,
                                               js_rewriter_class,
                                               css_rewriter_class)


        self.target = RewriterTarget(self)
        self.parser = lxml.etree.HTMLParser(remove_pis=False,
                                            remove_blank_text=False,
                                            remove_comments=False,
                                            strip_cdata=False,
                                            compact=True,
                                            target=self.target,
                                            #encoding='utf-8'
                                            )


    def feed(self, string):
        self.parser.feed(string)

    def close(self):
        if not self.out:
            self.out = self.AccumBuff()

        self.parser.close()

        result = self.out.getvalue()
        # Clear buffer to create new one for next rewrite()
        self.out = None

        return result


class RewriterTarget(object):
    def __init__(self, rewriter):
        self.rewriter = rewriter
        self.curr_tag = None

    def _close_tag(self):
        if self.curr_tag:
            self.rewriter.out.write('>')
            self.curr_tag = None

    def start(self, tag, attrs):
        self._close_tag()
        attrs = attrs.items()

        self.curr_tag = tag

        if self.rewriter._rewrite_tag_attrs(tag, attrs, escape=True):
            if tag == 'head' and self.rewriter._rewrite_head(False):
                self.curr_tag = None
            return

        self.rewriter.out.write('<' + tag)

        for name, value in attrs:
            self.rewriter._write_attr(name, value, escape=True)


    def end(self, tag):
        if (tag == self.rewriter._wb_parse_context):
            self.rewriter._wb_parse_context = None

        if (self.curr_tag == tag) and (tag != 'script'):
            self.rewriter.out.write('/>')
            self.curr_tag = None
        else:
            self._close_tag()
            self.rewriter.out.write('</' + tag + '>')

    def data(self, data):
        self._close_tag()

        if not self.rewriter._wb_parse_context:
            data = cgi.escape(data, quote=True)

        self.rewriter.parse_data(data)

    def comment(self, text):
        self._close_tag()

        self.rewriter.out.write('<!--')
        self.rewriter.parse_data(text)
        self.rewriter.out.write('-->')

    def close(self):
        self._close_tag()
        return ''

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/web/')

def parse(data, head_insert=None):
    parser = LXMLHTMLRewriter(urlrewriter, head_insert=head_insert)
    print parser.rewrite(data) + parser.close()
    #return parser.rewrite(data) + parser.close()


if __name__ == "__main__":

    import sys
    if len(sys.argv) == 1:
        import doctest
        doctest.testmod()
    else:
        parser = LXMLHTMLRewriter(urlrewriter)
        x = open(sys.argv[1])
        b = x.read()
        while b:
            print parser.rewrite(b)
            b = x.read()
        print parser.close()
