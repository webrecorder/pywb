import re
from urllib.parse import parse_qs, urlsplit
from pywb.rewrite.content_rewriter import StreamingRewriter


# ============================================================================
class JSONPRewriter(StreamingRewriter):
    #JSONP = re.compile(r'^(?:\s*\/\*(?:.*)\*\/)*\s*(\w+)\(\{')
    # Match a single /* and // style comments at the beginning
    JSONP = re.compile(r'(?:^[ \t]*(?:(?:\/\*[^\*]*\*\/)|(?:\/\/[^\n]+[\n])))*[ \t]*(\w+)\(\{', re.M)
    CALLBACK = re.compile(r'^[A-Za-z_$][0-9A-Za-z_$]*(?:\.[A-Za-z_$][0-9A-Za-z_$]*)*$')

    def rewrite(self, string):
        # see if json is jsonp, starts with callback func
        m_json = self.JSONP.match(string)
        if not m_json:
            return string

        # see if there is a callback param in current url
        query = parse_qs(urlsplit(self.url_rewriter.wburl.url).query, keep_blank_values=True)
        callbacks = query.get('callback')
        if not callbacks:
            return string

        callback = callbacks[-1]
        if callback == '?':
            # this is a very sharp edge case e.g. callback=?
            # since we only have this string[m_json.end(1):]
            # would cut off the name of the CB if any is included
            # so we just pass the string through
            return string
        if not self.CALLBACK.match(callback):
            return string

        string = callback + string[m_json.end(1):]
        return string

