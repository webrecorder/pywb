from pywb.utils.statusandheaders import StatusAndHeaders


#=================================================================
class RewrittenStatusAndHeaders:
    def __init__(self, statusline, headers,
                 removed_header_dict, text_type, charset):

        self.status_headers = StatusAndHeaders(statusline, headers)
        self.removed_header_dict = removed_header_dict
        self.text_type = text_type
        self.charset = charset

    def contains_removed_header(self, name, value):
        return self.removed_header_dict.get(name) == value


#=================================================================
class HeaderRewriter:
    REWRITE_TYPES = {
        'html': ['text/html', 'application/xhtml'],

        'css':  ['text/css'],

        'js':   ['text/javascript',
                 'application/javascript',
                 'application/x-javascript'],

        'xml':  ['/xml', '+xml', '.xml', '.rss'],
    }

    PROXY_HEADERS = ['content-type', 'content-disposition']

    URL_REWRITE_HEADERS = ['location', 'content-location', 'content-base']

    ENCODING_HEADERS = ['content-encoding']

    REMOVE_HEADERS = ['transfer-encoding']

    PROXY_NO_REWRITE_HEADERS = ['content-length']

    COOKIE_HEADERS = ['set-cookie', 'cookie']

    def __init__(self, header_prefix='X-Archive-Orig-'):
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

        result = self._rewrite_headers(status_headers.headers,
                                       urlrewriter,
                                       strip_encoding)

        new_headers = result[0]
        removed_header_dict = result[1]

        return RewrittenStatusAndHeaders(status_headers.statusline,
                                         new_headers,
                                         removed_header_dict,
                                         text_type,
                                         charset)

    def _extract_text_type(self, content_type):
        for ctype, mimelist in self.REWRITE_TYPES.iteritems():
            if any((mime in content_type) for mime in mimelist):
                return ctype

        return None

    def _extract_char_set(self, content_type):
        CHARSET_TOKEN = 'charset='
        idx = content_type.find(CHARSET_TOKEN)
        if idx < 0:
            return None

        return content_type[idx + len(CHARSET_TOKEN):].lower()

    def _rewrite_headers(self, headers, urlrewriter, content_rewritten=False):
        new_headers = []
        removed_header_dict = {}

        cookie_rewriter = urlrewriter.get_cookie_rewriter()

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

            elif (lowername in self.PROXY_NO_REWRITE_HEADERS and
                  not content_rewritten):
                new_headers.append((name, value))

            elif (lowername in self.COOKIE_HEADERS and
                  cookie_rewriter):
                cookie_list = cookie_rewriter.rewrite(value)
                new_headers.extend(cookie_list)

            else:
                new_headers.append((self.header_prefix + name, value))

        return (new_headers, removed_header_dict)
