"""
#=================================================================
HTTP Headers Rewriting
#=================================================================

# Text with charset
>>> _test_headers([('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'), ('Content-Length', '5'), ('Content-Type', 'text/html;charset=UTF-8')])
{'charset': 'utf-8',
 'removed_header_dict': {},
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

# cookie, host/origin rewriting
>>> _test_headers([('Connection', 'close'), ('Set-Cookie', 'foo=bar; Path=/; abc=def; Path=somefile.html'), ('Host', 'example.com'), ('Origin', 'https://example.com')])
{'charset': None,
 'removed_header_dict': {},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Connection', 'close'),
  ('Set-Cookie', 'foo=bar; Path=/web/20131010/http://example.com/'),
  ( 'Set-Cookie',
    'abc=def; Path=/web/20131010/http://example.com/somefile.html'),
  ('X-Archive-Orig-Host', 'example.com'),
  ('X-Archive-Orig-Origin', 'https://example.com')]),
 'text_type': None}



# gzip
>>> _test_headers([('Content-Length', '199999'), ('Content-Type', 'text/javascript'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
{'charset': None,
 'removed_header_dict': {'content-encoding': 'gzip',
                         'transfer-encoding': 'chunked'},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('X-Archive-Orig-Content-Length', '199999'),
  ('Content-Type', 'text/javascript'),
  ('X-Archive-Orig-Transfer-Encoding', 'chunked')]),
 'text_type': 'js'}

# Binary -- transfer-encoding rewritten
>>> _test_headers([('Content-Length', '200000'), ('Content-Type', 'image/png'), ('Set-Cookie', 'foo=bar; Path=/;'), ('Content-Encoding', 'gzip'), ('Transfer-Encoding', 'chunked')])
{'charset': None,
 'removed_header_dict': {'transfer-encoding': 'chunked'},
 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK', headers = [ ('Content-Length', '200000'),
  ('Content-Type', 'image/png'),
  ('Set-Cookie', 'foo=bar; Path=/web/20131010/http://example.com/'),
  ('Content-Encoding', 'gzip'),
  ('X-Archive-Orig-Transfer-Encoding', 'chunked')]),
 'text_type': None}

"""



from pywb.rewrite.header_rewriter import HeaderRewriter
from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.utils.statusandheaders import StatusAndHeaders

import pprint

urlrewriter = UrlRewriter('20131010/http://example.com/', '/web/')


headerrewriter = HeaderRewriter()

def _test_headers(headers, status = '200 OK'):
    rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers), urlrewriter, urlrewriter.get_cookie_rewriter())
    return pprint.pprint(vars(rewritten))


if __name__ == "__main__":
    import doctest
    doctest.testmod()


