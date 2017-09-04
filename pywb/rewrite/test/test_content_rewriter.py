from warcio.warcwriter import BufferWARCWriter, GzippingWrapper
from warcio.statusandheaders import StatusAndHeaders

from io import BytesIO

from pywb.warcserver.index.cdxobject import CDXObject
from pywb.utils.canonicalize import canonicalize

from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.default_rewriter import DefaultRewriter

from pywb import get_test_dir
import os
import pytest


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
        self.content_rewriter = DefaultRewriter()

    def _create_response_record(self, url, headers, payload, warc_headers):
        writer = BufferWARCWriter()

        warc_headers = warc_headers or {}

        payload = payload.encode('utf-8')

        http_headers = StatusAndHeaders('200 OK', headers, protocol='HTTP/1.0')

        return writer.create_warc_record(url, 'response',
                                         payload=BytesIO(payload),
                                         length=len(payload),
                                         http_headers=http_headers,
                                         warc_headers_dict=warc_headers)

    def rewrite_record(self, headers, content, ts, url='http://example.com/',
                       prefix='http://localhost:8080/prefix/', warc_headers=None):

        record = self._create_response_record(url, headers, content, warc_headers)

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

        assert b''.join(gen).decode('utf-8') == content

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

    def test_hls_custom_max_bandwidth(self):
        headers = {'Content-Type': 'application/x-mpegURL'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_hls.m3u8'), 'rt') as fh:
            content = fh.read()

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701oe_',
                                                  url='http://example.com/path/master.m3u8',
                                                  warc_headers={'WARC-JSON-Metadata': '{"adaptive_max_bandwidth": 2000000}'})

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

    def test_dash_custom_max_bandwidth(self):
        headers = {'Content-Type': 'application/dash+xml'}
        with open(os.path.join(get_test_dir(), 'text_content', 'sample_dash.mpd'), 'rt') as fh:
            content = fh.read()

        headers, gen, is_rw = self.rewrite_record(headers, content, ts='201701oe_',
                                                  url='http://example.com/path/manifest.mpd',
                                                  warc_headers={'WARC-JSON-Metadata': '{"adaptive_max_bandwidth": 2000000}'})

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



