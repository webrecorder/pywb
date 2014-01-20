import urlparse
import re

from wbrequestresponse import WbRequest, WbResponse
from url_rewriter import ArchivalUrlRewriter
from wbarchivalurl import ArchivalUrl

#=================================================================
# ArchivalRequestRouter -- route WB requests in archival mode
#=================================================================
class ArchivalRequestRouter:
    def __init__(self, handlers, hostpaths = None, abs_path = True, archivalurl_class = ArchivalUrl):
        self.handlers = handlers
        self.fallback = ReferRedirect(hostpaths)
        self.abs_path = abs_path
        self.archivalurl_class = archivalurl_class

    def __call__(self, env):
        for handler in self.handlers:
            result = handler(env, self.abs_path, self.archivalurl_class)
            if result:
                return result

        if not self.fallback:
            return None

        return self.fallback(WbRequest.from_uri(None, env))




#=================================================================
# Route by matching regex (or fixed prefix)
# of request uri (excluding first '/')
#=================================================================
class Route:
    def __init__(self, regex, handler, coll_group = 0):
        self.regex = re.compile(regex)
        self.handler = handler
        # collection id from regex group (default 0)
        self.coll_group = coll_group


    def __call__(self, env, useAbsPrefix, archivalurl_class):
        request_uri =  env['REL_REQUEST_URI']
        matcher = self.regex.match(request_uri[1:])
        if not matcher:
            return None

        rel_prefix = matcher.group(0)

        if rel_prefix:
            wb_prefix = env['SCRIPT_NAME'] + '/' + rel_prefix + '/'
            wb_url = request_uri[len(rel_prefix) + 1:] # remove the '/' + rel_prefix part of uri
        else:
            wb_prefix = env['SCRIPT_NAME'] + '/'
            wb_url = request_uri # the request_uri is the wb_url, since no coll

        coll = matcher.group(self.coll_group)

        wbrequest = WbRequest(env,
                              request_uri = request_uri,
                              coll = coll,
                              wb_url = wb_url,
                              wb_prefix = wb_prefix,
                              use_abs_prefix = useAbsPrefix,
                              archivalurl_class = archivalurl_class)


        # Allow for setup of additional filters
        self._addFilters(wbrequest, matcher)

        return self._handleRequest(wbrequest)

    def _addFilters(self, wbrequest, matcher):
        pass

    def _handleRequest(self, wbrequest):
        return self.handler(wbrequest)


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


    def __call__(self, wbrequest):
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
        env = {'REL_REQUEST_URI': request_uri, 'HTTP_REFERER': referrer}

        redir = ReferRedirect(matchHost)
        req = WbRequest.from_uri(request_uri, env)
        rep = redir(req)
        if not rep:
            return False

        return rep.status_headers.getHeader('Location')


    doctest.testmod()


