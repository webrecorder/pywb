from webagg.inputrequest import DirectWSGIInputRequest
from pywb.utils.loaders import extract_client_cookie

from six import iteritems
from six.moves.urllib.parse import urlsplit


#=============================================================================
class RewriteInputRequest(DirectWSGIInputRequest):
    def __init__(self, env, urlkey, url, rewriter):
        super(RewriteInputRequest, self).__init__(env)
        self.urlkey = urlkey
        self.url = url
        self.rewriter = rewriter

        self.splits = urlsplit(self.url)

    def get_full_request_uri(self):
        uri = self.splits.path
        if self.splits.query:
            uri += '?' + self.splits.query

        return uri

    def get_req_headers(self):
        headers = {}

        has_cookies = False

        for name, value in iteritems(self.env):
            if name == 'HTTP_HOST':
                name = 'Host'
                value = self.splits.netloc

            elif name == 'HTTP_ORIGIN':
                name = 'Origin'
                value = (self.splits.scheme + '://' + self.splits.netloc)

            elif name == 'HTTP_X_CSRFTOKEN':
                name = 'X-CSRFToken'
                cookie_val = extract_client_cookie(env, 'csrftoken')
                if cookie_val:
                    value = cookie_val

            elif name == 'HTTP_X_PYWB_REQUESTED_WITH':
                continue

            elif name == 'HTTP_X_FORWARDED_PROTO':
                name = 'X-Forwarded-Proto'
                value = self.splits.scheme

            elif name == 'HTTP_COOKIE':
                name = 'Cookie'
                value = self._req_cookie_rewrite(value)
                has_cookies = True

            elif name.startswith('HTTP_'):
                name = name[5:].title().replace('_', '-')

            elif name in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                name = name.title().replace('_', '-')

            else:
                value = None

            if value:
                headers[name] = value

        if not has_cookies:
            value = self._req_cookie_rewrite('')
            if value:
                headers['Cookie'] = value

        return headers

    def _req_cookie_rewrite(self, value):
        rule = self.rewriter.ruleset.get_first_match(self.urlkey)
        if not rule or not rule.req_cookie_rewrite:
            return value

        for cr in rule.req_cookie_rewrite:
            try:
                value = cr['rx'].sub(cr['replace'], value)
            except KeyError:
                pass

        return value

