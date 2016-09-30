from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.timeutils import datetime_to_http_date
from datetime import datetime, timedelta
import six


#=================================================================
class RewrittenStatusAndHeaders(object):
    def __init__(self, statusline, headers,
                 removed_header_dict, text_type, charset):

        self.status_headers = StatusAndHeaders(statusline, headers)
        self.removed_header_dict = removed_header_dict
        self.text_type = text_type
        self.charset = charset

    def contains_removed_header(self, name, value):
        return self.removed_header_dict.get(name) == value

    def readd_rewrite_removed(self):
        for name in HeaderRewriter.KEEP_NO_REWRITE_HEADERS:
            value = self.removed_header_dict.get(name)
            if value is not None:
                self.status_headers.headers.append((name, value))


#=================================================================
class HeaderRewriter(object):
    REWRITE_TYPES = {
        'html': ['text/html',
                 'application/xhtml',
                 'application/xhtml+xml'],

        'css':  ['text/css'],

        'js':   ['text/javascript',
                 'application/javascript',
                 'application/x-javascript'],

        'json': ['application/json'],

        'xml':  ['/xml', '+xml', '.xml', '.rss'],

        'plain': ['text/plain'],
    }

    PROXY_HEADERS = ['content-type', 'content-disposition', 'content-range',
                     'accept-ranges', 'www-authenticate', 'proxy-authenticate']

    URL_REWRITE_HEADERS = ['location', 'content-location', 'content-base']

    REMOVE_ALWAYS_HEADERS = ['transfer-encoding']

    KEEP_PROXY_HEADERS = ['content-security-policy', 'strict-transport-security']

    KEEP_NO_REWRITE_HEADERS = ['content-length', 'content-encoding']

    COOKIE_HEADERS = ['set-cookie', 'cookie']

    CACHE_HEADERS = ['cache-control', 'expires', 'etag', 'last-modified']


    def __init__(self, header_prefix='X-Archive-Orig-'):
        self.header_prefix = header_prefix

    def rewrite(self, status_headers, urlrewriter, cookie_rewriter):
        content_type = status_headers.get_header('Content-Type')
        text_type = None
        charset = None
        content_modified = False
        http_cache = None
        if urlrewriter:
            http_cache = urlrewriter.rewrite_opts.get('http_cache')

        if content_type:
            text_type = self._extract_text_type(content_type)
            if text_type:
                charset = self._extract_char_set(content_type)
                content_modified = True

        result = self._rewrite_headers(status_headers.headers,
                                       urlrewriter,
                                       cookie_rewriter,
                                       content_modified,
                                       http_cache)

        new_headers = result[0]
        removed_header_dict = result[1]

        if http_cache != None and http_cache != 'pass':
            self._add_cache_headers(new_headers, http_cache)

        return RewrittenStatusAndHeaders(status_headers.statusline,
                                         new_headers,
                                         removed_header_dict,
                                         text_type,
                                         charset)

    def _add_cache_headers(self, new_headers, http_cache):
        try:
            age = int(http_cache)
        except:
            age = 0

        if age <= 0:
            new_headers.append(('Cache-Control', 'no-cache; no-store'))
        else:
            dt = datetime.utcnow()
            dt = dt + timedelta(seconds=age)
            new_headers.append(('Cache-Control', 'max-age=' + str(age)))
            new_headers.append(('Expires', datetime_to_http_date(dt)))

    def _extract_text_type(self, content_type):
        for ctype, mimelist in six.iteritems(self.REWRITE_TYPES):
            if any((mime in content_type) for mime in mimelist):
                return ctype

        return None

    def _extract_char_set(self, content_type):
        CHARSET_TOKEN = 'charset='
        idx = content_type.find(CHARSET_TOKEN)
        if idx < 0:
            return None

        return content_type[idx + len(CHARSET_TOKEN):].lower()

    def _rewrite_headers(self, headers, urlrewriter,
                         cookie_rewriter,
                         content_modified,
                         http_cache):

        new_headers = []
        removed_header_dict = {}

        def add_header(name, value):
            new_headers.append((name, value))

        def add_prefixed_header(name, value):
            new_headers.append((self.header_prefix + name, value))

        for (name, value) in headers:
            lowername = name.lower()

            if lowername in self.PROXY_HEADERS:
                add_header(name, value)

            elif urlrewriter and urlrewriter.prefix and lowername in self.URL_REWRITE_HEADERS:
                new_headers.append((name, urlrewriter.rewrite(value)))

            elif lowername in self.KEEP_NO_REWRITE_HEADERS:
                if content_modified:
                    removed_header_dict[lowername] = value
                    add_prefixed_header(name, value)
                else:
                    add_header(name, value)

            elif lowername in self.KEEP_PROXY_HEADERS:
                if urlrewriter.prefix:
                    removed_header_dict[lowername] = value
                    add_prefixed_header(name, value)
                else:
                    add_header(name, value)

            elif lowername in self.REMOVE_ALWAYS_HEADERS:
                removed_header_dict[lowername] = value
                add_prefixed_header(name, value)

            elif (lowername in self.COOKIE_HEADERS and
                  cookie_rewriter):
                cookie_list = cookie_rewriter.rewrite(value)
                new_headers.extend(cookie_list)

            elif (lowername in self.CACHE_HEADERS):
                if http_cache == 'pass':
                    add_header(name, value)
                else:
                    add_prefixed_header(name, value)

            elif urlrewriter and urlrewriter.prefix:
                add_prefixed_header(name, value)
            else:
                add_header(name, value)

        return (new_headers, removed_header_dict)
