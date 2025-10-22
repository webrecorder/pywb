from pywb.warcserver.inputrequest import DirectWSGIInputRequest
from pywb.utils.loaders import extract_client_cookie

from six import iteritems
from six.moves.urllib.parse import urlsplit
import re


try: # pragma: no cover
    import brotli
    has_brotli = True
except Exception:  # pragma: no cover
    has_brotli = False
    print('Warning: brotli module could not be loaded, will not be able to replay brotli-encoded content')


#=============================================================================
class RewriteInputRequest(DirectWSGIInputRequest):
    RANGE_ARG_RX = re.compile('.*.googlevideo.com/videoplayback.*([&?]range=(\d+)-(\d+))')

    RANGE_HEADER = re.compile('bytes=(\d+)-(\d+)?')

    def __init__(self, env, urlkey, url, rewriter):
        super(RewriteInputRequest, self).__init__(env)
        self.urlkey = urlkey
        self.url = url
        self.rewriter = rewriter
        self.extra_cookie = None
        self.warcserver_headers = {}

        is_proxy = ('wsgiprox.proxy_host' in env)

        self.splits = urlsplit(self.url) if not is_proxy else None

    def get_full_request_uri(self):
        if not self.splits:
            return self.url

        uri = self.splits.path
        if not uri:
            uri = '/'

        if self.splits.query:
            uri += '?' + self.splits.query

        return uri

    def get_req_headers(self):
        headers = {}

        has_cookies = False

        for name, value in iteritems(self.env):
            if name == 'HTTP_HOST':
                name = 'Host'
                if self.splits:
                    value = self.splits.netloc

            elif name == 'HTTP_ORIGIN':
                name = 'Origin'
                referrer = self.env.get('HTTP_REFERER')
                if referrer:
                    splits = urlsplit(referrer)
                else:
                    splits = self.splits

                if splits:
                    value = (splits.scheme + '://' + splits.netloc)

            elif name == 'HTTP_X_CSRFTOKEN':
                name = 'X-CSRFToken'
                if self.splits:
                    cookie_val = extract_client_cookie(self.env, 'csrftoken')
                    if cookie_val:
                        value = cookie_val

            elif name == 'HTTP_X_PYWB_REQUESTED_WITH':
                continue

            elif name in ('HTTP_CONNECTION', 'HTTP_PROXY_CONNECTION'):
                continue

            elif name in ('HTTP_IF_MODIFIED_SINCE', 'HTTP_IF_UNMODIFIED_SINCE'):
                continue

            elif name == 'HTTP_X_PYWB_ACL_USER':
                name = name[5:].title().replace('_', '-')
                self.warcserver_headers[name] = value
                continue

            elif name == 'HTTP_X_FORWARDED_PROTO':
                name = 'X-Forwarded-Proto'
                if self.splits:
                    value = self.splits.scheme

            elif name == 'HTTP_ACCEPT_ENCODING':
                # if brotli not available, remove 'br' from accept-encoding to avoid
                # capture brotli encoded content
                # We have to remove zstd from the list of accepted encodings as warcio does not support it.
                disallowed_encodings = ('zstd',) if has_brotli else ('zstd', 'br')
                name = 'Accept-Encoding'
                value = ','.join([enc for enc in value.split(',') if enc.strip() not in disallowed_encodings])

            elif name.startswith('HTTP_'):
                name = name[5:].title().replace('_', '-')

            elif name in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                name = name.title().replace('_', '-')

            else:
                value = None

            if value:
                headers[name] = value

        if self.extra_cookie:
            headers['Cookie'] = self.extra_cookie + ';' + headers.get('Cookie', '')

        return headers

    def extract_range(self):
        use_206 = False
        start = None
        end = None
        url = self.url

        range_h = self.env.get('HTTP_RANGE')

        if range_h:
            m = self.RANGE_HEADER.match(range_h)
            if m:
                start = m.group(1)
                end = m.group(2)
                use_206 = True

        else:
            m = self.RANGE_ARG_RX.match(url)
            if m:
                start = m.group(2)
                end = m.group(3)
                url = url[:m.start(1)] + url[m.end(1):]
                use_206 = False

        if not start:
            return None

        start = int(start)

        if end:
            end = int(end)
        else:
            end = ''

        result = (url, start, end, use_206)
        return result

