from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import BufferWARCWriter
from warcio.timeutils import datetime_to_http_date

from pywb.rewrite.content_rewriter import RewriteInfo
from pywb.rewrite.default_rewriter import DefaultRewriter
from pywb.rewrite.header_rewriter import DefaultHeaderRewriter
from pywb.rewrite.url_rewriter import UrlRewriter

from datetime import datetime, timezone

from io import BytesIO


class TestHeaderRewriter(object):
    @classmethod
    def setup_class(cls):
        cls.urlrewriter = UrlRewriter('20171226/http://example.com/', '/warc/')
        cls.default_rewriter = DefaultRewriter()

    @classmethod
    def get_rwinfo(cls, record):
        return RewriteInfo(record=record,
                           content_rewriter=cls.default_rewriter,
                           url_rewriter=cls.urlrewriter, cookie_rewriter=None)

    @classmethod
    def do_rewrite(cls, statusline, headers):
        writer = BufferWARCWriter()

        http_headers = StatusAndHeaders(statusline, headers, protocol='HTTP/1.0')

        record = writer.create_warc_record('http://example.com/', 'response',
                                           http_headers=http_headers)

        return cls.get_rwinfo(record)

    def test_header_rewrite_200_response(self):
        headers = [('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
                   ('Content-Length', '5'),
                   ('Content-Type', 'text/html;charset=UTF-8')]

        res = """\
HTTP/1.0 200 OK\r\n\
X-Archive-Orig-Date: Fri, 03 Jan 2014 03:03:21 GMT\r\n\
X-Archive-Orig-Content-Length: 5\r\n\
Content-Type: text/html;charset=UTF-8\r\n\
"""
        rwinfo = self.do_rewrite('200 OK', headers)
        http_headers = DefaultHeaderRewriter(rwinfo)()
        assert str(http_headers) == res

        assert rwinfo.text_type == None
        assert rwinfo.charset == None

    def test_header_rewrite_redirect(self):
        headers = [('Connection', 'close'),
                   ('Location', 'http://example.com/other.html')]

        res = """\
HTTP/1.0 302 Redirect\r\n\
X-Archive-Orig-Connection: close\r\n\
Location: /warc/20171226/http://example.com/other.html\r\n\
"""
        rwinfo = self.do_rewrite('302 Redirect', headers)
        http_headers = DefaultHeaderRewriter(rwinfo)()
        assert str(http_headers) == res

        assert rwinfo.text_type == None
        assert rwinfo.charset == None

    def test_header_rewrite_gzipped(self):
        headers = [('Content-Length', '199999'),
                   ('Content-Type', 'text/javascript'),
                   ('Content-Encoding', 'gzip'),
                   ('Transfer-Encoding', 'chunked')]

        rwinfo = self.do_rewrite('200 OK', headers)

        # Content-Encoding, Content-Length not yet rewritten
        res = """\
HTTP/1.0 200 OK\r\n\
Content-Length: 199999\r\n\
Content-Type: text/javascript\r\n\
Content-Encoding: gzip\r\n\
X-Archive-Orig-Transfer-Encoding: chunked\r\n\
"""
        http_headers = DefaultHeaderRewriter(rwinfo)()
        assert str(http_headers) == res

        assert rwinfo.text_type == 'js'
        assert rwinfo.charset == None

        # access stream
        stream = rwinfo.content_stream

        # Content-Encoding, Content-Length rewritten now
        res = """\
HTTP/1.0 200 OK\r\n\
X-Archive-Orig-Content-Length: 199999\r\n\
Content-Type: text/javascript\r\n\
X-Archive-Orig-Content-Encoding: gzip\r\n\
X-Archive-Orig-Transfer-Encoding: chunked\r\n\
"""
        http_headers = DefaultHeaderRewriter(rwinfo)()
        assert str(http_headers) == res

    def test_header_rewrite_binary(self):
        headers = [('Content-Length', '200000'),
                   ('Content-Type', 'image/png'),
                   ('Set-Cookie', 'foo=bar; Path=/; abc=123; Path=/path.html'),
                   ('Content-Encoding', 'gzip'),
                   ('Transfer-Encoding', 'chunked'),
                   ('X-Custom', 'test'),
                   ('Status', '200')]

        rwinfo = self.do_rewrite('200 OK', headers)
        http_headers = DefaultHeaderRewriter(rwinfo)()

        assert(('Content-Length', '200000')) in http_headers.headers
        assert(('Content-Type', 'image/png')) in http_headers.headers

        assert(('Set-Cookie', 'foo=bar; Path=/warc/20171226/http://example.com/') in http_headers.headers)
        assert(('Set-Cookie', 'abc=123; Path=/warc/20171226/http://example.com/path.html') in http_headers.headers)

        assert(('Content-Encoding', 'gzip') in http_headers.headers)
        assert(('X-Archive-Orig-Transfer-Encoding', 'chunked') in http_headers.headers)
        assert(('X-Custom', 'test') in http_headers.headers)

        assert(('X-Archive-Orig-Status', '200') in http_headers.headers)

        assert(len(http_headers.headers) == 8)

        assert rwinfo.text_type == None
        assert rwinfo.charset == None



def _test_head_data(headers, status='200 OK', rewriter=None):
    rewritten = headerrewriter.rewrite(StatusAndHeaders(status, headers),
                                       rewriter,
                                       rewriter.get_cookie_rewriter())
    return rewritten.status_headers



def _test_cookie_headers():
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
                     ('Expires', datetime_to_http_date(datetime.now(timezone.utc))),
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


def _test_proxy_default():
    res = _test_proxy_headers()

    assert res.get_header('X-Archive-Orig-Cache-Control') != None
    assert res.get_header('X-Archive-Orig-Expires') != None
    assert res.get_header('X-Archive-Orig-ETag') != None


def _test_proxy_pass():
    res = _test_proxy_headers('pass')

    assert res.get_header('Cache-Control') == 'max-age=10'
    assert res.get_header('Expires') != None
    assert res.get_header('ETag') != None


def _test_proxy_set_age():
    res = _test_proxy_headers('600')

    assert res.get_header('Cache-Control') == 'max-age=600'
    assert res.get_header('Expires') != None
    assert res.get_header('ETag') == None


def _test_proxy_zero():
    res = _test_proxy_headers('0')

    assert res.get_header('Cache-Control') == 'no-cache; no-store'
    assert res.get_header('Expires') == None
    assert res.get_header('ETag') == None


def _test_proxy_not_num():
    res = _test_proxy_headers('blah')

    assert res.get_header('Cache-Control') == 'no-cache; no-store'
    assert res.get_header('Expires') == None
    assert res.get_header('ETag') == None


if __name__ == "__main__":
    import doctest
    doctest.testmod()


