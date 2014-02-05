import urlparse
import re
import wbexceptions

from wbrequestresponse import WbRequest, WbResponse
from url_rewriter import UrlRewriter
from wburl import WbUrl

#=================================================================
# ArchivalRouter -- route WB requests in archival mode
#=================================================================
class ArchivalRouter:
    def __init__(self, routes, hostpaths = None, abs_path = True, home_view = None, error_view = None):
        self.routes = routes
        self.fallback = ReferRedirect(hostpaths)
        self.abs_path = abs_path

        self.home_view = home_view
        self.error_view = error_view

    def __call__(self, env):
        for route in self.routes:
            result = route(env, self.abs_path)
            if result:
                return result

        # Home Page
        if env['REL_REQUEST_URI'] in ['/', '/index.html', '/index.htm']:
            return self.render_home_page()

        if not self.fallback:
            return None

        return self.fallback(WbRequest.from_uri(None, env))


    def render_home_page(self):
        # render the homepage!
        if self.home_view:
            return self.home_view.render_response(routes = self.routes)
        else:
            # default home page template
            text = '\n'.join(map(str, self.routes))
            return WbResponse.text_response(text)

#=================================================================
# Route by matching regex (or fixed prefix)
# of request uri (excluding first '/')
#=================================================================
class Route:
    """
    # route with relative path
    >>> Route('web', handlers.BaseHandler())({'REL_REQUEST_URI': '/web/test.example.com', 'SCRIPT_NAME': ''}, False)
    {'wb_url': ('latest_replay', '', '', 'http://test.example.com', 'http://test.example.com'), 'coll': 'web', 'wb_prefix': '/web/', 'request_uri': '/web/test.example.com'}

    # route with absolute path, running at script /my_pywb
    >>> Route('web', handlers.BaseHandler())({'REL_REQUEST_URI': '/web/2013im_/test.example.com', 'SCRIPT_NAME': '/my_pywb', 'HTTP_HOST': 'localhost:8081', 'wsgi.url_scheme': 'https'}, True)
    {'wb_url': ('replay', '2013', 'im_', 'http://test.example.com', '2013im_/http://test.example.com'), 'coll': 'web', 'wb_prefix': 'https://localhost:8081/my_pywb/web/', 'request_uri': '/web/2013im_/test.example.com'}


    # not matching route -- skipped
    >>> Route('web', handlers.BaseHandler())({'REL_REQUEST_URI': '/other/test.example.com', 'SCRIPT_NAME': ''}, False)
    """

    # match upto next / or ? or end
    SLASH_QUERY_LOOKAHEAD ='(?=/|$|\?)'


    def __init__(self, regex, handler, coll_group = 0, lookahead = SLASH_QUERY_LOOKAHEAD):
        self.path = regex
        self.regex = re.compile(regex + lookahead)
        self.handler = handler
        # collection id from regex group (default 0)
        self.coll_group = coll_group


    def __call__(self, env, use_abs_prefix):
        request_uri =  env['REL_REQUEST_URI']
        matcher = self.regex.match(request_uri[1:])
        if not matcher:
            return None

        rel_prefix = matcher.group(0)

        if rel_prefix:
            wb_prefix = env['SCRIPT_NAME'] + '/' + rel_prefix + '/'
            wb_url_str = request_uri[len(rel_prefix) + 2:] # remove the '/' + rel_prefix part of uri
        else:
            wb_prefix = env['SCRIPT_NAME'] + '/'
            wb_url_str = request_uri[1:] # the request_uri is the wb_url, since no coll

        coll = matcher.group(self.coll_group)

        wbrequest = WbRequest(env,
                              request_uri = request_uri,
                              coll = coll,
                              wb_url_str = wb_url_str,
                              wb_prefix = wb_prefix,
                              use_abs_prefix = use_abs_prefix,
                              wburl_class = self.handler.get_wburl_type())


        # Allow for setup of additional filters
        self._add_filters(wbrequest, matcher)

        return self._handle_request(wbrequest)

    def _add_filters(self, wbrequest, matcher):
        pass

    def _handle_request(self, wbrequest):
        return self.handler(wbrequest)

    def __str__(self):
        #return '* ' + self.regex_str + ' => ' + str(self.handler)
        return str(self.handler)


#=================================================================
# ReferRedirect -- redirect urls that have 'fallen through' based on the referrer settings
#=================================================================
class ReferRedirect:

    """
    >>> ReferRedirect('http://localhost:8080/').match_prefixs
    ['http://localhost:8080/']

    >>> ReferRedirect(['http://example:9090/']).match_prefixs
    ['http://example:9090/']

    >>> test_redir('http://localhost:8080/', '/other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
    'http://localhost:8080/coll/20131010/http://example.com/path/other.html'

    >>> test_redir('http://localhost:8080/', '/../other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
    'http://localhost:8080/coll/20131010/http://example.com/other.html'

    >>> test_redir('http://localhost:8080/', '/../../other.html', 'http://localhost:8080/coll/20131010/http://example.com/index.html')
    'http://localhost:8080/coll/20131010/http://example.com/other.html'

    >>> test_redir('http://example:8080/', '/other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
    False

    # With custom SCRIPT_NAME
    >>> test_redir('http://localhost:8080/', '/../other.html', 'http://localhost:8080/extra/coll/20131010/http://example.com/path/page.html', '/extra')
    'http://localhost:8080/extra/coll/20131010/http://example.com/other.html'

    # With custom SCRIPT_NAME, bad match
    >>> test_redir('http://localhost:8080/', '/../other.html', 'http://localhost:8080/extra/coll/20131010/http://example.com/path/page.html', '/extr')
    False

    """

    def __init__(self, match_prefixs):
        if isinstance(match_prefixs, list):
            self.match_prefixs = match_prefixs
        else:
            self.match_prefixs = [match_prefixs]


    def __call__(self, wbrequest):
        if wbrequest.referrer is None:
            return None

        if not any (wbrequest.referrer.startswith(i) for i in self.match_prefixs):
            return None

        ref_split = urlparse.urlsplit(wbrequest.referrer)

        path = ref_split.path
        script_name = wbrequest.env['SCRIPT_NAME']

        if not path.startswith(script_name):
            return None

        ref_path = path[len(script_name) + 1:].split('/', 1)

        # No match on any exception
        try:
            rewriter = UrlRewriter(ref_path[1], script_name + '/' + ref_path[0] + '/')
        except Exception:
            return None

        rel_request_uri = wbrequest.request_uri[1:]

        #ref_wb_url = archiveurl('/' + ref_path[1])
        #ref_wb_url.url = urlparse.urljoin(ref_wb_url.url, wbrequest.request_uri[1:])
        #ref_wb_url.url = ref_wb_url.url.replace('../', '')

        #final_url = urlparse.urlunsplit((ref_split.scheme, ref_split.netloc, ref_path[0] + str(ref_wb_url), '', ''))
        final_url = urlparse.urlunsplit((ref_split.scheme, ref_split.netloc, rewriter.rewrite(rel_request_uri), '', ''))

        return WbResponse.redir_response(final_url)


import utils
if __name__ == "__main__" or utils.enable_doctests():

    import handlers

    def test_redir(match_host, request_uri, referrer, script_name = ''):
        env = {'REL_REQUEST_URI': request_uri, 'HTTP_REFERER': referrer, 'SCRIPT_NAME': script_name}

        redir = ReferRedirect(match_host)
        req = WbRequest.from_uri(request_uri, env)
        rep = redir(req)
        if not rep:
            return False

        return rep.status_headers.get_header('Location')


    import doctest
    doctest.testmod()


