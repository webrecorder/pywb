import re
from pywb.rewrite.content_rewriter import StreamingRewriter


# ============================================================================
class HTMLInsertOnlyRewriter(StreamingRewriter):
    """ Insert custom string into HTML into the head, before any tag not <head> or <html>
        no other rewriting performed
    """
    NOT_HEAD_REGEX = re.compile(r'(<\s*\b)(?!(html|head))', re.I)

    XML_HEADER = re.compile(r'<\?xml.*\?>')

    def __init__(self, url_rewriter, **kwargs):
        super(HTMLInsertOnlyRewriter, self).__init__(url_rewriter, False)
        self.head_insert = kwargs['head_insert']

        self.done = False
        self.first = True

    def rewrite(self, string):
        if self.first:
            if self.url_rewriter.rewrite_opts.get('is_ajax') and self.XML_HEADER.search(string):
                self.done = True

            self.first = False

        if self.done:
            return string

        m = self.NOT_HEAD_REGEX.search(string)
        if m:
            inx = m.start()
            buff = string[:inx]
            buff += self.head_insert
            buff += string[inx:]
            self.done = True
            return buff
        else:
            return string

    def final_read(self):
        return '' if self.done else self.head_insert
