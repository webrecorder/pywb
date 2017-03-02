"""
# WbRequest Tests
# =================
#>>> get_req_from_uri('/save/_embed/example.com/?a=b')
{'wb_url': ('latest_replay', '', '', 'http://_embed/example.com/?a=b', 'http://_embed/example.com/?a=b'), 'coll': 'save', 'wb_prefix': '/save/', 'request_uri': '/save/_embed/example.com/?a=b'}

#>>> get_req_from_uri('/2345/20101024101112im_/example.com/?b=c')
{'wb_url': ('replay', '20101024101112', 'im_', 'http://example.com/?b=c', '20101024101112im_/http://example.com/?b=c'), 'coll': '2345', 'wb_prefix': '/2345/', 'request_uri': '/2345/20101024101112im_/example.com/?b=c'}

#>>> get_req_from_uri('/2010/example.com')
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '2010', 'wb_prefix': '/2010/', 'request_uri': '/2010/example.com'}

# ajax
#>>> get_req_from_uri('', {'REL_REQUEST_URI': '/2010/example.com', 'HTTP_HOST': 'localhost:8080', 'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '2010', 'wb_prefix': '/2010/', 'request_uri': '/2010/example.com'}

#>>> get_req_from_uri('../example.com')
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '', 'wb_prefix': '/', 'request_uri': '../example.com'}

# Abs path
#>>> get_req_from_uri('/2010/example.com', {'wsgi.url_scheme': 'https', 'HTTP_HOST': 'localhost:8080'}, use_abs_prefix = True)
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '2010', 'wb_prefix': 'https://localhost:8080/2010/', 'request_uri': '/2010/example.com'}

# No Scheme, default to http (shouldn't happen per WSGI standard)
#>>> get_req_from_uri('/2010/example.com', {'HTTP_HOST': 'localhost:8080'}, use_abs_prefix = True)
{'wb_url': ('latest_replay', '', '', 'http://example.com', 'http://example.com'), 'coll': '2010', 'wb_prefix': 'http://localhost:8080/2010/', 'request_uri': '/2010/example.com'}

# Referrer extraction
>>> WbUrl(req_from_uri('/web/2010/example.com', {'wsgi.url_scheme': 'http', 'HTTP_HOST': 'localhost:8080', 'HTTP_REFERER': 'http://localhost:8080/web/2011/blah.example.com/'}).extract_referrer_wburl_str()).url
'http://blah.example.com/'

# incorrect referer
>>> req_from_uri('/web/2010/example.com', {'wsgi.url_scheme': 'http', 'HTTP_HOST': 'localhost:8080', 'HTTP_REFERER': 'http://other.example.com/web/2011/blah.example.com/'}).extract_referrer_wburl_str()


# no referer
>>> req_from_uri('/web/2010/example.com', {'wsgi.url_scheme': 'http', 'HTTP_HOST': 'localhost:8080'}).extract_referrer_wburl_str()

# range requests
>>> req_from_uri('/web/2014/example.com', dict(HTTP_RANGE='bytes=10-100')).extract_range()
('http://example.com', 10, 100, True)

>>> req_from_uri('/web/2014/example.com', dict(HTTP_RANGE='bytes=0-')).extract_range()
('http://example.com', 0, '', True)

>>> req_from_uri('/web/www.googlevideo.com/videoplayback?id=123&range=0-65535').extract_range()
('http://www.googlevideo.com/videoplayback?id=123', 0, 65535, False)

>>> req_from_uri('/web/www.googlevideo.com/videoplayback?id=123&range=100-200').extract_range()
('http://www.googlevideo.com/videoplayback?id=123', 100, 200, False)

# invalid range requests
>>> req_from_uri('/web/2014/example.com', dict(HTTP_RANGE='10-20')).extract_range()

>>> req_from_uri('/web/2014/example.com', dict(HTTP_RANGE='A-5')).extract_range()

>>> req_from_uri('/web/www.googlevideo.com/videoplayback?id=123&range=100-').extract_range()

"""


from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter
from warcio.statusandheaders import StatusAndHeaders

from pywb.framework.wbrequestresponse import WbRequest, WbResponse


def get_req_from_uri(request_uri, env={}, use_abs_prefix=False):
    response = req_from_uri(request_uri, env, use_abs_prefix)
    varlist = vars(response)
    the_dict = dict((k, varlist[k]) for k in ('request_uri', 'wb_prefix', 'wb_url', 'coll'))
    #print(the_dict)
    return the_dict

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


def test_req_1():
    res = get_req_from_uri('/save/_embed/example.com/?a=b')

    assert(repr(res['wb_url']) == "('latest_replay', '', '', 'http://_embed/example.com/?a=b', 'http://_embed/example.com/?a=b')")
    assert(res['coll'] == 'save')
    assert(res['wb_prefix'] == '/save/')
    assert(res['request_uri'] == '/save/_embed/example.com/?a=b')

def test_req_2():
    res = get_req_from_uri('/2345/20101024101112im_/example.com/?b=c')

    assert(repr(res['wb_url']) == "('replay', '20101024101112', 'im_', 'http://example.com/?b=c', '20101024101112im_/http://example.com/?b=c')")
    assert(res['coll'] == '2345')
    assert(res['wb_prefix'] == '/2345/')
    assert(res['request_uri'] == '/2345/20101024101112im_/example.com/?b=c')

def test_req_3():
    res = get_req_from_uri('/2010/example.com')

    assert(repr(res['wb_url']) == "('latest_replay', '', '', 'http://example.com', 'http://example.com')")
    assert(res['coll'] == '2010')
    assert(res['wb_prefix'] == '/2010/')
    assert(res['request_uri'] == '/2010/example.com')


def test_req_4():
    # ajax
    res = get_req_from_uri('', {'REL_REQUEST_URI': '/2010/example.com', 'HTTP_HOST': 'localhost:8080', 'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})

    assert(repr(res['wb_url']) == "('latest_replay', '', '', 'http://example.com', 'http://example.com')")
    assert(res['coll'] == '2010')
    assert(res['wb_prefix'] == '/2010/')
    assert(res['request_uri'] == '/2010/example.com')


def test_req_5():
    res = get_req_from_uri('../example.com')

    assert(repr(res['wb_url']) == "('latest_replay', '', '', 'http://example.com', 'http://example.com')")
    assert(res['coll'] == '')
    assert(res['wb_prefix'] == '/')
    assert(res['request_uri'] == '../example.com')



def test_req_6():
    # Abs path
    res = get_req_from_uri('/2010/example.com', {'wsgi.url_scheme': 'https', 'HTTP_HOST': 'localhost:8080'}, use_abs_prefix = True)

    assert(repr(res['wb_url']) == "('latest_replay', '', '', 'http://example.com', 'http://example.com')")
    assert(res['coll'] == '2010')
    assert(res['wb_prefix'] == 'https://localhost:8080/2010/')
    assert(res['request_uri'] == '/2010/example.com')


def test_req_7():
    # No Scheme, default to http (shouldn't happen per WSGI standard)
    res = get_req_from_uri('/2010/example.com', {'HTTP_HOST': 'localhost:8080'}, use_abs_prefix = True)

    assert(repr(res['wb_url']) == "('latest_replay', '', '', 'http://example.com', 'http://example.com')")
    assert(res['coll'] == '2010')
    assert(res['wb_prefix'] == 'http://localhost:8080/2010/')
    assert(res['request_uri'] == '/2010/example.com')





#Response tests

def test_resp_1():
    resp = vars(WbResponse.text_response('Test'))

    expected = {'body': [b'Test'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK',
                headers = [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', '4')])}

    assert(resp == expected)


def test_resp_2():
    resp = vars(WbResponse.bin_stream([b'Test', b'Another'], content_type='text/plain; charset=utf-8', status='404'))

    expected = {'body': [b'Test', b'Another'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '404',
                headers = [('Content-Type', 'text/plain; charset=utf-8')])}

    assert(resp == expected)

def test_resp_3():

    resp = vars(WbResponse.redir_response('http://example.com/otherfile'))

    expected = {'body': [], 'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect',
                 headers = [('Location', 'http://example.com/otherfile'), ('Content-Length', '0')])}

    assert(resp == expected)

def test_resp_4():
    resp = vars(WbResponse.text_response('Test').add_range(10, 4, 100))

    expected = {'body': [b'Test'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '206 Partial Content',
                headers = [ ('Content-Type', 'text/plain; charset=utf-8'),
                  ('Content-Length', '4'),
                  ('Content-Range', 'bytes 10-13/100'),
                  ('Accept-Ranges', 'bytes')])}

    assert(resp == expected)


if __name__ == "__main__":
    import doctest
    doctest.testmod()

