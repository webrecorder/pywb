#from gevent import monkey; monkey.patch_all()
import gevent

import pywb.webagg
from pywb.webagg.test.testutils import TempDirTests, LiveServerTests, BaseTestClass, to_path
from pywb.webagg.test.testutils import FakeRedisTests

import os
import webtest

from pytest import raises
from fakeredis import FakeStrictRedis

from pywb.recorder.recorderapp import RecorderApp
from pywb.recorder.redisindexer import WritableRedisIndexer
from pywb.recorder.multifilewarcwriter import PerRecordWARCWriter, MultiFileWARCWriter
from pywb.recorder.filters import ExcludeSpecificHeaders
from pywb.recorder.filters import SkipDupePolicy, WriteDupePolicy, WriteRevisitDupePolicy

from pywb.webagg.utils import MementoUtils

from pywb.cdx.cdxobject import CDXObject

from warcio.statusandheaders import StatusAndHeadersParser
from warcio.bufferedreaders import DecompressingBufferedReader
from warcio.recordloader import ArcWarcRecordLoader
from warcio.archiveiterator import ArchiveIterator

from pywb.warc.cdxindexer import write_cdx_index

from six.moves.urllib.parse import quote, unquote, urlencode
from io import BytesIO
import time
import json

general_req_data = "\
GET {path} HTTP/1.1\r\n\
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\n\
User-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36\r\n\
X-Other: foo\r\n\
Host: {host}\r\n\
Cookie: boo=far\r\n\
\r\n"



class TestRecorder(LiveServerTests, FakeRedisTests, TempDirTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRecorder, cls).setup_class()

        cls.warcs_dir = to_path(cls.root_dir + '/warcs')

        os.makedirs(cls.warcs_dir)

        cls.upstream_url = 'http://localhost:{0}'.format(cls.server.port)

    def _get_dedup_index(self, dupe_policy=WriteRevisitDupePolicy(), user=True):
        if user:
            file_key_template = '{user}:{coll}:warc'
            redis_url = 'redis://localhost/2/{user}:{coll}:cdxj'
        else:
            file_key_template = '{coll}:warc'
            redis_url = 'redis://localhost/2/{coll}:cdxj'

        dedup_index = WritableRedisIndexer(redis_url=redis_url,
                        file_key_template=file_key_template,
                        rel_path_template=self.root_dir + '/warcs/',
                        dupe_policy=dupe_policy)

        return dedup_index

    def _test_warc_write(self, recorder_app, host, path, other_params='', link_url=''):
        url = 'http://' + host + path
        req_url = '/live/resource/postreq?url=' + url + other_params
        testapp = webtest.TestApp(recorder_app)
        resp = testapp.post(req_url, general_req_data.format(host=host, path=path).encode('utf-8'))

        if not recorder_app.write_queue.empty():
            recorder_app._write_one()

        assert resp.headers['WebAgg-Source-Coll'] == 'live'

        if not link_url:
            link_url = unquote(url)

        assert resp.headers['Link'] == MementoUtils.make_link(link_url, 'original')
        assert resp.headers['Memento-Datetime'] != ''

        return resp

    def _test_all_warcs(self, dirname, num):
        coll_dir = to_path(self.root_dir + dirname)
        assert os.path.isdir(coll_dir)

        files = [x for x in os.listdir(coll_dir) if os.path.isfile(os.path.join(coll_dir, x))]
        assert len(files) == num
        assert all(x.endswith('.warc.gz') for x in files)

        self._verify_content_len(coll_dir, files)
        return files, coll_dir

    def _load_resp_req(self, base_path):
        warcs = os.listdir(base_path)
        assert len(warcs) == 1
        warc = warcs[0]

        stored_resp = None
        stored_req = None

        with open(os.path.join(base_path, warc), 'rb') as fh:
            for rec in ArchiveIterator(fh):
                if rec.rec_type == 'response':
                    stored_resp = rec
                elif rec.rec_type == 'request':
                    stored_req = rec

        assert stored_resp is not None
        assert stored_req is not None
        return stored_req, stored_resp

    def _verify_content_len(self, base_dir, files):
        for filename in files:
            filename = os.path.join(base_dir, filename)
            with open(filename, 'rb') as fh:
                for record in ArchiveIterator(fh, no_record_parse=True):
                    assert record.http_headers == None
                    assert int(record.rec_headers.get_header('Content-Length')) == record.length
                    assert record.length == len(record.raw_stream.read())

    def test_record_warc_1(self):
        recorder_app = RecorderApp(self.upstream_url,
                        PerRecordWARCWriter(to_path(self.root_dir + '/warcs/')))

        resp = self._test_warc_write(recorder_app, 'httpbin.org', '/get?foo=bar')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs/', 1)

    def test_record_warc_2(self):
        recorder_app = RecorderApp(self.upstream_url,
                        PerRecordWARCWriter(to_path(self.root_dir + '/warcs/')), accept_colls='live')

        resp = self._test_warc_write(recorder_app, 'httpbin.org', '/get?foo=bar')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs/', 2)

    def test_error_url(self):
        recorder_app = RecorderApp(self.upstream_url + '01',
                        PerRecordWARCWriter(to_path(self.root_dir + '/warcs/')), accept_colls='live')


        testapp = webtest.TestApp(recorder_app)
        resp = testapp.get('/live/resource?url=http://example.com/', status=400)

        assert resp.json['error'] != ''

        self._test_all_warcs('/warcs/', 2)

    def test_record_cookies_header(self):
        base_path = to_path(self.root_dir + '/warcs/cookiecheck/')
        recorder_app = RecorderApp(self.upstream_url,
                        PerRecordWARCWriter(base_path), accept_colls='live')

        resp = self._test_warc_write(recorder_app, 'httpbin.org', '/cookies/set%3Fname%3Dvalue%26foo%3Dbar')
        assert b'HTTP/1.1 302' in resp.body

        buff = BytesIO(resp.body)
        record = ArcWarcRecordLoader().parse_record_stream(buff)
        assert ('Set-Cookie', 'name=value; Path=/') in record.http_headers.headers
        assert ('Set-Cookie', 'foo=bar; Path=/') in record.http_headers.headers

        stored_req, stored_resp = self._load_resp_req(base_path)

        assert ('Set-Cookie', 'name=value; Path=/') in stored_resp.http_headers.headers
        assert ('Set-Cookie', 'foo=bar; Path=/') in stored_resp.http_headers.headers

        assert ('X-Other', 'foo') in stored_req.http_headers.headers
        assert ('Cookie', 'boo=far') in stored_req.http_headers.headers

        self._test_all_warcs('/warcs/cookiecheck/', 1)

    def test_record_cookies_skip_header(self):
        warc_path = to_path(self.root_dir + '/warcs/cookieskip/')
        header_filter = ExcludeSpecificHeaders(['Set-Cookie', 'Cookie'])
        recorder_app = RecorderApp(self.upstream_url,
                         PerRecordWARCWriter(warc_path, header_filter=header_filter),
                            accept_colls='live')

        resp = self._test_warc_write(recorder_app, 'httpbin.org', '/cookies/set%3Fname%3Dvalue%26foo%3Dbar')
        assert b'HTTP/1.1 302' in resp.body

        buff = BytesIO(resp.body)
        record = ArcWarcRecordLoader().parse_record_stream(buff)
        assert ('Set-Cookie', 'name=value; Path=/') in record.http_headers.headers
        assert ('Set-Cookie', 'foo=bar; Path=/') in record.http_headers.headers

        stored_req, stored_resp = self._load_resp_req(warc_path)

        assert ('Set-Cookie', 'name=value; Path=/') not in stored_resp.http_headers.headers
        assert ('Set-Cookie', 'foo=bar; Path=/') not in stored_resp.http_headers.headers

        assert ('X-Other', 'foo') in stored_req.http_headers.headers
        assert ('Cookie', 'boo=far') not in stored_req.http_headers.headers

        self._test_all_warcs('/warcs/cookieskip/', 1)

    def test_record_skip_wrong_coll(self):
        recorder_app = RecorderApp(self.upstream_url,
                        writer=PerRecordWARCWriter(to_path(self.root_dir + '/warcs/')), accept_colls='not-live')

        resp = self._test_warc_write(recorder_app, 'httpbin.org', '/get?foo=bar')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs/', 2)

    def test_record_param_user_coll(self):
        warc_path = to_path(self.root_dir + '/warcs/{user}/{coll}/')

        dedup_index = self._get_dedup_index()

        recorder_app = RecorderApp(self.upstream_url,
                        PerRecordWARCWriter(warc_path, dedup_index=dedup_index))

        self._test_all_warcs('/warcs/', 2)

        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?foo=bar', '&param.recorder.user=USER&param.recorder.coll=COLL')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs/USER/COLL/', 1)

        r = FakeStrictRedis.from_url('redis://localhost/2')

        res = r.zrangebylex('USER:COLL:cdxj', '[org,httpbin)/', '(org,httpbin,')
        assert len(res) == 1

        cdx = CDXObject(res[0])
        assert cdx['urlkey'] == 'org,httpbin)/get?foo=bar'
        assert cdx['mime'] == 'application/json'
        assert cdx['offset'] == '0'
        assert cdx['filename'].startswith('USER/COLL/')
        assert cdx['filename'].endswith('.warc.gz')

        warcs = r.hgetall('USER:COLL:warc')
        full_path = self.root_dir + '/warcs/' + cdx['filename']
        assert warcs == {cdx['filename'].encode('utf-8'): full_path.encode('utf-8')}

    def test_record_param_user_coll_same_dir(self):
        warc_path = to_path(self.root_dir + '/warcs2/')

        dedup_index = self._get_dedup_index()

        recorder_app = RecorderApp(self.upstream_url,
                        PerRecordWARCWriter(warc_path, dedup_index=dedup_index, key_template='{user}:{coll}'))

        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?foo=bar', '&param.recorder.user=USER2&param.recorder.coll=COLL2')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?foo=bar', '&param.recorder.user=USER2&param.recorder.coll=COLL3')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs2', 2)

    def test_record_param_user_coll_revisit(self):
        warc_path = to_path(self.root_dir + '/warcs/{user}/{coll}/')

        dedup_index = self._get_dedup_index()

        recorder_app = RecorderApp(self.upstream_url,
                        PerRecordWARCWriter(warc_path, dedup_index=dedup_index))

        self._test_all_warcs('/warcs/', 2)

        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?foo=bar', '&param.recorder.user=USER&param.recorder.coll=COLL')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs/USER/COLL/', 2)

        # Test Redis CDX
        r = FakeStrictRedis.from_url('redis://localhost/2')

        res = r.zrangebylex('USER:COLL:cdxj', '[org,httpbin)/', '(org,httpbin,')
        assert len(res) == 2

        if b'warc/revisit' in res[0]:
            cdx = CDXObject(res[0])
        else:
            cdx = CDXObject(res[1])

        assert cdx['urlkey'] == 'org,httpbin)/get?foo=bar'
        assert cdx['mime'] == 'warc/revisit'
        assert cdx['offset'] == '0'
        assert cdx['filename'].startswith('USER/COLL/')
        assert cdx['filename'].endswith('.warc.gz')

        fullwarc = os.path.join(self.root_dir, 'warcs', cdx['filename'])

        warcs = r.hgetall('USER:COLL:warc')
        assert len(warcs) == 2
        assert warcs[cdx['filename'].encode('utf-8')] == fullwarc.encode('utf-8')

        with open(fullwarc, 'rb') as fh:
            decomp = DecompressingBufferedReader(fh)
            # Test refers-to headers
            status_headers = StatusAndHeadersParser(['WARC/1.0']).parse(decomp)
            assert status_headers.get_header('WARC-Type') == 'revisit'
            assert status_headers.get_header('WARC-Target-URI') == 'http://httpbin.org/get?foo=bar'
            assert status_headers.get_header('WARC-Date') != ''
            assert status_headers.get_header('WARC-Refers-To-Target-URI') == 'http://httpbin.org/get?foo=bar'
            assert status_headers.get_header('WARC-Refers-To-Date') != ''

    def test_record_param_user_coll_skip(self):
        warc_path = to_path(self.root_dir + '/warcs/{user}/{coll}/')

        dedup_index = self._get_dedup_index(dupe_policy=SkipDupePolicy())

        recorder_app = RecorderApp(self.upstream_url,
                        PerRecordWARCWriter(warc_path, dedup_index=dedup_index))

        # No new entries written
        self._test_all_warcs('/warcs/', 2)

        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?foo=bar', '&param.recorder.user=USER&param.recorder.coll=COLL')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs/USER/COLL/', 2)

        # Test Redis CDX
        r = FakeStrictRedis.from_url('redis://localhost/2')

        res = r.zrangebylex('USER:COLL:cdxj', '[org,httpbin)/', '(org,httpbin,')
        assert len(res) == 2

    def test_record_param_user_coll_write_dupe_no_revisit(self):
        warc_path = to_path(self.root_dir + '/warcs/{user}/{coll}/')

        dedup_index = self._get_dedup_index(dupe_policy=WriteDupePolicy())

        writer = PerRecordWARCWriter(warc_path, dedup_index=dedup_index)
        recorder_app = RecorderApp(self.upstream_url, writer)

        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?foo=bar', '&param.recorder.user=USER&param.recorder.coll=COLL')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs/USER/COLL/', 3)

        r = FakeStrictRedis.from_url('redis://localhost/2')

        res = r.zrangebylex('USER:COLL:cdxj', '[org,httpbin)/', '(org,httpbin,')
        assert len(res) == 3

        mimes = [CDXObject(x)['mime'] for x in res]

        assert sorted(mimes) == ['application/json', 'application/json', 'warc/revisit']

        assert len(writer.fh_cache) == 0

    # Keep Open
    def test_record_file_warc_keep_open(self):
        path = to_path(self.root_dir + '/warcs/A.warc.gz')
        writer = MultiFileWARCWriter(path)
        recorder_app = RecorderApp(self.upstream_url, writer)

        resp = self._test_warc_write(recorder_app, 'httpbin.org', '/get?foo=bar')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        assert os.path.isfile(path)
        assert len(writer.fh_cache) == 1

    def test_record_multiple_writes_keep_open(self):
        warc_path = to_path(self.root_dir + '/warcs/FOO/ABC-{hostname}-{timestamp}.warc.gz')

        rel_path = self.root_dir + '/warcs/'

        dedup_index = self._get_dedup_index(user=False)

        writer = MultiFileWARCWriter(warc_path, dedup_index=dedup_index)
        recorder_app = RecorderApp(self.upstream_url, writer)

        # First Record
        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?foo=bar', '&param.recorder.coll=FOO')

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body


        # Second Record
        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?boo=far', '&param.recorder.coll=FOO')

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"boo": "far"' in resp.body

        self._test_all_warcs('/warcs/FOO/', 1)

        # Check two records in WARC
        r = FakeStrictRedis.from_url('redis://localhost/2')
        res = r.zrangebylex('FOO:cdxj', '[org,httpbin)/', '(org,httpbin,')
        assert len(res) == 2

        files, coll_dir = self._test_all_warcs('/warcs/FOO/', 1)
        fullname = coll_dir + files[0]

        cdxout = BytesIO()
        with open(fullname, 'rb') as fh:
            filename = os.path.relpath(fullname, rel_path)
            write_cdx_index(cdxout, fh, filename,
                            cdxj=True, append_post=True, sort=True)

        res = [CDXObject(x) for x in res]

        cdxres = cdxout.getvalue().strip()
        cdxres = cdxres.split(b'\n')
        cdxres = [CDXObject(x) for x in cdxres]

        assert cdxres == res

        assert len(writer.fh_cache) == 1

        writer.close_key(self.root_dir + '/warcs/FOO/')

        assert len(writer.fh_cache) == 0

        writer.close()

        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                                '/get?boo=far', '&param.recorder.coll=FOO')

        self._test_all_warcs('/warcs/FOO/', 2)

        warcs = r.hgetall('FOO:warc')
        assert len(warcs) == 2

    def test_record_multiple_writes_rollover_idle(self):
        warc_path = to_path(self.root_dir + '/warcs/GOO/ABC-{hostname}-{timestamp}.warc.gz')

        rel_path = self.root_dir + '/warcs/'

        dedup_index = self._get_dedup_index(user=False)

        writer = MultiFileWARCWriter(warc_path, dedup_index=dedup_index, max_idle_secs=0.9)
        recorder_app = RecorderApp(self.upstream_url, writer)

        # First Record
        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?foo=bar', '&param.recorder.coll=GOO')

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        # Second Record
        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?boo=far', '&param.recorder.coll=GOO')

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"boo": "far"' in resp.body

        self._test_all_warcs('/warcs/GOO/', 1)

        time.sleep(1.0)
        writer.close_idle_files()

        # Third Record
        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                            '/get?goo=bar', '&param.recorder.coll=GOO')

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"goo": "bar"' in resp.body

        self._test_all_warcs('/warcs/GOO/', 2)

    def test_record_custom_record(self):
        dedup_index = self._get_dedup_index(user=False)

        warc_path = to_path(self.root_dir + '/warcs/meta/meta.warc.gz')

        recorder_app = RecorderApp(self.upstream_url,
                        MultiFileWARCWriter(warc_path, dedup_index=dedup_index))

        req_url = '/live/resource/postreq?url=custom://httpbin.org&param.recorder.coll=META&put_record=resource'

        buff = b'Some Data'

        testapp = webtest.TestApp(recorder_app)
        headers = {'content-type': 'text/plain',
                   'WARC-Custom': 'foo'
                  }

        resp = testapp.put(req_url, headers=headers, params=buff)

        assert resp.json['success'] == 'true'
        assert resp.json['WARC-Date'] != ''

        self._test_all_warcs('/warcs/meta', 1)

        r = FakeStrictRedis.from_url('redis://localhost/2')

        warcs = r.hgetall('META:warc')
        assert len(warcs) == 1

        with open(warcs[b'meta/meta.warc.gz'], 'rb') as fh:
            decomp = DecompressingBufferedReader(fh)
            record = ArcWarcRecordLoader().parse_record_stream(decomp)

        status_headers = record.rec_headers
        assert len(record.rec_headers.headers) == 9
        assert status_headers.get_header('WARC-Type') == 'resource'
        assert status_headers.get_header('WARC-Target-URI') == 'custom://httpbin.org'
        assert status_headers.get_header('WARC-Record-ID') != ''
        assert status_headers.get_header('WARC-Date') != ''
        assert status_headers.get_header('WARC-Block-Digest') != ''
        assert status_headers.get_header('WARC-Block-Digest') == status_headers.get_header('WARC-Payload-Digest')
        assert status_headers.get_header('Content-Type') == 'text/plain'
        assert status_headers.get_header('Content-Length') == str(len(buff))
        assert status_headers.get_header('WARC-Custom') == 'foo'

        assert record.raw_stream.read() == buff

        status_headers = record.http_headers
        assert len(record.http_headers.headers) == 2

        assert status_headers.get_header('Content-Type') == 'text/plain'
        assert status_headers.get_header('Content-Length') == str(len(buff))

    def test_record_video_metadata(self):
        warc_path = to_path(self.root_dir + '/warcs/{user}/{coll}/')

        dedup_index = self._get_dedup_index()

        writer = PerRecordWARCWriter(warc_path, dedup_index=dedup_index)
        recorder_app = RecorderApp(self.upstream_url, writer)

        params = {'param.recorder.user': 'USER',
                  'param.recorder.coll': 'VIDEO',
                  'content_type': 'application/vnd.youtube-dl_formats+json'
                 }

        resp = self._test_warc_write(recorder_app,
            'www.youtube.com', '/v/BfBgWtAIbRc', '&' + urlencode(params),
            link_url='metadata://www.youtube.com/v/BfBgWtAIbRc')

        r = FakeStrictRedis.from_url('redis://localhost/2')

        warcs = r.hgetall('USER:VIDEO:warc')
        assert len(warcs) == 1

        filename = list(warcs.values())[0]

        with open(filename, 'rb') as fh:
            decomp = DecompressingBufferedReader(fh)
            record = ArcWarcRecordLoader().parse_record_stream(decomp)

        status_headers = record.rec_headers
        assert status_headers.get_header('WARC-Type') == 'metadata'
        assert status_headers.get_header('Content-Type') == 'application/vnd.youtube-dl_formats+json'
        assert status_headers.get_header('WARC-Block-Digest') != ''
        assert status_headers.get_header('WARC-Block-Digest') == status_headers.get_header('WARC-Payload-Digest')
