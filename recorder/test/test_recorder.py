#from gevent import monkey; monkey.patch_all()
import gevent

from webagg.test.testutils import TempDirTests, LiveServerTests, BaseTestClass, to_path
from webagg.test.testutils import FakeRedisTests

import os
import webtest

from pytest import raises
from fakeredis import FakeStrictRedis

from recorder.recorderapp import RecorderApp
from recorder.redisindexer import WritableRedisIndexer
from recorder.warcwriter import PerRecordWARCWriter, MultiFileWARCWriter
from recorder.filters import ExcludeSpecificHeaders
from recorder.filters import SkipDupePolicy, WriteDupePolicy, WriteRevisitDupePolicy

from webagg.utils import MementoUtils

from pywb.cdx.cdxobject import CDXObject
from pywb.utils.statusandheaders import StatusAndHeadersParser
from pywb.utils.bufferedreaders import DecompressingBufferedReader
from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.warc.cdxindexer import write_cdx_index

from six.moves.urllib.parse import quote, unquote
from io import BytesIO
import time

general_req_data = "\
GET {path} HTTP/1.1\r\n\
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\n\
User-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36\r\n\
Host: {host}\r\n\
\r\n"



class TestRecorder(LiveServerTests, FakeRedisTests, TempDirTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRecorder, cls).setup_class()

        warcs = to_path(cls.root_dir + '/warcs')

        os.makedirs(warcs)

        cls.upstream_url = 'http://localhost:{0}'.format(cls.server.port)

    def _get_dedup_index(self, dupe_policy=WriteRevisitDupePolicy()):
        dedup_index = WritableRedisIndexer('redis://localhost/2/{user}:{coll}:cdxj',
                        file_key_template='{user}:{coll}:warc',
                        rel_path_template=self.root_dir + '/warcs/',
                        dupe_policy=dupe_policy)

        return dedup_index

    def _test_warc_write(self, recorder_app, host, path, other_params=''):
        url = 'http://' + host + path
        req_url = '/live/resource/postreq?url=' + url + other_params
        testapp = webtest.TestApp(recorder_app)
        resp = testapp.post(req_url, general_req_data.format(host=host, path=path).encode('utf-8'))

        if not recorder_app.write_queue.empty():
            recorder_app._write_one()

        assert resp.headers['WebAgg-Source-Coll'] == 'live'

        assert resp.headers['Link'] == MementoUtils.make_link(unquote(url), 'original')
        assert resp.headers['Memento-Datetime'] != ''

        return resp

    def _test_all_warcs(self, dirname, num):
        coll_dir = to_path(self.root_dir + dirname)
        assert os.path.isdir(coll_dir)

        files = [x for x in os.listdir(coll_dir) if os.path.isfile(os.path.join(coll_dir, x))]
        assert len(files) == num
        assert all(x.endswith('.warc.gz') for x in files)
        return files, coll_dir

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
        assert ('Set-Cookie', 'name=value; Path=/') in record.status_headers.headers
        assert ('Set-Cookie', 'foo=bar; Path=/') in record.status_headers.headers

        warcs = os.listdir(base_path)

        stored_rec = None
        for warc in warcs:
            with open(os.path.join(base_path, warc), 'rb') as fh:
                decomp = DecompressingBufferedReader(fh)
                stored_rec = ArcWarcRecordLoader().parse_record_stream(decomp)
                if stored_rec.rec_type == 'response':
                    break

        assert stored_rec is not None
        assert ('Set-Cookie', 'name=value; Path=/') in stored_rec.status_headers.headers
        assert ('Set-Cookie', 'foo=bar; Path=/') in stored_rec.status_headers.headers

    def test_record_cookies_skip_header(self):
        base_path = to_path(self.root_dir + '/warcs/cookieskip/')
        header_filter = ExcludeSpecificHeaders(['Set-Cookie', 'Cookie'])
        recorder_app = RecorderApp(self.upstream_url,
                         PerRecordWARCWriter(base_path, header_filter=header_filter),
                            accept_colls='live')

        resp = self._test_warc_write(recorder_app, 'httpbin.org', '/cookies/set%3Fname%3Dvalue%26foo%3Dbar')
        assert b'HTTP/1.1 302' in resp.body

        buff = BytesIO(resp.body)
        record = ArcWarcRecordLoader().parse_record_stream(buff)
        assert ('Set-Cookie', 'name=value; Path=/') in record.status_headers.headers
        assert ('Set-Cookie', 'foo=bar; Path=/') in record.status_headers.headers

        warcs = os.listdir(base_path)

        stored_rec = None
        for warc in warcs:
            with open(os.path.join(base_path, warc), 'rb') as fh:
                decomp = DecompressingBufferedReader(fh)
                stored_rec = ArcWarcRecordLoader().parse_record_stream(decomp)
                if stored_rec.rec_type == 'response':
                    break

        assert stored_rec is not None
        assert ('Set-Cookie', 'name=value; Path=/') not in stored_rec.status_headers.headers
        assert ('Set-Cookie', 'foo=bar; Path=/') not in stored_rec.status_headers.headers


    def test_record_skip_wrong_coll(self):
        recorder_app = RecorderApp(self.upstream_url,
                        writer=PerRecordWARCWriter(to_path(self.root_dir + '/warcs/')), accept_colls='not-live')

        resp = self._test_warc_write(recorder_app, 'httpbin.org', '/get?foo=bar')
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        self._test_all_warcs('/warcs/', 2)

    #@patch('redis.StrictRedis', FakeStrictRedis)
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


    #@patch('redis.StrictRedis', FakeStrictRedis)
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

    #@patch('redis.StrictRedis', FakeStrictRedis)
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

    #@patch('redis.StrictRedis', FakeStrictRedis)
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

    #@patch('redis.StrictRedis', FakeStrictRedis)
    def test_record_multiple_writes_keep_open(self):
        warc_path = to_path(self.root_dir + '/warcs/FOO/ABC-{hostname}-{timestamp}.warc.gz')

        rel_path = self.root_dir + '/warcs/'

        dedup_index = WritableRedisIndexer('redis://localhost/2/{coll}:cdxj',
                        file_key_template='{coll}:warc',
                        rel_path_template=rel_path)


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

        writer.remove_file(self.root_dir + '/warcs/FOO/')

        assert len(writer.fh_cache) == 0

        writer.close()

        resp = self._test_warc_write(recorder_app, 'httpbin.org',
                                '/get?boo=far', '&param.recorder.coll=FOO')

        self._test_all_warcs('/warcs/FOO/', 2)

        warcs = r.hgetall('FOO:warc')
        assert len(warcs) == 2
