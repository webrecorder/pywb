"""
#=================================================================
HTTP Headers Rewriting
#=================================================================

# Text with charset
>>> _test_headers([('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'), ('Content-Length', '5'), ('Content-Type', 'text/html;charset=UTF-8')])
{'charset': 'utf-8',
 'removed_header_dict': {'content-length': '5'},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
  ('X-Archive-Orig-Content-Length', '5'),
  ('Content-Type', 'text/html;charset=UTF-8')]),
 'text_type': 'html'}

# Redirect
>>> _test_headers([('Connection', 'close'), ('Location', '/other.html')], '302 Redirect')
{'charset': None,
 'removed_header_dict': {},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect', headers = [ ('X-Archive-Orig-Connection', 'close'),
  ('Location', '/web/20131010/http://example.com/other.html')]),
 'text_type': None}

# gzip
>>> _test_headers([('Content-Length', '199999'), ('Content-Type', 'text/javascript'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
{'charset': None,
 'removed_header_dict': {'content-encoding': 'gzip',
                         'content-length': '199999',
                         'transfer-encoding': 'chunked'},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Content-Length', '199999'),
  ('Content-Type', 'text/javascript'),
  ('X-Archive-Orig-Content-Encoding', 'gzip'),
  ('X-Archive-Orig-Transfer-Encoding', 'chunked')]),
 'text_type': 'js'}

# Binary -- transfer-encoding rewritten
>>> _test_headers([('Content-Length', '200000'), ('Content-Type', 'image/png'), ('Set-Cookie', 'foo=bar; Path=/;'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked'), ('X-Proxy', 'test')])
{'charset': None,
 'removed_header_dict': {'transfer-encoding': 'chunked'},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('Content-Length', '200000'),
  ('Content-Type', 'image/png'),
  ('Set-Cookie', 'foo=bar; Path=/web/20131010/http://example.com/'),
  ('Content-Encoding', 'gzip'),
  ('X-Archive-Orig-Transfer-Encoding', 'chunked'),
  ('X-Archive-Orig-X-Proxy', 'test')]),
 'text_type': None}

"""



from pywb.rewrite.header_rewriter import HeaderRewriter
from pywb.rewrite.url_rewriter import UrlRewriter
from warcio.statusandheaders import StatusAndHeaders

from warcio.timeutils import datetime_to_http_date
from datetime import datetime

import pprint

urlrewriter = UrlRewriter('20131010/http://example.com/', '/web/')


headerrewriter = HeaderRewriter()

def _test_headers(headers, status='200 OK', rewriter=urlrewriter):
    rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers), rewriter, rewriter.get_cookie_rewriter())
    return pprint.pprint(vars(rewritten))


def _test_head_data(headers, status='200 OK', rewriter=urlrewriter):
    rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers),
                                       rewriter,
                                       rewriter.get_cookie_rewriter())
    return rewritten.status_headers



def test_cookie_headers():
    # cookie, host/origin rewriting
    res = _test_head_data([('Connection', 'close'),
                           ('Set-Cookie', 'foo=bar; Path=/; abc=def; Path=/somefile.html'),
                           ('Host', 'example.com'),
                           ('Origin', 'https://example.com')])

    assert(('Set-Cookie', 'foo=bar; Path=/web/20131010/http://example.com/') in res.headers)
    assert(('Set-Cookie', 'abc=def; Path=/web/20131010/http://example.com/somefile.html') in res.headers)

    assert(('X-Archive-Orig-Connection', 'close') in res.headers)
    assert(('X-Archive-Orig-Host', 'example.com') in res.headers)
    assert(('X-Archive-Orig-Origin', 'https://example.com') in res.headers)



def _make_cache_headers():
    cache_headers = [('Content-Length', '123'),
                     ('Cache-Control', 'max-age=10'),
                     ('Expires', datetime_to_http_date(datetime.now())),
                     ('ETag', '123456')]
    return cache_headers


def _test_proxy_headers(http_cache=None):
    headers = _make_cache_headers()
    status = '200 OK'
    rewriter = UrlRewriter('20131010/http://example.com/', '/pywb/',
                           rewrite_opts={'http_cache': http_cache})

    rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers),
                                       rewriter,
                                       rewriter.get_cookie_rewriter())
    return rewritten.status_headers


def test_proxy_default():
    res = _test_proxy_headers()

    assert res.get_header('X-Archive-Orig-Cache-Control') != None
    assert res.get_header('X-Archive-Orig-Expires') != None
    assert res.get_header('X-Archive-Orig-ETag') != None


def test_proxy_pass():
    res = _test_proxy_headers('pass')

    assert res.get_header('Cache-Control') == 'max-age=10'
    assert res.get_header('Expires') != None
    assert res.get_header('ETag') != None


def test_proxy_set_age():
    res = _test_proxy_headers('600')

    assert res.get_header('Cache-Control') == 'max-age=600'
    assert res.get_header('Expires') != None
    assert res.get_header('ETag') == None


def test_proxy_zero():
    res = _test_proxy_headers('0')

    assert res.get_header('Cache-Control') == 'no-cache; no-store'
    assert res.get_header('Expires') == None
    assert res.get_header('ETag') == None


def test_proxy_not_num():
    res = _test_proxy_headers('blah')

    assert res.get_header('Cache-Control') == 'no-cache; no-store'
    assert res.get_header('Expires') == None
    assert res.get_header('ETag') == None


if __name__ == "__main__":
    import doctest
    doctest.testmod()


