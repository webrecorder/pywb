#from gevent import monkey; monkey.patch_all(thread=False)

from collections import OrderedDict

from webagg.handlers import DefaultResourceHandler, HandlerSeq

from webagg.indexsource import MementoIndexSource, FileIndexSource, LiveIndexSource
from webagg.aggregator import GeventTimeoutAggregator, SimpleAggregator
from webagg.aggregator import DirectoryIndexSource

from webagg.app import ResAggApp
from webagg.utils import MementoUtils

from pywb.utils.statusandheaders import StatusAndHeadersParser
from pywb.utils.bufferedreaders import ChunkedDataReader
from io import BytesIO

import webtest
from fakeredis import FakeStrictRedis

from .testutils import to_path, FakeRedisTests, BaseTestClass

import json

sources = {
    'local': DirectoryIndexSource(to_path('testdata/'), ''),
    'ia': MementoIndexSource.from_timegate_url('http://web.archive.org/web/'),
    'rhiz': MementoIndexSource.from_timegate_url('http://webenact.rhizome.org/vvork/', path='*'),
    'live': LiveIndexSource(),
}

testapp = None

def setup_module(self):
    live_source = SimpleAggregator({'live': LiveIndexSource()})
    live_handler = DefaultResourceHandler(live_source)
    app = ResAggApp()
    app.add_route('/live', live_handler)

    source1 = GeventTimeoutAggregator(sources)
    handler1 = DefaultResourceHandler(source1, to_path('testdata/'))
    app.add_route('/many', handler1)

    source2 = SimpleAggregator({'post': FileIndexSource(to_path('testdata/post-test.cdxj'))})
    handler2 = DefaultResourceHandler(source2, to_path('testdata/'))
    app.add_route('/posttest', handler2)

    source3 = SimpleAggregator({'example': FileIndexSource(to_path('testdata/example.cdxj'))})
    handler3 = DefaultResourceHandler(source3, to_path('testdata/'))

    app.add_route('/fallback', HandlerSeq([handler3,
                                       handler2,
                                       live_handler]))

    app.add_route('/seq', HandlerSeq([handler3,
                                  handler2]))

    app.add_route('/allredis', DefaultResourceHandler(source3, 'redis://localhost/2/test:warc'))

    app.add_route('/empty', HandlerSeq([]))
    app.add_route('/invalid', DefaultResourceHandler([SimpleAggregator({'invalid': 'should not be a callable'})]))

    global testapp
    testapp = webtest.TestApp(app.application)


def to_json_list(text):
    return list([json.loads(cdx) for cdx in text.rstrip().split('\n')])


class TestResAgg(FakeRedisTests, BaseTestClass):
    def setup(self):
        self.testapp = testapp

    def _check_uri_date(self, resp, uri, dt):
        buff = BytesIO(resp.body)
        buff = ChunkedDataReader(buff)
        status_headers = StatusAndHeadersParser(['WARC/1.0']).parse(buff)
        assert status_headers.get_header('WARC-Target-URI') == uri
        if dt == True:
            assert status_headers.get_header('WARC-Date') != ''
        else:
            assert status_headers.get_header('WARC-Date') == dt

    def test_list_routes(self):
        resp = self.testapp.get('/')
        res = resp.json
        assert set(res.keys()) == set(['/empty', '/empty/postreq',
                                       '/fallback', '/fallback/postreq',
                                       '/live', '/live/postreq',
                                       '/many', '/many/postreq',
                                       '/posttest', '/posttest/postreq',
                                       '/seq', '/seq/postreq',
                                       '/allredis', '/allredis/postreq',
                                       '/invalid', '/invalid/postreq'])

        assert res['/fallback'] == {'modes': ['list_sources', 'index', 'resource']}

    def test_list_handlers(self):
        resp = self.testapp.get('/many')
        assert resp.json == {'modes': ['list_sources', 'index', 'resource']}
        assert 'ResErrors' not in resp.headers

        resp = self.testapp.get('/many/other')
        assert resp.json == {'modes': ['list_sources', 'index', 'resource']}
        assert 'ResErrors' not in resp.headers

    def test_list_errors(self):
        # must specify url for index or resource
        resp = self.testapp.get('/many/index', status=400)
        assert resp.json == {'message': 'The "url" param is required'}
        assert resp.text == resp.headers['ResErrors']

        resp = self.testapp.get('/many/index', status=400)
        assert resp.json == {'message': 'The "url" param is required'}
        assert resp.text == resp.headers['ResErrors']

        resp = self.testapp.get('/many/resource', status=400)
        assert resp.json == {'message': 'The "url" param is required'}
        assert resp.text == resp.headers['ResErrors']

    def test_list_sources(self):
        resp = self.testapp.get('/many/list_sources')
        assert resp.json == {'sources': {'local': 'file_dir', 'ia': 'memento', 'rhiz': 'memento', 'live': 'live'}}
        assert 'ResErrors' not in resp.headers

    def test_live_index(self):
        resp = self.testapp.get('/live/index?url=http://httpbin.org/get&output=json')
        resp.charset = 'utf-8'

        res = to_json_list(resp.text)
        res[0]['timestamp'] = '2016'
        assert(res == [{'url': 'http://httpbin.org/get', 'urlkey': 'org,httpbin)/get', 'is_live': 'true',
                        'load_url': 'http://httpbin.org/get', 'source': 'live', 'timestamp': '2016'}])

    def test_live_resource(self):
        headers = {'foo': 'bar'}
        resp = self.testapp.get('/live/resource?url=http://httpbin.org/get?foo=bar', headers=headers)

        assert resp.headers['WebAgg-Source-Coll'] == 'live'

        self._check_uri_date(resp, 'http://httpbin.org/get?foo=bar', True)

        assert resp.headers['Link'] == MementoUtils.make_link('http://httpbin.org/get?foo=bar', 'original')
        assert resp.headers['Memento-Datetime'] != ''

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        assert 'ResErrors' not in resp.headers

    def test_live_post_resource(self):
        resp = self.testapp.post('/live/resource?url=http://httpbin.org/post',
                                 OrderedDict([('foo', 'bar')]))

        assert resp.headers['WebAgg-Source-Coll'] == 'live'

        self._check_uri_date(resp, 'http://httpbin.org/post', True)

        assert resp.headers['Link'] == MementoUtils.make_link('http://httpbin.org/post', 'original')
        assert resp.headers['Memento-Datetime'] != ''

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        assert 'ResErrors' not in resp.headers

    def test_agg_select_mem_1(self):
        resp = self.testapp.get('/many/resource?url=http://vvork.com/&closest=20141001')

        assert resp.headers['WebAgg-Source-Coll'] == 'rhiz'

        self._check_uri_date(resp, 'http://www.vvork.com/', '2014-10-06T18:43:57Z')

        assert b'HTTP/1.1 200 OK' in resp.body

        assert resp.headers['Link'] == MementoUtils.make_link('http://www.vvork.com/', 'original')
        assert resp.headers['Memento-Datetime'] == 'Mon, 06 Oct 2014 18:43:57 GMT'

        assert 'ResErrors' not in resp.headers

    def test_agg_select_mem_2(self):
        resp = self.testapp.get('/many/resource?url=http://vvork.com/&closest=20151231')

        assert resp.headers['WebAgg-Source-Coll'] == 'ia'

        self._check_uri_date(resp, 'http://vvork.com/', '2016-01-10T13:48:55Z')

        assert b'HTTP/1.1 200 OK' in resp.body

        assert resp.headers['Link'] == MementoUtils.make_link('http://vvork.com/', 'original')
        assert resp.headers['Memento-Datetime'] == 'Sun, 10 Jan 2016 13:48:55 GMT'

        assert 'ResErrors' not in resp.headers

    def test_agg_select_live(self):
        resp = self.testapp.get('/many/resource?url=http://vvork.com/&closest=2016')

        assert resp.headers['WebAgg-Source-Coll'] == 'live'

        self._check_uri_date(resp, 'http://vvork.com/', True)

        assert resp.headers['Link'] == MementoUtils.make_link('http://vvork.com/', 'original')
        assert resp.headers['Memento-Datetime'] != ''

        assert 'ResErrors' not in resp.headers

    def test_agg_select_local(self):
        resp = self.testapp.get('/many/resource?url=http://iana.org/&closest=20140126200624')

        assert resp.headers['WebAgg-Source-Coll'] == 'local:iana.cdxj'

        self._check_uri_date(resp, 'http://www.iana.org/', '2014-01-26T20:06:24Z')

        assert resp.headers['Link'] == MementoUtils.make_link('http://www.iana.org/', 'original')
        assert resp.headers['Memento-Datetime'] == 'Sun, 26 Jan 2014 20:06:24 GMT'

        assert json.loads(resp.headers['ResErrors']) == {"rhiz": "NotFoundException('http://webenact.rhizome.org/vvork/http://iana.org/',)"}

    def test_agg_select_local_postreq(self):
        req_data = """\
GET / HTTP/1.1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
User-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36
Host: iana.org
"""

        resp = self.testapp.post('/many/resource/postreq?url=http://iana.org/&closest=20140126200624', req_data)

        assert resp.headers['WebAgg-Source-Coll'] == 'local:iana.cdxj'

        self._check_uri_date(resp, 'http://www.iana.org/', '2014-01-26T20:06:24Z')

        assert resp.headers['Link'] == MementoUtils.make_link('http://www.iana.org/', 'original')
        assert resp.headers['Memento-Datetime'] == 'Sun, 26 Jan 2014 20:06:24 GMT'

        assert json.loads(resp.headers['ResErrors']) == {"rhiz": "NotFoundException('http://webenact.rhizome.org/vvork/http://iana.org/',)"}

    def test_agg_live_postreq(self):
        req_data = """\
GET /get?foo=bar HTTP/1.1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
User-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36
Host: httpbin.org
"""

        resp = self.testapp.post('/many/resource/postreq?url=http://httpbin.org/get?foo=bar&closest=now', req_data)

        assert resp.headers['WebAgg-Source-Coll'] == 'live'

        self._check_uri_date(resp, 'http://httpbin.org/get?foo=bar', True)

        assert resp.headers['Link'] == MementoUtils.make_link('http://httpbin.org/get?foo=bar', 'original')
        assert resp.headers['Memento-Datetime'] != ''

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

        assert json.loads(resp.headers['ResErrors']) == {"rhiz": "NotFoundException('http://webenact.rhizome.org/vvork/http://httpbin.org/get?foo=bar',)"}

    def test_agg_post_resolve_postreq(self):
        req_data = """\
POST /post HTTP/1.1
content-length: 16
accept-encoding: gzip, deflate
accept: */*
host: httpbin.org
content-type: application/x-www-form-urlencoded

foo=bar&test=abc"""

        resp = self.testapp.post('/posttest/resource/postreq?url=http://httpbin.org/post', req_data)

        assert resp.headers['WebAgg-Source-Coll'] == 'post'

        self._check_uri_date(resp, 'http://httpbin.org/post', True)

        assert resp.headers['Link'] == MementoUtils.make_link('http://httpbin.org/post', 'original')
        assert resp.headers['Memento-Datetime'] != ''

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body
        assert b'"test": "abc"' in resp.body
        assert b'"url": "http://httpbin.org/post"' in resp.body

        assert 'ResErrors' not in resp.headers

    def test_agg_post_resolve_fallback(self):
        req_data = OrderedDict([('foo', 'bar'), ('test', 'abc')])

        resp = self.testapp.post('/fallback/resource?url=http://httpbin.org/post', req_data)

        assert resp.headers['WebAgg-Source-Coll'] == 'post'

        self._check_uri_date(resp, 'http://httpbin.org/post', True)

        assert resp.headers['Link'] == MementoUtils.make_link('http://httpbin.org/post', 'original')

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body
        assert b'"test": "abc"' in resp.body
        assert b'"url": "http://httpbin.org/post"' in resp.body

        assert 'ResErrors' not in resp.headers

    def test_agg_seq_fallback_1(self):
        resp = self.testapp.get('/fallback/resource?url=http://www.iana.org/')

        assert resp.headers['WebAgg-Source-Coll'] == 'live'

        self._check_uri_date(resp, 'http://www.iana.org/', True)

        assert resp.headers['Link'] == MementoUtils.make_link('http://www.iana.org/', 'original')

        assert b'HTTP/1.1 200 OK' in resp.body

        assert 'ResErrors' not in resp.headers

    def test_agg_seq_fallback_2(self):
        resp = self.testapp.get('/fallback/resource?url=http://www.example.com/')

        assert resp.headers['WebAgg-Source-Coll'] == 'example'

        self._check_uri_date(resp, 'http://example.com/', '2016-02-25T04:23:29Z')

        assert resp.headers['Link'] == MementoUtils.make_link('http://example.com/', 'original')
        assert resp.headers['Memento-Datetime'] == 'Thu, 25 Feb 2016 04:23:29 GMT'

        assert b'HTTP/1.1 200 OK' in resp.body

        assert 'ResErrors' not in resp.headers

    def test_redis_warc_1(self):
        f = FakeStrictRedis.from_url('redis://localhost/2')
        f.hset('test:warc', 'example.warc.gz', './testdata/example.warc.gz')

        resp = self.testapp.get('/allredis/resource?url=http://www.example.com/')

        assert resp.headers['WebAgg-Source-Coll'] == 'example'

    def test_error_redis_file_not_found(self):
        f = FakeStrictRedis.from_url('redis://localhost/2')
        f.hset('test:warc', 'example.warc.gz', './testdata/example2.warc.gz')

        resp = self.testapp.get('/allredis/resource?url=http://www.example.com/', status=503)
        assert resp.json['message'] == "example.warc.gz:[Errno 2] No such file or directory: './testdata/example2.warc.gz'"

        f.hdel('test:warc', 'example.warc.gz')
        resp = self.testapp.get('/allredis/resource?url=http://www.example.com/', status=503)

        assert resp.json == {'message': 'example.warc.gz:Archive File Not Found',
                             'errors': {'WARCPathLoader': "ArchiveLoadFailed('example.warc.gz:Archive File Not Found',)"}}

        f.delete('test:warc')
        resp = self.testapp.get('/allredis/resource?url=http://www.example.com/', status=503)

        assert resp.json == {'message': 'example.warc.gz:Archive File Not Found',
                             'errors': {'WARCPathLoader': "ArchiveLoadFailed('example.warc.gz:Archive File Not Found',)"}}


    def test_error_fallback_live_not_found(self):
        resp = self.testapp.get('/fallback/resource?url=http://invalid.url-not-found', status=400)

        assert resp.json == {'message': 'http://invalid.url-not-found',
                             'errors': {'LiveWebLoader': "LiveResourceException('http://invalid.url-not-found',)"}}

        assert resp.text == resp.headers['ResErrors']

    def test_agg_local_revisit(self):
        resp = self.testapp.get('/many/resource?url=http://www.example.com/&closest=20140127171251&sources=local')

        assert resp.headers['WebAgg-Source-Coll'] == 'local:dupes.cdxj'

        buff = BytesIO(resp.body)
        status_headers = StatusAndHeadersParser(['WARC/1.0']).parse(buff)
        assert status_headers.get_header('WARC-Target-URI') == 'http://example.com'
        assert status_headers.get_header('WARC-Date') == '2014-01-27T17:12:51Z'
        assert status_headers.get_header('WARC-Refers-To-Target-URI') == 'http://example.com'
        assert status_headers.get_header('WARC-Refers-To-Date') == '2014-01-27T17:12:00Z'

        assert resp.headers['Link'] == MementoUtils.make_link('http://example.com', 'original')
        assert resp.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'<!doctype html>' in resp.body

        assert 'ResErrors' not in resp.headers

    def test_error_invalid_index_output(self):
        resp = self.testapp.get('/live/index?url=http://httpbin.org/get&output=foobar', status=400)

        assert resp.json == {'message': 'output=foobar not supported'}
        assert resp.text == resp.headers['ResErrors']

    def test_error_local_not_found(self):
        resp = self.testapp.get('/many/resource?url=http://not-found.error/&sources=local', status=404)

        assert resp.json == {'message': 'No Resource Found'}
        assert resp.text == resp.headers['ResErrors']

    def test_error_empty(self):
        resp = self.testapp.get('/empty/resource?url=http://example.com/', status=404)

        assert resp.json == {'message': 'No Resource Found'}
        assert resp.text == resp.headers['ResErrors']

    def test_error_invalid(self):
        resp = self.testapp.get('/invalid/resource?url=http://example.com/', status=500)

        assert resp.json == {'message': "Internal Error: 'list' object is not callable"}
        assert resp.text == resp.headers['ResErrors']


