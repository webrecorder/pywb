import urlparse

from wbrequestresponse import WbRequest, WbResponse
from url_rewriter import ArchivalUrlRewriter

#=================================================================
# ArchivalRequestRouter -- route WB requests in archival mode
#=================================================================
class ArchivalRequestRouter:
    def __init__(self, mappings, hostpaths = None, abs_path = True):
        self.mappings = mappings
        self.fallback = ReferRedirect(hostpaths)
        self.abs_path = abs_path

    def _parseRequest(self, env):
        request_uri = env['REQUEST_URI']

        for coll, handler in self.mappings.iteritems():
            rel_prefix = '/' + coll + '/'
            if request_uri.startswith(rel_prefix):
                #return value, ArchivalRequestRouter._prefix_request(env, key, request_uri)
                req = WbRequest(env,
                                request_uri = request_uri,
                                coll = coll,
                                wb_url = request_uri[len(coll) + 1:],
                                wb_prefix = self.getPrefix(env, rel_prefix))

                return handler, req

        return self.fallback, WbRequest.from_uri(request_uri, env)

    def handleRequest(self, env):
        handler, wbrequest = self._parseRequest(env)
        resp = None

        if isinstance(handler, list):
            for x in handler:
                resp = x(wbrequest, resp)
        else:
            resp = handler(wbrequest, resp)

        return resp

    def getPrefix(self, env, rel_prefix):
        if self.abs_path:
            try:
                return env['wsgi.url_scheme'] + '://' + env['HTTP_HOST'] + rel_prefix
            except KeyError:
                return rel_prefix
        else:
            return rel_prefix


#=================================================================
# ReferRedirect -- redirect urls that have 'fallen through' based on the referrer settings
#=================================================================
class ReferRedirect:

    """
    >>> ReferRedirect('http://localhost:8080/').matchPrefixs
    ['http://localhost:8080/']

    >>> ReferRedirect(['http://example:9090/']).matchPrefixs
    ['http://example:9090/']

    >>> test_redir('http://localhost:8080/', '/other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
    'http://localhost:8080/coll/20131010/http://example.com/path/other.html'

    >>> test_redir('http://localhost:8080/', '/../other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
    'http://localhost:8080/coll/20131010/http://example.com/other.html'

    >>> test_redir('http://localhost:8080/', '/../../other.html', 'http://localhost:8080/coll/20131010/http://example.com/index.html')
    'http://localhost:8080/coll/20131010/http://example.com/other.html'

    >>> test_redir('http://example:8080/', '/other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
    False
    """

    def __init__(self, matchPrefixs):
        if isinstance(matchPrefixs, list):
            self.matchPrefixs = matchPrefixs
        else:
            self.matchPrefixs = [matchPrefixs]


    def __call__(self, wbrequest, _):
        if wbrequest.referrer is None:
            return None

        if not any (wbrequest.referrer.startswith(i) for i in self.matchPrefixs):
            return None

        try:
            ref_split = urlparse.urlsplit(wbrequest.referrer)
            ref_path = ref_split.path[1:].split('/', 1)

            rewriter = ArchivalUrlRewriter('/' + ref_path[1], '/' + ref_path[0])

            rel_request_uri = wbrequest.request_uri[1:]

            #ref_wb_url = archiveurl('/' + ref_path[1])
            #ref_wb_url.url = urlparse.urljoin(ref_wb_url.url, wbrequest.request_uri[1:])
            #ref_wb_url.url = ref_wb_url.url.replace('../', '')

            #final_url = urlparse.urlunsplit((ref_split.scheme, ref_split.netloc, ref_path[0] + str(ref_wb_url), '', ''))
            final_url = urlparse.urlunsplit((ref_split.scheme, ref_split.netloc, rewriter.rewrite(rel_request_uri), '', ''))

        except Exception as e:
            raise e

        return WbResponse.redir_response(final_url)

if __name__ == "__main__":
    import doctest

    def test_redir(matchHost, request_uri, referrer):
        env = {'REQUEST_URI': request_uri, 'HTTP_REFERER': referrer}

        redir = ReferRedirect(matchHost)
        req = WbRequest.from_uri(request_uri, env)
        rep = redir(req, None)
        if not rep:
            return False

        return rep.status_headers.getHeader('Location')


    doctest.testmod()


