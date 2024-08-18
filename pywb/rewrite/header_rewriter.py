from warcio.statusandheaders import StatusAndHeaders
from warcio.timeutils import datetime_to_http_date
from datetime import datetime, timedelta, timezone
from six.moves.urllib.parse import urlsplit


#=============================================================================
class DefaultHeaderRewriter(object):
    header_rules = {
        'access-control-allow-origin': 'prefix-if-url-rewrite',
        'access-control-allow-credentials': 'prefix-if-url-rewrite',
        'access-control-expose-headers': 'prefix-if-url-rewrite',
        'access-control-max-age': 'prefix-if-url-rewrite',
        'access-control-allow-methods': 'prefix-if-url-rewrite',
        'access-control-allow-headers': 'prefix-if-url-rewrite',

        'accept-patch': 'keep',
        'accept-ranges': 'keep',

        'age': 'prefix',

        'allow': 'keep',

        'alt-svc': 'prefix',
        'cache-control': 'prefix',

        'connection': 'prefix',

        'content-base': 'url-rewrite',
        'content-disposition': 'keep',
        'content-encoding': 'prefix-if-content-rewrite',
        'content-language': 'keep',
        'content-length': 'content-length',
        'content-location': 'url-rewrite',
        'content-md5': 'prefix',
        'content-range': 'keep',
        'content-security-policy': 'prefix',
        'content-security-policy-report-only': 'prefix',
        'content-type': 'keep',

        'date': 'prefix',

        'etag': 'prefix',
        'expires': 'prefix',

        'last-modified': 'prefix',
        'link': 'keep',
        'location': 'url-rewrite',

        'p3p': 'prefix',
        'pragma': 'prefix',

        'proxy-authenticate': 'keep',

        'public-key-pins': 'prefix',
        'retry-after': 'prefix',
        'server': 'prefix',

        'set-cookie': 'cookie',

        'status': 'prefix',

        'strict-transport-security': 'prefix',

        'trailer': 'prefix',
        'transfer-encoding': 'transfer-encoding',
        'tk': 'prefix',

        'upgrade': 'prefix',
        'upgrade-insecure-requests': 'prefix',

        'vary': 'prefix',

        'via': 'prefix',

        'warning': 'prefix',

        'www-authenticate': 'keep',

        'x-frame-options': 'prefix',
        'x-xss-protection': 'prefix',
    }

    def __init__(self, rwinfo, header_prefix='X-Archive-Orig-'):
        self.header_prefix = header_prefix
        self.rwinfo = rwinfo
        self.http_headers = rwinfo.record.http_headers

    def __call__(self):
        new_headers_list = []
        for name, value in self.http_headers.headers:
            rule = self.header_rules.get(name.lower())
            new_header = self.rewrite_header(name, value, rule)
            if new_header:
                if isinstance(new_header, list):
                    new_headers_list.extend(new_header)
                else:
                    new_headers_list.append(new_header)

        if self.rwinfo.url_rewriter.wburl.mod == 'sw_':
            parts = urlsplit(self.rwinfo.url_rewriter.wburl.url)
            new_url = parts.scheme + '://' + parts.netloc + '/'
            rw_origin = self.rwinfo.url_rewriter.rewrite(new_url, mod='mp_')
            new_headers_list.append(('Service-Worker-Allowed', rw_origin))

        return StatusAndHeaders(self.http_headers.statusline,
                                headers=new_headers_list,
                                protocol=self.http_headers.protocol)

    def rewrite_header(self, name, value, rule):
        if rule == 'keep':
            return (name, value)

        elif rule == 'url-rewrite':
            if self.rwinfo.is_url_rw():
                return (name, self.rwinfo.url_rewriter.rewrite(value))
            else:
                return (name, value)

        elif rule == 'prefix-if-content-rewrite':
            if self.rwinfo.is_content_rw:
                return (self.header_prefix + name, value)
            else:
                return (name, value)

        elif rule == 'prefix-if-url-rewrite':
            if self.rwinfo.is_url_rw():
                return (self.header_prefix + name, value)
            else:
                return (name, value)

        elif rule == 'content-length':
            if value == '0':
                return (name, value)

            if not self.rwinfo.is_content_rw:
                try:
                    if int(value) >= 0:
                        return (name, value)
                except:
                    pass

            return (self.header_prefix + name, value)

        elif rule == 'transfer-encoding':
            self.rwinfo.is_chunked = True
            return (self.header_prefix + name, value)

        elif rule == 'cookie':
            if self.rwinfo.cookie_rewriter and self.rwinfo.is_url_rw():
                return self.rwinfo.cookie_rewriter.rewrite(value)
            else:
                return (name, value)

        elif rule == 'prefix':
            return (self.header_prefix + name, value)

        return (name, value)

    def _add_cache_headers(self, new_headers, http_cache):
        try:
            age = int(http_cache)
        except:
            age = 0

        if age <= 0:
            new_headers.append(('Cache-Control', 'no-cache; no-store'))
        else:
            dt = datetime.now(timezone.utc)
            dt = dt + timedelta(seconds=age)
            new_headers.append(('Cache-Control', 'max-age=' + str(age)))
            new_headers.append(('Expires', datetime_to_http_date(dt)))


