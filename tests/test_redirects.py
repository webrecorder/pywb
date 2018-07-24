from .base_config_test import BaseConfigTest, CollsDirMixin, fmod

from warcio.timeutils import timestamp_to_iso_date
from warcio.warcwriter import WARCWriter
from warcio.statusandheaders import StatusAndHeaders
from io import BytesIO
import os

from pywb.manager.manager import main as wb_manager


# ============================================================================
class TestRedirects(CollsDirMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestRedirects, cls).setup_class('config_test.yaml')

    def create_redirect_record(self, url, redirect_url, timestamp):
        warc_headers = {}
        warc_headers['WARC-Date'] = timestamp_to_iso_date(timestamp)

        #content = 'Redirect to ' + redirect_url
        content = ''
        payload = content.encode('utf-8')
        headers_list = [('Content-Length', str(len(payload))),
                        ('Location', redirect_url)
                       ]

        http_headers = StatusAndHeaders('301 Permanent Redirect', headers_list, protocol='HTTP/1.0')

        rec = self.writer.create_warc_record(url, 'response',
                                             payload=BytesIO(payload),
                                             length=len(payload),
                                             http_headers=http_headers,
                                             warc_headers_dict=warc_headers)

        self.writer.write_record(rec)

        return rec

    def create_response_record(self, url, timestamp, text):
        payload = text.encode('utf-8')

        warc_headers = {}
        warc_headers['WARC-Date'] = timestamp_to_iso_date(timestamp)

        headers_list = [('Content-Length', str(len(payload)))]

        http_headers = StatusAndHeaders('200 OK', headers_list, protocol='HTTP/1.0')

        rec = self.writer.create_warc_record(url, 'response',
                                             payload=BytesIO(payload),
                                             length=len(payload),
                                             http_headers=http_headers,
                                             warc_headers_dict=warc_headers)

        self.writer.write_record(rec)
        return rec

    def create_revisit_record(self, original, url, redirect_url, timestamp):
        warc_headers = {}
        warc_headers['WARC-Date'] = timestamp_to_iso_date(timestamp)

        headers_list = [('Content-Length', '0'),
                        ('Location', redirect_url)]

        http_headers = StatusAndHeaders('302 Temp Redirect', headers_list, protocol='HTTP/1.0')

        rec = self.writer.create_revisit_record(url,
                                                digest=original.rec_headers['WARC-Payload-Digest'],
                                                refers_to_uri=url,
                                                refers_to_date=original.rec_headers['WARC-Date'],
                                                warc_headers_dict=warc_headers,
                                                http_headers=http_headers)

        self.writer.write_record(rec)

    def test_init_1(self):
        filename = os.path.join(self.root_dir, 'redir.warc.gz')
        with open(filename, 'wb') as fh:
            self.writer = WARCWriter(fh, gzip=True)

            redirect = self.create_redirect_record('http://example.com/', 'https://example.com/', '201806026101112')
            redirect = self.create_redirect_record('https://example.com/', 'https://www.example.com/', '201806026101112')
            response = self.create_response_record('https://www.example.com/', '201806026101112', 'Some Text')

        wb_manager(['init', 'redir'])

        wb_manager(['add', 'redir', filename])

        assert os.path.isfile(os.path.join(self.root_dir, self.COLLS_DIR, 'redir', 'indexes', 'index.cdxj'))

    def test_self_redir_1(self, fmod):
        res = self.get('/redir/201806026101112{0}/https://example.com/', fmod)

        assert res.status_code == 200

        assert res.text == 'Some Text'

    def test_redir_init_slash(self):
        filename = os.path.join(self.root_dir, 'redir-slash.warc.gz')
        with open(filename, 'wb') as fh:
            self.writer = WARCWriter(fh, gzip=True)

            response = self.create_response_record('https://www.example.com/sub/path/', '201806026101112', 'Sub Path Data')

            response = self.create_response_record('https://www.example.com/sub/path/?foo=bar', '201806026101112', 'Sub Path Data Q')

        wb_manager(['add', 'redir', filename])

    def test_redir_slash(self, fmod):
        res = self.get('/redir/201806026101112{0}/https://example.com/sub/path', fmod, status=307)

        assert res.headers['Location'].endswith('/redir/201806026101112{0}/https://example.com/sub/path/'.format(fmod))
        res = res.follow()

        assert res.status_code == 200

        assert res.text == 'Sub Path Data'

    def test_redir_slash_with_query(self, fmod):
        res = self.get('/redir/201806026101112{0}/https://example.com/sub/path?foo=bar', fmod, status=307)

        assert res.headers['Location'].endswith('/redir/201806026101112{0}/https://example.com/sub/path/?foo=bar'.format(fmod))
        res = res.follow()

        assert res.status_code == 200

        assert res.text == 'Sub Path Data Q'



