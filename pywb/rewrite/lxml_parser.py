#!/usr/bin/env python
# -*- coding: utf-8 -*-

#import lxml.html
import lxml.etree
import cgi
import re

from regex_rewriters import JSRewriter, CSSRewriter
from url_rewriter import UrlRewriter
from html_rewriter import HTMLRewriterMixin


class LXMLHTMLRewriter(HTMLRewriterMixin):
    ur"""
    >>> parse('<HTML><A Href="page.html">Text</a></hTmL>')
    <html><body><a href="/web/20131226101010/http://example.com/some/path/page.html">Text</a></body></html>

    >>> parse('<body x="y"><img src="../img.gif"/><br/></body>')
    <html><body x="y"><img src="/web/20131226101010im_/http://example.com/some/img.gif"></img><br></br></body></html>

    >>> parse('<body x="y"><img src="/img.gif"/><br/></body>')
    <html><body x="y"><img src="/web/20131226101010im_/http://example.com/img.gif"></img><br></br></body></html>

    # malformed html -- "selected" attrib dropped
    >>> parse('<input "selected"><img src></div>')
    <html><body><input></input><img src=""></img></body></html>

    >>> parse('<html><head><base href="http://example.com/some/path/index.html"/>')
    <html><head><base href="/web/20131226101010/http://example.com/some/path/index.html"></base></head></html>

    # Don't rewrite anchors
    >>> parse('<HTML><A Href="#abc">Text</a></hTmL>')
    <html><body><a href="#abc">Text</a></body></html>

    # Ensure attr values are not unescaped
    >>> parse('<p data-value="&quot;X&quot;">data</p>')
    <html><body><p data-value="&quot;X&quot;">data</p></body></html>

    # text moved out of input
    >>> parse('<input value="val">data</input>')
    <html><body><input value="val"></input>data</body></html>

    >>> parse('<script src="abc.js"></script>')
    <html><head><script src="/web/20131226101010js_/http://example.com/some/path/abc.js"></script></head></html>

    # Unicode
    >>> parse('<a href="http://испытание.испытание/">испытание</a>')
    <html><body><a href="/web/20131226101010/http://испытание.испытание/">испытание</a></body></html>

    # Meta tag
    >>> parse('<META http-equiv="refresh" content="10; URL=/abc/def.html">')
    <html><head><meta content="10; URL=/web/20131226101010/http://example.com/abc/def.html" http-equiv="refresh"></meta></head></html>

    >>> parse('<meta http-equiv="Content-type" content="text/html; charset=utf-8" />')
    <html><head><meta content="text/html; charset=utf-8" http-equiv="Content-type"></meta></head></html>

    >>> parse('<META http-equiv="refresh" content>')
    <html><head><meta content="" http-equiv="refresh"></meta></head></html>

    # Script tag
    >>> parse('<script>window.location = "http://example.com/a/b/c.html"</script>')
    <html><head><script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</script></head></html>

    # Unterminated script tag, will auto-terminate
    >>> parse('<script>window.location = "http://example.com/a/b/c.html"</sc>')
    <html><head><script>window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html"</sc></script></head></html>

    >>> parse('<script>/*<![CDATA[*/window.location = "http://example.com/a/b/c.html;/*]]>*/"</script>')
    <html><head><script>/*<![CDATA[*/window.WB_wombat_location = "/web/20131226101010/http://example.com/a/b/c.html;/*]]>*/"</script></head></html>

    >>> parse('<div style="background: url(\'abc.html\')" onblah onclick="location = \'redirect.html\'"></div>')
    <html><body><div style="background: url('/web/20131226101010/http://example.com/some/path/abc.html')" onblah="" onclick="WB_wombat_location = 'redirect.html'"></div></body></html>

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
    <html><head><script>load_stuff();</script><link href="/web/20131226101010oe_/http://example.com/some/path/abc.txt"></link></head><body><div>SomeTest</div></body></html>


    # content after </html>
    >>> parse('<body>abc</body></html><input type="hidden" value="def"/>')
    <html><body>abc</body><input type="hidden" value="def"></input></html>

    # doctype
    >>> parse('<!doctype html><div>abcdef</div>')
    <html><body><div>abcdef</div></body></html>

    # no attr value
    >>> parse('<checkbox selected></checkbox')
    <html><body><checkbox selected=""></checkbox></body></html>
    """

    END_HTML = re.compile(r'</\s*html\s*>', re.IGNORECASE)

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
                                            recover=True,
                                            )

        self.is_closing = False


    def feed(self, string):
        string = self.END_HTML.sub(u'', string)
        #string = string.replace(u'</html>', u'')
        self.parser.feed(string)

    def close(self):
        if not self.out:
            self.out = self.AccumBuff()

        self.is_closing = True
        self.parser.close()

        result = self.out.getvalue()
        # Clear buffer to create new one for next rewrite()
        self.out = None

        return result


class RewriterTarget(object):
    def __init__(self, rewriter):
        self.rewriter = rewriter

    def start(self, tag, attrs):
        attrs = attrs.items()

        if not self.rewriter._rewrite_tag_attrs(tag, attrs, escape=True):
            self.rewriter.out.write(u'<' + tag)

            for name, value in attrs:
                self.rewriter._write_attr(name, value, escape=True)
        else:
            if tag == u'head':
                if (self.rewriter._rewrite_head(False)):
                    return

        self.rewriter.out.write(u'>')


    def end(self, tag):
        #if tag == 'html' and not self.rewriter.is_closing:
        #    raise lxml.etree.LxmlError('test')

        if (tag == self.rewriter._wb_parse_context):
            self.rewriter._wb_parse_context = None

        self.rewriter.out.write(u'</' + tag + u'>')

    def data(self, data):
        if not self.rewriter._wb_parse_context:
            data = cgi.escape(data, quote=True)

        self.rewriter.parse_data(data)

    def comment(self, data):
        self.rewriter.out.write(u'<!--')
        self.rewriter.parse_data(data)
        self.rewriter.out.write(u'-->')

    def pi(self, data):
        self.rewriter.out.write(u'<?' + data + u'>')

    def close(self):
        return ''

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/web/')

def parse(data, head_insert=None):
    parser = LXMLHTMLRewriter(urlrewriter, head_insert=head_insert)
    data = data.decode('utf-8')
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
        b = x.read(81920)
        while b:
            result = parser.rewrite(b.decode('utf-8'))
            print result.encode('utf-8')
            b = x.read(81920)
        print parser.close()
