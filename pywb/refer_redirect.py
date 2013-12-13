import aurl
import urlparse
from wbrequestresponse import WbRequest, WbResponse

# Redirect urls that have 'fallen through' based on the referrer
# settings
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

    def run(self, wbrequest):
        if wbrequest.referrer is None:
            return None

        if not any (wbrequest.referrer.startswith(i) for i in self.matchPrefixs):
            return None

        try:
            ref_split = urlparse.urlsplit(wbrequest.referrer)
            ref_path = ref_split.path[1:].split('/', 1)

            ref_wb_url = aurl.aurl('/' + ref_path[1])

            ref_wb_url.url = urlparse.urljoin(ref_wb_url.url, wbrequest.request_uri[1:])
            ref_wb_url.url = ref_wb_url.url.replace('../', '')

            final_url = urlparse.urlunsplit((ref_split.scheme, ref_split.netloc, ref_path[0] + str(ref_wb_url), '', ''))

        except Exception as e:
            return None

        return WbResponse.redir_response(final_url)

if __name__ == "__main__":
    import doctest

    def test_redir(matchHost, request_uri, referrer):
        env = {'REQUEST_URI': request_uri, 'HTTP_REFERER': referrer}

        redir = ReferRedirect(matchHost)
        req = WbRequest(env)
        rep = redir.run(req)
        if not rep:
            return False

        return rep.get_header('Location')


    doctest.testmod()


