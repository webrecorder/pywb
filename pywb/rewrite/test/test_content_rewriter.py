#!/usr/bin/env python
# -*- coding: utf-8 -*-

from warcio.warcwriter import BufferWARCWriter, GzippingWrapper
from warcio.statusandheaders import StatusAndHeaders

from io import BytesIO

from pywb.warcserver.index.cdxobject import CDXObject
from pywb.utils.canonicalize import canonicalize

from pywb.utils.io import chunk_encode_iter

from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.default_rewriter import RewriterWithJSProxy

from pywb import get_test_dir

import os
import json
import pytest
import six
import re


# ============================================================================
@pytest.fixture(params=[{'Content-Type': 'text/html'},
                        {'Content-Type': 'application/xhtml+xml'},
                        {'Content-Type': 'application/octet-stream'},
                        {'Content-Type': 'text/plain'},
                        {}],
                ids=['html', 'xhtml', 'octet-stream', 'text', 'none'])
def headers(request):
    return request.param


# ============================================================================
class TestContentRewriter(object):
    @classmethod
    def setup_class(self):
        self.content_rewriter = RewriterWithJSProxy()

    def _create_response_record(self, url, headers, payload, warc_headers):
        writer = BufferWARCWriter()

        warc_headers = warc_headers or {}

        if isinstance(payload, six.text_type):
            payload = payload.encode('utf-8')

        http_headers = StatusAndHeaders('200 OK', headers, protocol='HTTP/1.0')

        return writer.create_warc_record(url, 'response',
                                         payload=BytesIO(payload),
                                         length=len(payload),
                                         http_headers=http_headers,
                                         warc_headers_dict=warc_headers)

    def rewrite_record(self, headers, content, ts, url='http://example.com/',
                       prefix='http://localhost:8080/prefix/', warc_headers=None,
                       request_url=None, is_live=None, use_js_proxy=True, environ=None):

        record = self._create_response_record(url, headers, content, warc_headers)

        wburl = WbUrl(ts + '/' + (request_url or url))

        cdx = CDXObject()
        cdx['url'] = url
        cdx['timestamp'] = ts
        cdx['urlkey'] = canonicalize(url)
        if request_url != url:
            cdx['is_fuzzy'] = '1'
        cdx['is_live'] = is_live

        def insert_func(rule, cdx):
            return ''

        if use_js_proxy:
            rewrite_opts = {}
        else:
            rewrite_opts = {'ua_string': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/10.0 Safari/537.36'}

        url_rewriter = UrlRewriter(wburl, prefix, rewrite_opts=rewrite_opts)

        return self.content_rewriter(record, url_rewriter, cookie_rewriter=None,
                        head_insert_func=insert_func,
                        cdx=cdx,
                        environ=environ)

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

    def test_rewrite_text_utf_8_long(self):
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        exp = u'éeé' * 3277
        content = exp.encode('utf-8')

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        assert is_rw == False
        assert ('Content-Type', 'text/html; charset=utf-8') in headers.headers
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_html_utf_8(self):
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        content = u'<html><body><a href="http://éxample.com/tésté"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        exp = '<html><body><a href="http://localhost:8080/prefix/201701/http://%C3%A9xample.com/t%C3%A9st%C3%A9"></a></body></html>'
        assert is_rw
        assert ('Content-Type', 'text/html; charset=utf-8') in headers.headers
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_html_ignore_bom(self):
        headers = {'Content-Type': 'text/html'}
        content = u'\ufeff\ufeff\ufeff<!DOCTYPE html>\n<head>\n<a href="http://example.com"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        exp = '\ufeff\ufeff\ufeff<!DOCTYPE html>\n<head>\n<a href="http://localhost:8080/prefix/201701/http://example.com"></a></body></html>'
        assert is_rw
        assert ('Content-Type', 'text/html') in headers.headers
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_html_utf_8_anchor(self):
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        content = u'<html><body><a href="#éxample-tésté"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        exp = u'<html><body><a href="#éxample-tésté"></a></body></html>'
        assert is_rw
        assert ('Content-Type', 'text/html; charset=utf-8') in headers.headers
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_html_other_encoding(self):
        headers = {'Content-Type': 'text/html; charset=latin-1'}
        content = b'<html><body><a href="http://\xe9xample.com/t\xe9st\xe9"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        exp = '<html><body><a href="http://localhost:8080/prefix/201701/http://%C3%A9xample.com/t%C3%A9st%C3%A9"></a></body></html>'
        assert is_rw
        assert ('Content-Type', 'text/html; charset=latin-1') in headers.headers
        assert b''.join(gen).decode('latin-1') == exp

    def test_rewrite_html_no_encoding_anchor(self):
        headers = {'Content-Type': 'text/html'}
        content = b'<html><body><a href="#\xe9xample-t\xe9st\xe9"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        exp = u'<html><body><a href="#éxample-tésté"></a></body></html>'
        assert is_rw
        assert ('Content-Type', 'text/html') in headers.headers
        assert b''.join(gen).decode('latin-1') == exp

    def test_rewrite_html_js_mod(self, headers):
        content = '<html><body><a href="http://example.com/"></a></body></html>'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_')

        assert ('Content-Type', 'text/html') in headers.headers

        exp = '<html><body><a href="http://localhost:8080/prefix/201701/http://example.com/"></a></body></html>'

        result = b''.join(gen).decode('utf-8')
        assert exp == result

    def test_rewrite_js_mod(self, headers):
        content = 'function() { location.href = "http://example.com/"; }'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_', use_js_proxy=False)

        assert ('Content-Type', 'text/javascript') in headers.headers

        exp = 'function() { WB_wombat_location.href = "http://example.com/"; }'
        result = b''.join(gen).decode('utf-8')

        assert exp == result

    def test_rewrite_js_mod_with_obj_proxy(self, headers):
        content = 'function() { location.href = "http://example.com/"; }'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_', use_js_proxy=True)

        assert ('Content-Type', 'text/javascript') in headers.headers

        exp = 'function() { location.href = "http://example.com/"; }'
        result = b''.join(gen).decode('utf-8')

        assert 'let window ' in result
        assert exp in result

    def test_rewrite_cs_mod(self, headers):
        content = '.foo { background: url(http://localhost:8080/prefix/201701cs_/http://example.com/) }'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701cs_')

        assert ('Content-Type', 'text/css') in headers.headers

        exp = '.foo { background: url(http://localhost:8080/prefix/201701cs_/http://example.com/) }'

        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_js_mod_alt_ct(self):
        headers = {'Content-Type': 'application/x-javascript'}
        content = 'function() { location.href = "http://example.com/"; }'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_', use_js_proxy=False)

        assert ('Content-Type', 'application/x-javascript') in headers.headers

        exp = 'function() { WB_wombat_location.href = "http://example.com/"; }'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_sw_add_headers(self):
        headers = {'Content-Type': 'application/x-javascript'}
        content = "function() { location.href = 'http://example.com/'; }"

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701sw_')

        assert ('Content-Type', 'application/x-javascript') in headers.headers
        assert ('Service-Worker-Allowed', 'http://localhost:8080/prefix/201701mp_/http://example.com/') in headers.headers

        assert "self.importScripts('wombatWorkers.js');" in b''.join(gen).decode('utf-8')

    def test_rewrite_worker(self):
        headers = {'Content-Type': 'application/x-javascript'}
        content = "importScripts('http://example.com/js.js')"

        rwheaders, gen, is_rw = self.rewrite_record(headers, content, ts='201701wkr_')

        assert "self.importScripts('wombatWorkers.js');" in b''.join(gen).decode('utf-8')

    def test_banner_only_no_cookie_rewrite(self):
        headers = {'Set-Cookie': 'foo=bar; Expires=Wed, 13 Jan 2021 22:23:01 GMT; Path=/',
                   'Content-Type': 'text/javascript'}

        content = 'function() { location.href = "http://example.com/"; }'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701bn_')

        assert ('Content-Type', 'text/javascript') in headers.headers
        assert ('Set-Cookie', 'foo=bar; Expires=Wed, 13 Jan 2021 22:23:01 GMT; Path=/') in headers.headers

        exp = 'function() { location.href = "http://example.com/"; }'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_cookies_only_binary_no_content_type(self):
        headers = {'Set-Cookie': 'foo=bar; Expires=Wed, 13 Jan 2021 22:23:01 GMT; Path=/'}
        content = '\x11\x12\x13\x14'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        assert [('Set-Cookie', 'foo=bar; Path=/prefix/201701mp_/http://example.com/')] == headers.headers
        #assert ('Content-Type', 'application/octet-stream') not in headers.headers

        assert is_rw == False

    def test_rewrite_cookies_all_mods(self):
        headers = {'Set-Cookie': 'foo=bar; Expires=Wed, 13 Jan 2021 22:23:01 GMT; Path=/some/path/; HttpOnly'}
        content = '\x11\x12\x13\x14'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        mods = set()
        assert len(headers.headers) == 8
        for name, value in headers.headers:
            assert name == 'Set-Cookie'
            mods.add(re.search('Path=/prefix/201701([^/]+)', value).group(1))

        assert mods == {'mp_', 'cs_', 'js_', 'im_', 'oe_', 'if_', 'sw_', 'wkrf_'}
        assert is_rw == False

    def test_rewrite_http_cookie_no_all_mods_no_slash(self):
        headers = {'Set-Cookie': 'foo=bar; Expires=Wed, 13 Jan 2021 22:23:01 GMT; Path=/some/path; HttpOnly'}
        content = 'abcdefg'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        assert len(headers.headers) == 1
        assert headers.headers[0][0] == 'Set-Cookie'

    def test_rewrite_http_cookie_no_all_mods_wrong_mod(self):
        headers = {'Set-Cookie': 'foo=bar; Expires=Wed, 13 Jan 2021 22:23:01 GMT; Path=/some/path/; HttpOnly'}
        content = 'abcdefg'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701id_')

        assert len(headers.headers) == 1
        assert headers.headers[0][0] == 'Set-Cookie'

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

    def test_binary_wrong_content_type_html(self):
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        content = b'\xe9\x11\x12\x13\x14'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        assert ('Content-Type', 'text/html; charset=utf-8') in headers.headers

        assert is_rw == False
        assert b''.join(gen) == content

    def test_binary_wrong_content_type_html_rw(self):
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        content = b'Hello <a href="/foo.html">link</a>'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        assert ('Content-Type', 'text/html; charset=utf-8') in headers.headers

        assert is_rw
        assert b''.join(gen) == b'Hello <a href="/prefix/201701/http://example.com/foo.html">link</a>'

    def test_binary_wrong_content_type_css(self):
        headers = {'Content-Type': 'text/css; charset=utf-8'}
        content = b'\xe9\x11\x12\x13\x14'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701cs_')

        assert ('Content-Type', 'text/css; charset=utf-8') in headers.headers

        assert is_rw == True
        assert b''.join(gen) == content

    def test_binary_dechunk(self):
        headers = {'Content-Type': 'application/octet-stream',
                   'Transfer-Encoding': 'chunked'}

        content = b''.join(chunk_encode_iter([b'ABCD'] * 10)).decode('utf-8')
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        exp = ''.join(['ABCD'] * 10)
        assert b''.join(gen).decode('utf-8') == exp

        assert is_rw == False

        assert ('Transfer-Encoding', 'chunked') not in headers.headers

    def test_binary_dechunk_not_actually_chunked(self):
        headers = {'Content-Type': 'application/octet-stream',
                   'Transfer-Encoding': 'chunked'}

        content = ''.join(['ABCD'] * 10)
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        exp = ''.join(['ABCD'] * 10)
        assert b''.join(gen).decode('utf-8') == exp

        assert is_rw == False

        assert ('Transfer-Encoding', 'chunked') not in headers.headers

    @pytest.mark.importorskip('brotli')
    def test_brotli_accepted_no_change(self):
        import brotli
        content = brotli.compress('ABCDEFG'.encode('utf-8'))

        headers = {'Content-Type': 'application/octet-stream',
                   'Content-Encoding': 'br',
                   'Content-Length': str(len(content))
                  }

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_',
                                                  environ={'HTTP_ACCEPT_ENCODING': 'gzip, deflate, br'})

        assert headers['Content-Encoding'] == 'br'
        assert headers['Content-Length'] == str(len(content))

        assert brotli.decompress(b''.join(gen)).decode('utf-8') == 'ABCDEFG'

    @pytest.mark.importorskip('brotli')
    def test_brotli_not_accepted_auto_decode(self):
        import brotli
        content = brotli.compress('ABCDEFG'.encode('utf-8'))

        headers = {'Content-Type': 'application/octet-stream',
                   'Content-Encoding': 'br',
                   'Content-Length': str(len(content))
                  }

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_')

        assert 'Content-Encoding' not in headers
        assert 'Content-Length' not in headers
        assert headers['X-Archive-Orig-Content-Encoding'] == 'br'

        assert b''.join(gen).decode('utf-8') == 'ABCDEFG'

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

    def test_rewrite_js_as_json_generic_jsonp(self):
        headers = {'Content-Type': 'application/json'}
        content = '/*abc*/ jsonpCallbackABCDEF({"foo": "bar"});'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://example.com/path/file?callback=jsonpCallback12345')

        # content-type unchanged
        assert ('Content-Type', 'application/json') in headers.headers

        exp = 'jsonpCallback12345({"foo": "bar"});'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_js_as_json_generic_jsonp_multiline_comment(self):
        headers = {'Content-Type': 'application/json'}
        content = """\
// A comment
// Another?
jsonpCallbackABCDEF({"foo": "bar"});"""

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://example.com/path/file?callback=jsonpCallback12345')

        # content-type unchanged
        assert ('Content-Type', 'application/json') in headers.headers

        exp = 'jsonpCallback12345({"foo": "bar"});'
        assert b''.join(gen).decode('utf-8') == exp

    def test_rewrite_js_not_json(self):
        # callback not set
        headers = {}
        content = '/**/ jQuery_ABC({"foo": "bar"});'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://example.com/path/file',
                                                  use_js_proxy=True)

        assert ('Content-Type', 'text/javascript') in headers.headers

        result = b''.join(gen).decode('utf-8')
        assert 'let window' in result
        assert content in result

    def test_rewrite_text_no_type(self):
        headers = {}
        content = 'Just Some Text'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_',
                                                  url='http://example.com/path/file')

        assert headers.headers == []

        assert b''.join(gen).decode('utf-8') == content

    def test_rewrite_text_plain_as_js(self):
        headers = {'Content-Type': 'text/plain'}
        content = '{"Just Some Text"}'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://example.com/path/file')

        assert headers.headers == [('Content-Type', 'text/javascript')]

        result = b''.join(gen).decode('utf-8')
        assert 'let window ' in result
        assert content in result

    def test_custom_fuzzy_replace(self):
        headers = {'Content-Type': 'application/octet-stream'}
        content = '{"ssid":"1234"}'

        actual_url = 'http://facebook.com/ajax/pagelet/generic.php/photoviewerinitpagelet?data="ssid":1234'
        request_url = 'http://facebook.com/ajax/pagelet/generic.php/photoviewerinitpagelet?data="ssid":5678'

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_',
                                                  url=actual_url,
                                                  request_url=request_url)

        assert headers.headers == [('Content-Type', 'application/octet-stream')]

        assert b''.join(gen).decode('utf-8') == '{"ssid":"5678"}'

    def test_rewrite_frameset_frame_content(self):
        """Determines if the content rewriter correctly determines that HTML loaded via a frameset's frame,
        frame's src url is rewritten with the **fr_** rewrite modifier, is content to be rewritten
        """
        headers = {'Content-Type': 'text/html; charset=UTF-8'}
        prefix = 'http://localhost:8080/live/'
        dt = '20190205180554%s'
        content = '<!DOCTYPE html><head><link rel="icon" href="http://r-u-ins.tumblr.com/img/favicon/72.png" ' \
                  'type="image/x-icon"></head>'
        rw_headers, gen, is_rw = self.rewrite_record(headers, content, ts=dt % 'fr_',
                                                     prefix=prefix,
                                                     url='http://r-u-ins.tumblr.com/',
                                                     is_live='1')
        # is_rw should be true indicating the content was rewritten
        assert is_rw
        assert b''.join(gen).decode('utf-8') == content.replace('href="', 'href="%s%s' % (prefix, dt % 'oe_/'))
        assert rw_headers.headers == [('Content-Type', 'text/html; charset=UTF-8')]

    def test_custom_live_only(self):
        headers = {'Content-Type': 'application/json'}
        content = '{"foo":"bar", "dash": {"on": "true"}, "some": ["list"]'

        # is_live
        rw_headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='https://player.vimeo.com/video/123445/config/config?A=B',
                                                  is_live='1')

        # rewritten
        assert b''.join(gen).decode('utf-8') == '{"foo":"bar", "__dash": {"on": "true"}, "some": ["list"]'

        # not is_live
        rw_headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_',
                                                  url='https://player.vimeo.com/video/123445/config/config?A=B')

        assert b''.join(gen).decode('utf-8') == content

    def test_custom_live_js_obj_proxy(self):
        headers = {'Content-Type': 'text/javascript'}
        content = '{"foo":"bar", "dash": {"on": "true"}, "some": ["list"], "hls": {"A": "B"}'

        # is_live
        rw_headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='https://player.vimeo.com/video/123445/config/config?A=B',
                                                  is_live='1',
                                                  use_js_proxy=True)

        # rewritten
        rw_content = '{"foo":"bar", "__dash": {"on": "true"}, "some": ["list"], "__hls": {"A": "B"}'

        assert rw_content in b''.join(gen).decode('utf-8')

    def test_custom_ajax_rewrite(self):
        headers = {'Content-Type': 'application/json',
                   'X-Pywb-Requested-With': 'XMLHttpRequest'}

        content = '{"player":{"value":123,"args":{"id":5}}}'

        rw_headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_',
                                                  url='http://www.youtube.com/watch?v=1234')

        # rewritten
        assert b''.join(gen).decode('utf-8') == '{"player":{"value":123,"args":{"dash":"0","dashmpd":"","id":5}}}'

    def test_hls_default_max(self):
        headers = {'Content-Type': 'application/vnd.apple.mpegurl'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_hls.m3u8'), 'rt') as fh:
            content = fh.read()

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701oe_',
                                                  url='http://example.com/path/master.m3u8')

        assert headers.headers == [('Content-Type', 'application/vnd.apple.mpegurl')]
        filtered = """\
#EXTM3U
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="WebVTT",NAME="English",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,URI="https://example.com/subtitles/"
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=4495000,RESOLUTION=1920x1080,CODECS="avc1.640028, mp4a.40.2",SUBTITLES="WebVTT"
http://example.com/video_6.m3u8
"""

        assert b''.join(gen).decode('utf-8') == filtered

    def test_hls_custom_max_resolution(self):
        headers = {'Content-Type': 'application/x-mpegURL'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_hls.m3u8'), 'rt') as fh:
            content = fh.read()

        metadata = {'adaptive_max_resolution': 921600,
                    'adaptive_max_bandwidth': 2000000}

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701oe_',
                                                  url='http://example.com/path/master.m3u8',
                                                  warc_headers={'WARC-JSON-Metadata': json.dumps(metadata)})

        assert headers.headers == [('Content-Type', 'application/x-mpegURL')]
        filtered = """\
#EXTM3U
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="WebVTT",NAME="English",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,URI="https://example.com/subtitles/"
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2505000,RESOLUTION=1280x720,CODECS="avc1.77.30, mp4a.40.2",SUBTITLES="WebVTT"
http://example.com/video_5.m3u8
"""

        assert b''.join(gen).decode('utf-8') == filtered

    def test_hls_custom_max_bandwidth(self):
        headers = {'Content-Type': 'application/x-mpegURL'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_hls.m3u8'), 'rt') as fh:
            content = fh.read()

        metadata = {'adaptive_max_bandwidth': 2000000}

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701oe_',
                                                  url='http://example.com/path/master.m3u8',
                                                  warc_headers={'WARC-JSON-Metadata': json.dumps(metadata)})

        assert headers.headers == [('Content-Type', 'application/x-mpegURL')]
        filtered = """\
#EXTM3U
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="WebVTT",NAME="English",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,URI="https://example.com/subtitles/"
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1002000,RESOLUTION=640x360,CODECS="avc1.77.30, mp4a.40.2",SUBTITLES="WebVTT"
http://example.com/video_4.m3u8
"""

        assert b''.join(gen).decode('utf-8') == filtered

    def test_dash_default_max(self):
        headers = {'Content-Type': 'application/dash+xml'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_dash.mpd'), 'rt') as fh:
            content = fh.read()

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701oe_',
                                                  url='http://example.com/path/manifest.mpd')

        assert headers.headers == [('Content-Type', 'application/dash+xml')]

        filtered = """\
<?xml version='1.0' encoding='UTF-8'?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" mediaPresentationDuration="PT0H3M1.63S" minBufferTime="PT1.5S" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" type="static">
  <Period duration="PT0H3M1.63S" start="PT0S">
    <AdaptationSet>
      <ContentComponent contentType="video" id="1" />
      <Representation bandwidth="4190760" codecs="avc1.640028" height="1080" id="1" mimeType="video/mp4" width="1920">
        <BaseURL>http://example.com/video-10.mp4</BaseURL>
        <SegmentBase indexRange="674-1149">
          <Initialization range="0-673" />
        </SegmentBase>
      </Representation>
      </AdaptationSet>
    <AdaptationSet>
      <ContentComponent contentType="audio" id="2" />
      <Representation bandwidth="255236" codecs="mp4a.40.2" id="7" mimeType="audio/mp4" numChannels="2" sampleRate="44100">
        <BaseURL>http://example.com/audio-2.mp4</BaseURL>
        <SegmentBase indexRange="592-851">
          <Initialization range="0-591" />
        </SegmentBase>
      </Representation>
      </AdaptationSet>
  </Period>
</MPD>"""
        assert b''.join(gen).decode('utf-8') == filtered


    def test_dash_fb_in_js(self):
        headers = {'Content-Type': 'text/javascript'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_dash.mpd'), 'rt') as fh:
            content = 'dash_manifest:"' + fh.read().encode('unicode-escape').decode('utf-8')

        rep_ids = r'\n",dash_prefetched_representation_ids:["4","5"]'
        content += rep_ids

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://facebook.com/example/dash/manifest.mpd')

        assert headers.headers == [('Content-Type', 'text/javascript')]

        result = b''.join(gen).decode('utf-8')

        # 4, 5 representations removed, replaced with default 1, 7
        assert 'dash_prefetched_representation_ids:["1", "7"]' in result
        assert rep_ids not in result

    def test_dash_fb_in_js_2(self):
        headers = {'Content-Type': 'text/javascript'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_dash.mpd'), 'rt') as fh:
            content = 'dash_manifest:"' + fh.read().encode('unicode-escape').decode('utf-8')

        rep_ids = r'\n","dash_prefetched_representation_ids":["4","5"]'
        content += rep_ids

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701js_',
                                                  url='http://facebook.com/example/dash/manifest.mpd')

        assert headers.headers == [('Content-Type', 'text/javascript')]

        result = b''.join(gen).decode('utf-8')

        # 4, 5 representations removed, replaced with default 1, 7
        assert '"dash_prefetched_representation_ids":["1", "7"]' in result
        assert rep_ids not in result

    def test_dash_custom_max_resolution(self):
        headers = {'Content-Type': 'application/dash+xml'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_dash.mpd'), 'rt') as fh:
            content = fh.read()

        metadata = {'adaptive_max_resolution': 921600,
                    'adaptive_max_bandwidth': 2000000}

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701oe_',
                                                  url='http://example.com/path/manifest.mpd',
                                                  warc_headers={'WARC-JSON-Metadata': json.dumps(metadata)})

        assert headers.headers == [('Content-Type', 'application/dash+xml')]

        filtered = """\
<?xml version='1.0' encoding='UTF-8'?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" mediaPresentationDuration="PT0H3M1.63S" minBufferTime="PT1.5S" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" type="static">
  <Period duration="PT0H3M1.63S" start="PT0S">
    <AdaptationSet>
      <ContentComponent contentType="video" id="1" />
      <Representation bandwidth="2073921" codecs="avc1.4d401f" height="720" id="2" mimeType="video/mp4" width="1280">
        <BaseURL>http://example.com/video-9.mp4</BaseURL>
        <SegmentBase indexRange="708-1183">
          <Initialization range="0-707" />
        </SegmentBase>
      </Representation>
      </AdaptationSet>
    <AdaptationSet>
      <ContentComponent contentType="audio" id="2" />
      <Representation bandwidth="255236" codecs="mp4a.40.2" id="7" mimeType="audio/mp4" numChannels="2" sampleRate="44100">
        <BaseURL>http://example.com/audio-2.mp4</BaseURL>
        <SegmentBase indexRange="592-851">
          <Initialization range="0-591" />
        </SegmentBase>
      </Representation>
      </AdaptationSet>
  </Period>
</MPD>"""

        assert b''.join(gen).decode('utf-8') == filtered


    def test_dash_custom_max_bandwidth(self):
        headers = {'Content-Type': 'application/dash+xml'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_dash.mpd'), 'rt') as fh:
            content = fh.read()

        metadata = {'adaptive_max_bandwidth': 2000000}

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701oe_',
                                                  url='http://example.com/path/manifest.mpd',
                                                  warc_headers={'WARC-JSON-Metadata': json.dumps(metadata)})

        assert headers.headers == [('Content-Type', 'application/dash+xml')]

        filtered = """\
<?xml version='1.0' encoding='UTF-8'?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" mediaPresentationDuration="PT0H3M1.63S" minBufferTime="PT1.5S" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" type="static">
  <Period duration="PT0H3M1.63S" start="PT0S">
    <AdaptationSet>
      <ContentComponent contentType="video" id="1" />
      <Representation bandwidth="869460" codecs="avc1.4d401e" height="480" id="3" mimeType="video/mp4" width="854">
        <BaseURL>http://example.com/video-8.mp4</BaseURL>
        <SegmentBase indexRange="708-1183">
          <Initialization range="0-707" />
        </SegmentBase>
      </Representation>
      </AdaptationSet>
    <AdaptationSet>
      <ContentComponent contentType="audio" id="2" />
      <Representation bandwidth="255236" codecs="mp4a.40.2" id="7" mimeType="audio/mp4" numChannels="2" sampleRate="44100">
        <BaseURL>http://example.com/audio-2.mp4</BaseURL>
        <SegmentBase indexRange="592-851">
          <Initialization range="0-591" />
        </SegmentBase>
      </Representation>
      </AdaptationSet>
  </Period>
</MPD>"""

        assert b''.join(gen).decode('utf-8') == filtered

    def test_json_body_but_mime_html(self):
        headers = {'Content-Type': 'text/html'}
        content = '{"foo":"bar", "dash": {"on": "true"}'
        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701mp_',
                                                  url='http://example.com/path/file.json')
        assert headers.headers == [('Content-Type', 'text/html')]
        result = b''.join(gen).decode('utf-8')
        assert result == content
