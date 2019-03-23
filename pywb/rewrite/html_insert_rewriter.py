import re
from pywb.rewrite.content_rewriter import StreamingRewriter


# ============================================================================
class HTMLInsertOnlyRewriter(StreamingRewriter):
    """ Insert custom string into HTML <head> tag
        no other rewriting performed
    """
    HEAD_REGEX = re.compile('<\s*head\\b[^>]*[>]+', re.I)

    def __init__(self, url_rewriter, **kwargs):
        super(HTMLInsertOnlyRewriter, self).__init__(url_rewriter, False)
        self.head_insert = kwargs['head_insert']

        self.done = False

    def rewrite(self, string):
        if self.done:
            return string

        # only try to find <head> in first buffer
        self.done = True
        m = self.HEAD_REGEX.search(string)
        if m:
            inx = m.end()
            buff = string[:inx]
            buff += self.head_insert
            buff += string[inx:]
            return buff
        else:
            return string


