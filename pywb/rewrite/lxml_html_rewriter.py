try:
    import lxml.etree
    LXML_SUPPORTED = True
except ImportError:
    LXML_SUPPORTED = False
    pass

import cgi
import re

from regex_rewriters import JSRewriter, CSSRewriter
from url_rewriter import UrlRewriter
from html_rewriter import HTMLRewriterMixin


#=================================================================
class LXMLHTMLRewriter(HTMLRewriterMixin):
    END_HTML = re.compile(r'</\s*html\s*>', re.IGNORECASE)

    def __init__(self, *args, **kwargs):
        super(LXMLHTMLRewriter, self).__init__(*args, **kwargs)

        self.target = RewriterTarget(self)
        self.parser = lxml.etree.HTMLParser(remove_pis=False,
                                            remove_blank_text=False,
                                            remove_comments=False,
                                            strip_cdata=False,
                                            compact=True,
                                            target=self.target,
                                            recover=True,
                                            )

        self.started = False

    def feed(self, string):
        self.started = True
        string = self.END_HTML.sub(u'', string)
        #string = string.replace(u'</html>', u'')
        self.parser.feed(string)

    def parse(self, stream):
        self.out = self.AccumBuff()

        lxml.etree.parse(stream, self.parser)

        result = self.out.getvalue()

        # Clear buffer to create new one for next rewrite()
        self.out = None

        return result

    def _internal_close(self):
        if self.started:
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
            if isinstance(data, unicode):
                data = data.replace(u'\xa0', '&nbsp;')
        self.rewriter.parse_data(data)

    def comment(self, data):
        self.rewriter.out.write(u'<!--')
        self.rewriter.parse_data(data)
        self.rewriter.out.write(u'-->')

    def doctype(self, root_tag, public_id, system_id):
        self.rewriter.out.write(u'<!doctype')
        if root_tag:
            self.rewriter.out.write(' ' + root_tag)
        if public_id:
            self.rewriter.out.write(' PUBLIC ' + public_id)
        if system_id:
            self.rewriter.out.write(' SYSTEM ' + system_id)
        self.rewriter.out.write(u'>')

    def pi(self, target, data):
        self.rewriter.out.write(u'<?' + target + ' ' + data + u'>')

    def close(self):
        return ''
