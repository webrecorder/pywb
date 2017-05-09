from warcio.statusandheaders import StatusAndHeaders
from warcio.timeutils import datetime_to_http_date
from datetime import datetime, timedelta


#=============================================================================
class PrefixHeaderRewriter(object):
    header_rules = {
        'content-type': 'keep',
        'content-disposition': 'keep',
        'content-range': 'keep',
        'accept-rangees': 'keep',
        'www-authenticate': 'keep',
        'proxy-authenticate': 'keep',

        'location': 'url-rewrite',
        'content-location': 'url-rewrite',
        'content-base': 'url-rewrite',

        'content-encoding': 'keep-if-no-content-rewrite',
        'content-length': 'content-length',

        'set-cookie': 'cookie',
        'cookie': 'cookie',
    }

    default_rule = 'prefix'

    def __init__(self, rwinfo, header_prefix='X-Archive-Orig-'):
        self.header_prefix = header_prefix
        self.rwinfo = rwinfo
        self.http_headers = rwinfo.record.http_headers

    def __call__(self):
        new_headers_list = []
        for name, value in self.http_headers.headers:
            rule = self.header_rules.get(name.lower(), self.default_rule)
            new_header = self.rewrite_header(name, value, rule)
            if new_header:
                if isinstance(new_header, list):
                    new_headers_list.extend(new_header)
                else:
                    new_headers_list.append(new_header)

        return StatusAndHeaders(self.http_headers.statusline,
                                headers=new_headers_list,
                                protocol=self.http_headers.protocol)

    def rewrite_header(self, name, value, rule):
        if rule == 'keep':
            return (name, value)

        elif rule == 'url-rewrite':
            return (name, self.rwinfo.url_rewriter.rewrite(value))

        elif rule == 'keep-if-no-content-rewrite':
            if not self.rwinfo.is_content_rw():
                return (name, value)

        elif rule == 'content-length':
            if value == '0':
                return (name, value)

            if not self.rwinfo.is_content_rw():
                try:
                    if int(value) >= 0:
                        return (name, value)
                except:
                    pass

        elif rule == 'cookie':
            if self.rwinfo.cookie_rewriter:
                return self.rwinfo.cookie_rewriter.rewrite(value)
            else:
                return (name, value)

        # default 'prefix'
        return (self.header_prefix + name, value)

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


#=============================================================================
class ProxyHeaderRewriter(PrefixHeaderRewriter):
    header_rules = {
        'transfer-encoding': 'prefix',
        'connection': 'prefix',
    }

    default_rule = 'keep'
