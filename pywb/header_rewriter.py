from wbrequestresponse import StatusAndHeaders

#=================================================================
class RewrittenStatusAndHeaders:
    def __init__(self, statusline, headers, removed_header_dict, text_type, charset):
        self.status_headers = StatusAndHeaders(statusline, headers)
        self.removed_header_dict = removed_header_dict
        self.text_type = text_type
        self.charset = charset

    def contains_removed_header(self, name, value):
        return self.removed_header_dict.get(name) == value


#=================================================================
class HeaderRewriter:
    """
    # Text with charset
    >>> test_rewrite([('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'), ('Content-Length', '5'), ('Content-Type', 'text/html;charset=UTF-8')])
    {'text_type': 'html', 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
      ('X-Archive-Orig-Content-Length', '5'),
      ('Content-Type', 'text/html;charset=UTF-8')]), 'removed_header_dict': {}, 'charset': 'utf-8'}

    # Redirect
    >>> test_rewrite([('Connection', 'close'), ('Location', '/other.html')], '302 Redirect')
    {'text_type': None, 'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect', headers = [ ('X-Archive-Orig-Connection', 'close'),
      ('Location', '/web/20131226101010/http://example.com/other.html')]), 'removed_header_dict': {}, 'charset': None}

    # gzip
    >>> test_rewrite([('Content-Length', '199999'), ('Content-Type', 'text/javascript'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
    {'text_type': 'js', 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Content-Length', '199999'),
      ('Content-Type', 'text/javascript')]), 'removed_header_dict': {'transfer-encoding': 'chunked', 'content-encoding': 'gzip'}, 'charset': None}

    # Binary
    >>> test_rewrite([('Content-Length', '200000'), ('Content-Type', 'image/png'), ('Cookie', 'blah'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
    {'text_type': None, 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('Content-Length', '200000'),
      ('Content-Type', 'image/png'),
      ('X-Archive-Orig-Cookie', 'blah'),
      ('Content-Encoding', 'gzip')]), 'removed_header_dict': {'transfer-encoding': 'chunked'}, 'charset': None}

    Removing Transfer-Encoding always, Was:
      ('Content-Encoding', 'gzip'),
      ('Transfer-Encoding', 'chunked')]), 'charset': None, 'text_type': None, 'removed_header_dict': {}}

    """


    REWRITE_TYPES = {
        'html': ['text/html', 'application/xhtml'],
        'css':  ['text/css'],
        'js':   ['text/javascript', 'application/javascript', 'application/x-javascript'],
        'xml':  ['/xml', '+xml', '.xml', '.rss'],
    }


    PROXY_HEADERS = ['content-type', 'content-disposition']

    URL_REWRITE_HEADERS = ['location', 'content-location', 'content-base']

    ENCODING_HEADERS = ['content-encoding']

    REMOVE_HEADERS = ['transfer-encoding']

    PROXY_NO_REWRITE_HEADERS = ['content-length']

    def __init__(self, header_prefix = 'X-Archive-Orig-'):
        self.header_prefix = header_prefix

    def rewrite(self, status_headers, urlrewriter):
        content_type = status_headers.get_header('Content-Type')
        text_type = None
        charset = None
        strip_encoding = False

        if content_type:
            text_type = self._extract_text_type(content_type)
            if text_type:
                charset = self._extract_char_set(content_type)
                strip_encoding = True

        (new_headers, removed_header_dict) = self._rewrite_headers(status_headers.headers, urlrewriter, strip_encoding)

        return RewrittenStatusAndHeaders(status_headers.statusline, new_headers, removed_header_dict, text_type, charset)


    def _extract_text_type(self, content_type):
        for ctype, mimelist in self.REWRITE_TYPES.iteritems():
            if any ((mime in content_type) for mime in mimelist):
                return ctype

        return None

    def _extract_char_set(self, content_type):
        CHARSET_TOKEN = 'charset='
        idx = content_type.find(CHARSET_TOKEN)
        if idx < 0:
            return None

        return content_type[idx + len(CHARSET_TOKEN):].lower()

    def _rewrite_headers(self, headers, urlrewriter, content_rewritten = False):
        new_headers = []
        removed_header_dict = {}

        for (name, value) in headers:
            lowername = name.lower()
            if lowername in self.PROXY_HEADERS:
                new_headers.append((name, value))
            elif lowername in self.URL_REWRITE_HEADERS:
                new_headers.append((name, urlrewriter.rewrite(value)))
            elif lowername in self.ENCODING_HEADERS:
                if content_rewritten:
                    removed_header_dict[lowername] = value
                else:
                    new_headers.append((name, value))
            elif lowername in self.REMOVE_HEADERS:
                    removed_header_dict[lowername] = value
            elif lowername in self.PROXY_NO_REWRITE_HEADERS and not content_rewritten:
                new_headers.append((name, value))
            else:
                new_headers.append((self.header_prefix + name, value))

        return (new_headers, removed_header_dict)

import utils
if __name__ == "__main__" or utils.enable_doctests():
    import os
    import pprint
    import url_rewriter

    urlrewriter = url_rewriter.UrlRewriter('/20131226101010/http://example.com/some/path/index.html', '/web/')

    headerrewriter = HeaderRewriter()

    def test_rewrite(headers, status = '200 OK'):
        rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers), urlrewriter)
        return vars(rewritten)

    import doctest
    doctest.testmod()

