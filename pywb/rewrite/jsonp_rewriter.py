import re
from pywb.rewrite.content_rewriter import StreamingRewriter


# ============================================================================
class JSONPRewriter(StreamingRewriter):
    #JSONP = re.compile(r'^(?:\s*\/\*(?:.*)\*\/)*\s*(\w+)\(\{')
    # Match a single /* and // style comments at the beginning
    JSONP = re.compile(r'(?:^[ \t]*(?:(?:\/\*[^\*]*\*\/)|(?:\/\/[^\n]+[\n])))*[ \t]*(\w+)\(\{', re.M)
    CALLBACK = re.compile(r'[?].*callback=([^&]+)')

    def rewrite(self, string):
        # see if json is jsonp, starts with callback func
        m_json = self.JSONP.match(string)
        if not m_json:
            return string

        # see if there is a callback param in current url
        m_callback = self.CALLBACK.search(self.url_rewriter.wburl.url)
        if not m_callback:
            return string
        if m_callback.group(1) == '?':
            # this is a very sharp edge case e.g. callback=?
            # since we only have this string[m_json.end(1):]
            # would cut off the name of the CB if any is included
            # so we just pass the string through
            return string

        string = m_callback.group(1) + string[m_json.end(1):]
        return string

