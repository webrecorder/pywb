"""
# Test WbRequest parsed via a Route
# route with relative path, print resulting wbrequest
>>> _test_route_req(Route('web', WbUrlHandler()), {'REL_REQUEST_URI': '/web/test.example.com', 'SCRIPT_NAME': ''})
{'coll': 'web',
 'request_uri': '/web/test.example.com',
 'wb_prefix': '/web/',
 'wb_url': ('latest_replay', '', '', 'http://test.example.com', 'http://test.example.com')}


# route with absolute path, running at script /my_pywb, print resultingwbrequest
>>> _test_route_req(Route('web', WbUrlHandler()), {'REL_REQUEST_URI': '/web/2013im_/test.example.com', 'SCRIPT_NAME': '/my_pywb', 'HTTP_HOST': 'localhost:8081', 'wsgi.url_scheme': 'https'}, True)
{'coll': 'web',
 'request_uri': '/web/2013im_/test.example.com',
 'wb_prefix': 'https://localhost:8081/my_pywb/web/',
 'wb_url': ('replay', '2013', 'im_', 'http://test.example.com', '2013im_/http://test.example.com')}

# route with no collection
>>> _test_route_req(Route('', BaseHandler()), {'REL_REQUEST_URI': 'http://example.com', 'SCRIPT_NAME': '/pywb'})
{'coll': '',
 'request_uri': 'http://example.com',
 'wb_prefix': '/pywb/',
 'wb_url': None}

# not matching route -- skipped
>>> _test_route_req(Route('web', BaseHandler()), {'REL_REQUEST_URI': '/other/test.example.com', 'SCRIPT_NAME': ''})

# Test Refer Redirects
>>> _test_redir('http://localhost:8080/', '/diff_path/other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
'http://localhost:8080/coll/20131010/http://example.com/diff_path/other.html'

>>> _test_redir('http://localhost:8080/', '/../other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
'http://localhost:8080/coll/20131010/http://example.com/other.html'

>>> _test_redir('http://localhost:8080/', '/../../other.html', 'http://localhost:8080/coll/20131010/http://example.com/index.html')
'http://localhost:8080/coll/20131010/http://example.com/other.html'

# Custom collection
>>> _test_redir('http://localhost:8080/', '/other.html', 'http://localhost:8080/complex/123/20131010/http://example.com/path/page.html', coll='complex/123')
'http://localhost:8080/complex/123/20131010/http://example.com/other.html'

# With timestamp included
>>> _test_redir('http://localhost:8080/', '/20131010/other.html', 'http://localhost:8080/coll/20131010/http://example.com/index.html')
'http://localhost:8080/coll/20131010/http://example.com/other.html'

# With timestamp included
>>> _test_redir('http://localhost:8080/', '/20131010/path/other.html', 'http://localhost:8080/coll/20131010/http://example.com/some/index.html')
'http://localhost:8080/coll/20131010/http://example.com/path/other.html'

# Wrong Host
>>> _test_redir('http://example.com:8080/', '/other.html', 'http://localhost:8080/coll/20131010/http://example.com/path/page.html')
False

# Right Host
>>> _test_redir('http://example.com:8080/', '/other.html', 'http://example.com:8080/coll/20131010/http://example.com/path/page.html')
'http://example.com:8080/coll/20131010/http://example.com/other.html'

# With custom SCRIPT_NAME
>>> _test_redir('http://localhost:8080/', '/../other.html', 'http://localhost:8080/extra/coll/20131010/http://example.com/path/page.html', '/extra')
'http://localhost:8080/extra/coll/20131010/http://example.com/other.html'

# With custom SCRIPT_NAME + timestamp
>>> _test_redir('http://localhost:8080/', '/20131010/other.html', 'http://localhost:8080/extra/coll/20131010/http://example.com/path/page.html', '/extra')
'http://localhost:8080/extra/coll/20131010/http://example.com/other.html'

# With custom SCRIPT_NAME, bad match
>>> _test_redir('http://localhost:8080/', '/../other.html', 'http://localhost:8080/extra/coll/20131010/http://example.com/path/page.html', '/extr')
False

# With no collection
>>> _test_redir('http://localhost:8080/', '/other.html', 'http://localhost:8080/2013/http://example.com/path/page.html', coll='')
'http://localhost:8080/2013/http://example.com/other.html'

# With SCRIPT_NAME but no collection
>>> _test_redir('http://localhost:8080/', '/other.html', 'http://localhost:8080/pywb-access/http://example.com/path/page.html', '/pywb-access', coll='')
'http://localhost:8080/pywb-access/http://example.com/other.html'


>>> _test_redir('http://localhost:8080/', '/some/example/other.html', 'http://localhost:8080/user/coll/http://example.com/path/page.html', '/user/coll', coll='')
'http://localhost:8080/user/coll/http://example.com/some/example/other.html'

## Test ensure_rel_uri_set

# Simple test:
>>> ArchivalRouter.ensure_rel_uri_set({'PATH_INFO': '/pywb/example.com'})
'/pywb/example.com'

# Test all unecoded special chars and double-quote
# (double-quote must be encoded but not single quote)
>>> ArchivalRouter.ensure_rel_uri_set({'PATH_INFO': "/pywb/example.com/0~!+$&'()*+,;=:\\\""})
"/pywb/example.com/0~!+$&'()*+,;=:%22"

"""

from pywb.framework.archivalrouter import Route, ReferRedirect, ArchivalRouter
from pywb.framework.basehandlers import BaseHandler, WbUrlHandler

import pprint

from six.moves.urllib.parse import urlsplit

def _test_route_req(route, env, abs_path=False):
    matcher, coll = route.is_handling(env['REL_REQUEST_URI'])
    if not matcher:
        return

    the_router = ArchivalRouter([route], abs_path=abs_path)
    req = the_router.parse_request(route, env, matcher, coll, env['REL_REQUEST_URI'], abs_path)

    varlist = vars(req)
    the_dict = dict((k, varlist[k]) for k in ('request_uri', 'wb_prefix', 'wb_url', 'coll'))
    pprint.pprint(the_dict)


def _test_redir(match_host, request_uri, referrer, script_name='', coll='coll'):
    env = {'REL_REQUEST_URI': request_uri, 'HTTP_REFERER': referrer, 'SCRIPT_NAME': script_name}

    env['HTTP_HOST'] = urlsplit(match_host).netloc

    routes = [Route(coll, WbUrlHandler())]

    the_router = ArchivalRouter(routes)

    redir = ReferRedirect()
    #req = WbRequest.from_uri(request_uri, env)
    rep = redir(env, the_router)
    if not rep:
        return False

    return rep.status_headers.get_header('Location')


if __name__ == "__main__":
    import doctest
    doctest.testmod()
