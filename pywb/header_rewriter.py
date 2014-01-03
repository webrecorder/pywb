from wbrequestresponse import StatusAndHeaders

#=================================================================
class RewrittenStatusAndHeaders:
    def __init__(self, statusline, headers, removedHeaderDict, textType, charset):
        self.status_headers = StatusAndHeaders(statusline, headers)
        self.removedHeaderDict = removedHeaderDict
        self.textType = textType
        self.charset = charset

    def containsRemovedHeader(self, name, value):
        return self.removedHeaderDict.get(name) == value


#=================================================================
class HeaderRewriter:
    """
    # Text with charset
    >>> test_rewrite([('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'), ('Content-Length', '5'), ('Content-Type', 'text/html;charset=utf-8')])
    {'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
      ('X-Archive-Orig-Content-Length', '5'),
      ('Content-Type', 'text/html;charset=utf-8')]), 'charset': 'utf-8', 'textType': 'html', 'removedHeaderDict': {}}

    # Redirect
    >>> test_rewrite([('Connection', 'close'), ('Location', '/other.html')], '302 Redirect')
    {'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect', headers = [ ('X-Archive-Orig-Connection', 'close'),
      ('Location', '/web/20131226101010/http://example.com/other.html')]), 'charset': None, 'textType': None, 'removedHeaderDict': {}}

    # gzip
    >>> test_rewrite([('Content-Length', '199999'), ('Content-Type', 'text/javascript'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
    {'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Content-Length', '199999'),
      ('Content-Type', 'text/javascript')]), 'charset': None, 'textType': 'js', 'removedHeaderDict': {'transfer-encoding': 'chunked', 'content-encoding': 'gzip'}}

    # Binary
    >>> test_rewrite([('Content-Length', '200000'), ('Content-Type', 'image/png'), ('Cookie', 'blah'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
    {'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('Content-Length', '200000'),
      ('Content-Type', 'image/png'),
      ('X-Archive-Orig-Cookie', 'blah'),
      ('Content-Encoding', 'gzip'),
      ('Transfer-Encoding', 'chunked')]), 'charset': None, 'textType': None, 'removedHeaderDict': {}}

    """


    REWRITE_TYPES = {
        'html': ['text/html', 'application/xhtml'],
        'css':  ['text/css'],
        'js':   ['text/javascript', 'application/javascript', 'application/x-javascript'],
        'xml':  ['/xml', '+xml', '.xml', '.rss'],
    }


    PROXY_HEADERS = ('content-type', 'content-disposition')

    URL_REWRITE_HEADERS = ('location', 'content-location', 'content-base')

    ENCODING_HEADERS = ('content-encoding', 'transfer-encoding')

    PROXY_NO_REWRITE_HEADERS = ('content-length')

    def __init__(self, headerPrefix = 'X-Archive-Orig-'):
        self.headerPrefix = headerPrefix

    def rewrite(self, status_headers, urlrewriter):
        contentType = status_headers.getHeader('Content-Type')
        textType = None
        charset = None
        stripEncoding = False

        if contentType:
            textType = self._extractTextType(contentType)
            if textType:
                charset = self._extractCharSet(contentType)
                stripEncoding = True

        (newHeaders, removedHeaderDict) = self._rewriteHeaders(status_headers.headers, urlrewriter, stripEncoding)

        return RewrittenStatusAndHeaders(status_headers.statusline, newHeaders, removedHeaderDict, textType, charset)


    def _extractTextType(self, contentType):
        for ctype, mimelist in self.REWRITE_TYPES.iteritems():
            if any ((mime in contentType) for mime in mimelist):
                return ctype

        return None

    def _extractCharSet(self, contentType):
        CHARSET_TOKEN = 'charset='
        idx = contentType.find(CHARSET_TOKEN)
        if idx < 0:
            return None

        return contentType[idx + len(CHARSET_TOKEN):]

    def _rewriteHeaders(self, headers, urlrewriter, contentRewritten = False):
        newHeaders = []
        removedHeaderDict = {}

        for (name, value) in headers:
            lowername = name.lower()
            if lowername in self.PROXY_HEADERS:
                newHeaders.append((name, value))
            elif lowername in self.URL_REWRITE_HEADERS:
                newHeaders.append((name, urlrewriter.rewrite(value)))
            elif lowername in self.ENCODING_HEADERS:
                if contentRewritten:
                    removedHeaderDict[lowername] = value
                else:
                    newHeaders.append((name, value))
            elif lowername in self.PROXY_NO_REWRITE_HEADERS and not contentRewritten:
                newHeaders.append((name, value))
            else:
                newHeaders.append((self.headerPrefix + name, value))

        return (newHeaders, removedHeaderDict)

if __name__ == "__main__":
    import doctest
    import os
    import pprint
    import url_rewriter

    urlrewriter = url_rewriter.ArchivalUrlRewriter('/20131226101010/http://example.com/some/path/index.html', '/web/')

    headerrewriter = HeaderRewriter()

    def test_rewrite(headers, status = '200 OK'):
        rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers), urlrewriter)
        return vars(rewritten)

    doctest.testmod()

