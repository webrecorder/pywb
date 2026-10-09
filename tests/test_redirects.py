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

    def create_redirect_record(self, url, redirect_url, timestamp, status='301'):
        warc_headers = {}
        warc_headers['WARC-Date'] = timestamp_to_iso_date(timestamp)

        #content = 'Redirect to ' + redirect_url
        content = ''
        payload = content.encode('utf-8')
        headers_list = [('Content-Length', str(len(payload))),
                        ('Location', redirect_url)
                       ]

        http_headers = StatusAndHeaders(status + ' Redirect', headers_list, protocol='HTTP/1.0')

        rec = self.writer.create_warc_record(url, 'response',
                                             payload=BytesIO(payload),
                                             length=len(payload),
                                             http_headers=http_headers,
                                             warc_headers_dict=warc_headers)

        self.writer.write_record(rec)

        return rec

    def create_response_record(self, url, timestamp, text, extra_headers=None):
        payload = text.encode('utf-8')

        warc_headers = {}
        warc_headers['WARC-Date'] = timestamp_to_iso_date(timestamp)

        headers_list = [('Content-Length', str(len(payload)))]
        if extra_headers:
            headers_list.extend(extra_headers)

        http_headers = StatusAndHeaders('200 OK', headers_list, protocol='HTTP/1.0')

        rec = self.writer.create_warc_record(url, 'response',
                                             payload=BytesIO(payload),
                                             length=len(payload),
                                             http_headers=http_headers,
                                             warc_headers_dict=warc_headers)

        self.writer.write_record(rec)
        return rec

    def create_revisit_record(self, url, timestamp, redirect_url, original_dt):
        warc_headers = {}
        warc_headers['WARC-Date'] = timestamp_to_iso_date(timestamp)

        headers_list = [('Content-Length', '0'),
                        ('Location', redirect_url)]

        http_headers = StatusAndHeaders('302 Temp Redirect', headers_list, protocol='HTTP/1.0')

        rec = self.writer.create_revisit_record(url,
                                                digest='3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ',
                                                refers_to_uri=url,
                                                refers_to_date=original_dt,
                                                warc_headers_dict=warc_headers,
                                                http_headers=http_headers)

        self.writer.write_record(rec)

    def test_init_1(self):
        filename = os.path.join(self.root_dir, 'redir.warc.gz')
        with open(filename, 'wb') as fh:
            self.writer = WARCWriter(fh, gzip=True)

            redirect = self.create_redirect_record('http://example.com/', 'https://example.com/', '20180626101112')
            redirect = self.create_redirect_record('https://example.com/', 'https://www.example.com/', '20180626101112')
            response = self.create_response_record('https://www.example.com/', '20180626101112', 'Some Text')

            revisit = self.create_revisit_record('https://example.com/path', '20190626101112', 'https://example.com/abc', response.rec_headers['WARC-Date'])
            revisit = self.create_revisit_record('https://www.example.com/', '20190626101112', 'https://www.example.com/', response.rec_headers['WARC-Date'])

        wb_manager(['init', 'redir'])

        wb_manager(['add', 'redir', filename])

        assert os.path.isfile(os.path.join(self.root_dir, self.COLLS_DIR, 'redir', 'indexes', 'index.cdxj'))

    def test_self_redir_1(self, fmod):
        res = self.get('/redir/20180626101112{0}/https://example.com/', fmod, status=200)

        assert res.status_code == 200

        assert res.text == 'Some Text'

    def test_redir_init_slash(self):
        filename = os.path.join(self.root_dir, 'redir-slash.warc.gz')
        with open(filename, 'wb') as fh:
            self.writer = WARCWriter(fh, gzip=True)

            response = self.create_response_record('https://www.example.com/sub/path/', '20180626101112', 'Sub Path Data')

            response = self.create_response_record('https://www.example.com/sub/path/?foo=bar', '20180626101112', 'Sub Path Data Q')

        wb_manager(['add', 'redir', filename])

    def test_redir_slash(self, fmod):
        res = self.get('/redir/20180626101112{0}/https://example.com/sub/path', fmod, status=307)

        assert res.headers['Location'].endswith('/redir/20180626101112{0}/https://example.com/sub/path/'.format(fmod))
        res = res.follow()

        assert res.status_code == 200

        assert res.text == 'Sub Path Data'

    def test_redir_slash_with_query(self, fmod):
        res = self.get('/redir/20180626101112{0}/https://example.com/sub/path?foo=bar', fmod, status=307)

        assert res.headers['Location'].endswith('/redir/20180626101112{0}/https://example.com/sub/path/?foo=bar'.format(fmod))
        res = res.follow()

        assert res.status_code == 200

        assert res.text == 'Sub Path Data Q'

    def test_revisit_redirect_302(self, fmod):
        res = self.get('/redir/20170626101112{0}/https://example.com/path', fmod, status=302)
        assert res.headers['Location'].endswith('/redir/20170626101112{0}/https://example.com/abc'.format(fmod))
        assert res.text == ''

    def test_revisit_redirect_skip_self_redir(self, fmod):
        res = self.get('/redir/20190626101112{0}/http://www.example.com/', fmod, status=200)
        assert res.text == 'Some Text'

    def test_init_2(self):
        filename = os.path.join(self.root_dir, 'redir2.warc.gz')
        with open(filename, 'wb') as fh:
            self.writer = WARCWriter(fh, gzip=True)

            redirect = self.create_redirect_record('http://www.example.com/path', 'https://www.example.com/path/', '20191003115920')
            redirect = self.create_redirect_record('https://www.example.com/path/', 'https://www2.example.com/path', '20191003115927', status='302')
            response = self.create_response_record('https://www2.example.com/path', '20191024125646', 'Some Text')
            revisit = self.create_revisit_record('https://www2.example.com/path', '20191024125648', 'https://www2.example.com/path', response.rec_headers['WARC-Date'])

        wb_manager(['init', 'redir2'])

        wb_manager(['add', 'redir2', filename])

        assert os.path.isfile(os.path.join(self.root_dir, self.COLLS_DIR, 'redir2', 'indexes', 'index.cdxj'))

    def test_revisit_redirect_skip_self_redir_2(self, fmod):
        res = self.get('/redir2/20191024125648{0}/http://www2.example.com/path', fmod, status=200)
        assert res.text == 'Some Text'

        res = self.get('/redir2/20191024125648{0}/https://www.example.com/path', fmod, status=200)
        assert res.text == 'Some Text'

    def test_init_refresh(self):
        filename = os.path.join(self.root_dir, 'refresh.warc.gz')
        with open(filename, 'wb') as fh:
            self.writer = WARCWriter(fh, gzip=True)

            # immediate refresh to same url, eg. to upgrade to https
            self.create_response_record('http://refresh.example.com/', '20200101000000', '',
                                        [('Refresh', '0; url=https://refresh.example.com/')])
            self.create_response_record('https://refresh.example.com/', '20200101000005', 'Refresh Target')

            # immediate refresh to another url
            self.create_response_record('http://refresh.example.com/start', '20200101000000', '',
                                        [('Refresh', '0; url=https://refresh.example.com/index.php')])

            # delayed refresh to same url, eg. to periodically reload the page
            self.create_response_record('http://refresh.example.com/reload', '20200101000000', 'Reloading Page',
                                        [('Refresh', '60; url=http://refresh.example.com/reload')])

        wb_manager(['init', 'refresh'])

        wb_manager(['add', 'refresh', filename])

        assert os.path.isfile(os.path.join(self.root_dir, self.COLLS_DIR, 'refresh', 'indexes', 'index.cdxj'))

    def test_refresh_skip_self_refresh(self, fmod):
        res = self.get('/refresh/20200101000000{0}/http://refresh.example.com/', fmod, status=200)
        assert res.text == 'Refresh Target'
        assert 'Refresh' not in res.headers

    def test_refresh_header_rewritten(self, fmod):
        res = self.get('/refresh/20200101000000{0}/http://refresh.example.com/start', fmod, status=200)
        assert res.headers['Refresh'].startswith('0; url=http')
        assert res.headers['Refresh'].endswith('/refresh/20200101000000{0}/https://refresh.example.com/index.php'.format(fmod))

    def test_refresh_delayed_self_refresh_not_skipped(self, fmod):
        res = self.get('/refresh/20200101000000{0}/http://refresh.example.com/reload', fmod, status=200)
        assert res.text == 'Reloading Page'
        assert res.headers['Refresh'].startswith('60; url=http')
        assert res.headers['Refresh'].endswith('/refresh/20200101000000{0}/http://refresh.example.com/reload'.format(fmod))
