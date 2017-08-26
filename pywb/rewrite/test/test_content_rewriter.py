from warcio.warcwriter import BufferWARCWriter, GzippingWrapper
from warcio.statusandheaders import StatusAndHeaders

from io import BytesIO

from pywb.warcserver.index.cdxobject import CDXObject
from pywb.utils.canonicalize import canonicalize

from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.default_rewriter import DefaultRewriter

import pytest

@pytest.fixture(params=[{'Content-Type': 'text/html'},
                        {'Content-Type': 'application/xhtml+xml'},
                        {'Content-Type': 'application/octet-stream'},
                        {}],
                ids=['html', 'xhtml', 'octet-stream', 'none'])
def headers(request):
    return request.param


# ============================================================================
class TestContentRewriter(object):
    @classmethod
    def setup_class(self):
        self.content_rewriter = DefaultRewriter()

    def _create_response_record(self, url, headers, payload):
        writer = BufferWARCWriter()

        payload = payload.encode('utf-8')

        http_headers = StatusAndHeaders('200 OK', headers, protocol='HTTP/1.0')

        return writer.create_warc_record(url, 'response',
                                         payload=BytesIO(payload),
                                         length=len(payload),
                                         http_headers=http_headers)

    def rewrite_record(self, headers, content, ts, url='http://example.com/',
                       prefix='http://localhost:8080/prefix/'):

        record = self._create_response_record(url, headers, content)

        wburl = WbUrl(ts + '/' + url)
        url_rewriter = UrlRewriter(wburl, prefix)

        cdx = CDXObject()
        cdx['url'] = url
        cdx['timestamp'] = ts
        cdx['urlkey'] = canonicalize(url)

        return self.content_rewriter(record, url_rewriter, None, cdx=cdx)

    def test_rewrite_html(self, headers):
        content = '<html><body><a href="http://example.com/"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        # if octet-stream, don't attempt to rewrite (only for JS/CSS)
        if headers.get('Content-Type') == 'application/octet-stream':
            exp_rw = False
            exp_ct = ('Content-Type', 'application/octet-stream')
            exp = content

        else:
            exp_rw = True
            exp_ct = ('Content-Type', 'text/html')
            exp = '<html><body><a href="http://localhost:8080/prefix/201701/http://example.com/"></a></body></html>'

        assert exp_ct in headers.headers
        assert is_rw == exp_rw
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_html_change_mime_keep_charset(self):
        headers = {'Content-Type': 'application/xhtml+xml; charset=UTF-8'}
        content = '<html><body><a href="http://example.com/"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        exp = '<html><body><a href="http://localhost:8080/prefix/201701/http://example.com/"></a></body></html>'
        assert is_rw
        assert ('Content-Type', 'text/html; charset=UTF-8') in headers.headers
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_html_js_mod(self, headers):
        content = '<html><body><a href="http://example.com/"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_')

        assert ('Content-Type', 'text/html') in headers.headers

        exp = '<html><body><a href="http://localhost:8080/prefix/201701/http://example.com/"></a></body></html>'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_js_mod(self, headers):
        content = 'function() { location.href = "http://example.com/"; }'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_')

        assert ('Content-Type', 'text/javascript') in headers.headers

        exp = 'function() { WB_wombat_location.href = "http://example.com/"; }'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_cs_mod(self, headers):
        content = '.foo { background: url(http://localhost:8080/prefix/201701cs_/http://example.com/) }'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701cs_')

        assert ('Content-Type', 'text/css') in headers.headers

        exp = '.foo { background: url(http://localhost:8080/prefix/201701cs_/http://example.com/) }'

        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_js_mod_alt_ct(self):
        headers = {'Content-Type': 'application/x-javascript'}
        content = 'function() { location.href = "http://example.com/"; }'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_')

        assert ('Content-Type', 'application/x-javascript') in headers.headers

        exp = 'function() { WB_wombat_location.href = "http://example.com/"; }'
        assert b''.join(gen).decode('utf-8') == exp

    def test_binary_no_content_type(self):
        headers = {}
        content = '\x11\x12\x13\x14'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        assert ('Content-Type', 'application/octet-stream') not in headers.headers

        assert is_rw == False

    def test_binary_octet_stream(self):
        headers = {'Content-Type': 'application/octet-stream'}
        content = '\x11\x12\x13\x14'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        assert ('Content-Type', 'application/octet-stream') in headers.headers

        assert is_rw == False

    def test_rewrite_json(self):
        headers = {'Content-Type': 'application/json'}
        content = '/**/ jQuery_ABC({"foo": "bar"});'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://example.com/path/file?callback=jQuery_DEF')

        assert ('Content-Type', 'application/json') in headers.headers

        exp = 'jQuery_DEF({"foo": "bar"});'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_js_as_json(self):
        headers = {'Content-Type': 'text/javascript'}
        content = '/**/ jQuery_ABC({"foo": "bar"});'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://example.com/path/file.json?callback=jQuery_DEF')

        assert ('Content-Type', 'text/javascript') in headers.headers

        exp = 'jQuery_DEF({"foo": "bar"});'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_js_as_json_jquery(self):
        headers = {'Content-Type': 'application/x-javascript'}
        content = '/**/ jQuery_ABC({"foo": "bar"});'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://example.com/path/file?callback=jQuery_DEF')

        # content-type unchanged
        assert ('Content-Type', 'application/x-javascript') in headers.headers

        exp = 'jQuery_DEF({"foo": "bar"});'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_js_not_json(self):
        # callback not set
        headers = {}
        content = '/**/ jQuery_ABC({"foo": "bar"});'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://example.com/path/file')

        assert ('Content-Type', 'text/javascript') in headers.headers

        assert b''.join(gen).decode('utf-8') == content



