import sys

from HTMLParser import HTMLParser
from wburlrewriter import ArchivalUrlRewriter

tag_list = {
    'a': {'href': ''},
    'img': {'src': 'im_'}
}

# create a subclass and override the handler methods
class WBHtml(HTMLParser):
    """
    >>> WBHtml(rewriter).feed('<HTML><A Href="page.html">Text</a></hTmL>')
    <HTML><a href="/web/20131226101010/http://example.com/some/path/page.html">Text</a></html>

    >>> WBHtml(rewriter).feed('<img src="../img.gif"/><br/>')
    <img src="/web/20131226101010im_/http://example.com/some/img.gif"/><br/>

    """

    def __init__(self, rewriter, outstream = None):
        HTMLParser.__init__(self)

        self.rewriter = rewriter
        self.out = outstream if outstream else sys.stdout

    def _rewriteAttr(self, mod, value):
        return self.rewriter.rewrite(value, mod)

    def rewriteTagAttrs(self, tag, tagAttrs, isStartEnd):
        rwAttrs = tag_list.get(tag)
        if not rwAttrs:
            rwAttrs = tag_list.get('')

        if not rwAttrs:
            return False

        self.out.write('<' + tag)
        for attr in tagAttrs:
            name, value = attr
            rwMod = rwAttrs.get(name)

            if rwMod is not None:
                value = self._rewriteAttr(rwMod, value)

            self.out.write(' {0}="{1}"'.format(name, value))

        self.out.write('/>' if isStartEnd else '>')
        return True

    def handle_starttag(self, tag, attrs):

        if not self.rewriteTagAttrs(tag, attrs, False):
            self.out.write(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):

        if not self.rewriteTagAttrs(tag, attrs, True):
            self.out.write(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.out.write('</' + tag + '>')

    def handle_data(self, data):
        self.out.write(data)

    def handle_entityref(self, data):
        self.out.write('&' + data)

    def handle_charref(self, data):
        self.out.write('&#' + data)

    def handle_comment(self, data):
        self.out.write('<!--' + data + '-->')

    def handle_decl(self, data):
        self.out.write('<!' + data + '>')

    def handle_pi(self, data):
        self.out.write('<?' + data + '>')

    def unknown_decl(self, data):
        self.out.write('<![' + data + ']>')




# instantiate the parser and fed it some HTML
#parser = WBHtml()
#instr = '<HTML X=\'a\' B=\'234\' some="other"><a href="Test"><BR/><head><title>Test</title></head>\n<body><h1>Parse me!</h1></body></HTML>'
#print instr
#print
#parser.feed(instr)
#print
if __name__ == "__main__":
    import doctest

    rewriter = ArchivalUrlRewriter('/20131226101010/http://example.com/some/path/index.html', '/web/')

    doctest.testmod()
