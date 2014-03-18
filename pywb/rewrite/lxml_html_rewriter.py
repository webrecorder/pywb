import lxml.etree
import cgi
import re

from regex_rewriters import JSRewriter, CSSRewriter
from url_rewriter import UrlRewriter
from html_rewriter import HTMLRewriterMixin


#=================================================================
class LXMLHTMLRewriter(HTMLRewriterMixin):
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

    def feed(self, string):
        string = self.END_HTML.sub(u'', string)
        #string = string.replace(u'</html>', u'')
        self.parser.feed(string)

    def _internal_close(self):
        self.parser.close()


#=================================================================
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
