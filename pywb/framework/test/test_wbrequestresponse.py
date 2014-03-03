"""
# WbRequest Tests
# =================
>>> print_req_from_uri('/save/_embed/example.com/?a=b')
{'wb_url': ('latest_replay', '', '', 'http://_embed/example.com/?a=b', 'http://_embed/example.com/?a=b'), 'coll': 'save', 'wb_prefix': '/save/', 'request_uri': '/save/_embed/example.com/?a=b'}

>>> print_req_from_uri('/2345/20101024101112im_/example.com/?b=c')
{'wb_url': ('replay', '20101024101112', 'im_', 'http://example.com/?b=c', '20101024101112im_/http://example.com/?b=c'), 'coll': '2345', 'wb_prefix': '/2345/', 'request_uri': '/2345/20101024101112im_/example.com/?b=c'}

>>> print_req_from_uri('/2010/example.com')
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '2010', 'wb_prefix': '/2010/', 'request_uri': '/2010/example.com'}

>>> print_req_from_uri('../example.com')
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '', 'wb_prefix': '/', 'request_uri': '../example.com'}

# Abs path
>>> print_req_from_uri('/2010/example.com', {'wsgi.url_scheme': 'https', 'HTTP_HOST': 'localhost:8080'}, use_abs_prefix = True)
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '2010', 'wb_prefix': 'https://localhost:8080/2010/', 'request_uri': '/2010/example.com'}

# No Scheme, so stick to relative
>>> print_req_from_uri('/2010/example.com', {'HTTP_HOST': 'localhost:8080'}, use_abs_prefix = True)
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '2010', 'wb_prefix': '/2010/', 'request_uri': '/2010/example.com'}



# WbResponse Tests
# =================
>>> WbResponse.text_response('Test')
{'body': ['Test'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [('Content-Type', 'text/plain')])}

>>> WbResponse.text_stream(['Test', 'Another'], '404')
{'body': ['Test', 'Another'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '404', headers = [('Content-Type', 'text/plain')])}

>>> WbResponse.redir_response('http://example.com/otherfile')
{'body': [], 'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect', headers = [('Location', 'http://example.com/otherfile')])}

"""


from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.utils.statusandheaders import StatusAndHeaders

from pywb.framework.wbrequestresponse import WbRequest, WbResponse


def print_req_from_uri(request_uri, env={}, use_abs_prefix=False):
    response = req_from_uri(request_uri, env, use_abs_prefix)
    varlist = vars(response)
    print str({k: varlist[k] for k in ('request_uri', 'wb_prefix', 'wb_url', 'coll')})


def req_from_uri(request_uri, env={}, use_abs_prefix=False):
    if not request_uri:
        request_uri = env.get('REL_REQUEST_URI')

    parts = request_uri.split('/', 2)

    # Has coll prefix
    if len(parts) == 3:
        rel_prefix = '/' + parts[1] + '/'
        wb_url_str = parts[2]
        coll = parts[1]
    # No Coll Prefix
    elif len(parts) == 2:
        rel_prefix = '/'
        wb_url_str = parts[1]
        coll = ''
    else:
        rel_prefix = '/'
        wb_url_str = parts[0]
        coll = ''

    return WbRequest(env,
                     request_uri=request_uri,
                     rel_prefix=rel_prefix,
                     wb_url_str=wb_url_str,
                     coll=coll,
                     wburl_class=WbUrl,
                     urlrewriter_class=UrlRewriter,
                     use_abs_prefix=use_abs_prefix)


if __name__ == "__main__":
    import doctest
    doctest.testmod()

