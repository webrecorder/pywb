from gevent import monkey; monkey.patch_all(thread=False)

from collections import OrderedDict

from rezag.handlers import DefaultResourceHandler, HandlerSeq

from rezag.indexsource import MementoIndexSource, FileIndexSource, LiveIndexSource
from rezag.aggindexsource import GeventTimeoutAggregator, SimpleAggregator
from rezag.aggindexsource import DirectoryIndexAggregator

from rezag.app import add_route, application

import webtest
import bottle

from .testutils import to_path

import json

sources = {
    'local': DirectoryIndexAggregator(to_path('testdata/'), ''),
    'ia': MementoIndexSource.from_timegate_url('http://web.archive.org/web/'),
    'rhiz': MementoIndexSource.from_timegate_url('http://webenact.rhizome.org/vvork/', path='*'),
    'live': LiveIndexSource(),
}

testapp = None

def setup_module(self):
    live_source = SimpleAggregator({'live': LiveIndexSource()})
    live_handler = DefaultResourceHandler(live_source)
    add_route('/live', live_handler)

    source1 = GeventTimeoutAggregator(sources)
    handler1 = DefaultResourceHandler(source1, to_path('testdata/'))
    add_route('/many', handler1)

    source2 = SimpleAggregator({'post': FileIndexSource(to_path('testdata/post-test.cdxj'))})
    handler2 = DefaultResourceHandler(source2, to_path('testdata/'))
    add_route('/posttest', handler2)

    source3 = SimpleAggregator({'example': FileIndexSource(to_path('testdata/example.cdxj'))})
    handler3 = DefaultResourceHandler(source3, to_path('testdata/'))


    add_route('/fallback', HandlerSeq([handler3,
                                       handler2,
                                       live_handler]))


    bottle.debug = True
    global testapp
    testapp = webtest.TestApp(application)


def to_json_list(text):
    return list([json.loads(cdx) for cdx in text.rstrip().split('\n')])


class TestResAgg(object):
    def setup(self):
        self.testapp = testapp

    def test_live_index(self):
        resp = self.testapp.get('/live?url=http://httpbin.org/get&mode=index&output=json')
        resp.charset = 'utf-8'

        res = to_json_list(resp.text)
        res[0]['timestamp'] = '2016'
        assert(res == [{'url': 'http://httpbin.org/get', 'urlkey': 'org,httpbin)/get', 'is_live': True,
                        'load_url': 'http://httpbin.org/get', 'source': 'live', 'timestamp': '2016'}])

    def test_live_resource(self):
        resp = self.testapp.get('/live?url=http://httpbin.org/get?foo=bar&mode=resource')

        assert resp.headers['WARC-Coll'] == 'live'
        assert resp.headers['WARC-Target-URI'] == 'http://httpbin.org/get?foo=bar'
        assert 'WARC-Date' in resp.headers

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body


    def test_live_post_resource(self):
        resp = self.testapp.post('/live?url=http://httpbin.org/post&mode=resource',
                                 OrderedDict([('foo', 'bar')]))

        assert resp.headers['WARC-Coll'] == 'live'
        assert resp.headers['WARC-Target-URI'] == 'http://httpbin.org/post'
        assert 'WARC-Date' in resp.headers

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

    def test_agg_select_mem_1(self):
        resp = self.testapp.get('/many?url=http://vvork.com/&closest=20141001')

        assert resp.headers['WARC-Coll'] == 'rhiz'
        assert resp.headers['WARC-Target-URI'] == 'http://www.vvork.com/'
        assert resp.headers['WARC-Date'] == '2014-10-06T18:43:57Z'
        assert b'HTTP/1.1 200 OK' in resp.body


    def test_agg_select_mem_2(self):
        resp = self.testapp.get('/many?url=http://vvork.com/&closest=20151231')

        assert resp.headers['WARC-Coll'] == 'ia'
        assert resp.headers['WARC-Target-URI'] == 'http://vvork.com/'
        assert resp.headers['WARC-Date'] == '2016-01-10T13:48:55Z'
        assert b'HTTP/1.1 200 OK' in resp.body


    def test_agg_select_live(self):
        resp = self.testapp.get('/many?url=http://vvork.com/&closest=2016')

        assert resp.headers['WARC-Coll'] == 'live'
        assert resp.headers['WARC-Target-URI'] == 'http://vvork.com/'
        assert resp.headers['WARC-Date'] != ''

    def test_agg_select_local(self):
        resp = self.testapp.get('/many?url=http://iana.org/&closest=20140126200624')

        assert resp.headers['WARC-Coll'] == 'local'
        assert resp.headers['WARC-Target-URI'] == 'http://www.iana.org/'
        assert resp.headers['WARC-Date'] == '2014-01-26T20:06:24Z'


    def test_agg_select_local_postreq(self):
        req_data = """\
GET / HTTP/1.1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
User-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36
Host: iana.org
"""

        resp = self.testapp.post('/many/postreq?url=http://iana.org/&closest=20140126200624', req_data)

        assert resp.headers['WARC-Coll'] == 'local'
        assert resp.headers['WARC-Target-URI'] == 'http://www.iana.org/'
        assert resp.headers['WARC-Date'] == '2014-01-26T20:06:24Z'


    def test_agg_live_postreq(self):
        req_data = """\
GET /get?foo=bar HTTP/1.1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
User-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36
Host: httpbin.org
"""

        resp = self.testapp.post('/many/postreq?url=http://httpbin.org/get?foo=bar&closest=now', req_data)

        assert resp.headers['WARC-Coll'] == 'live'
        assert resp.headers['WARC-Target-URI'] == 'http://httpbin.org/get?foo=bar'
        assert 'WARC-Date' in resp.headers

        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body

    def test_agg_post_resolve_postreq(self):
        req_data = """\
POST /post HTTP/1.1
content-length: 16
accept-encoding: gzip, deflate
accept: */*
host: httpbin.org
content-type: application/x-www-form-urlencoded

foo=bar&test=abc"""

        resp = self.testapp.post('/posttest/postreq?url=http://httpbin.org/post', req_data)

        assert resp.headers['WARC-Coll'] == 'post'
        assert resp.headers['WARC-Target-URI'] == 'http://httpbin.org/post'
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body
        assert b'"test": "abc"' in resp.body
        assert b'"url": "http://httpbin.org/post"' in resp.body

    def test_agg_post_resolve_fallback(self):
        req_data = OrderedDict([('foo', 'bar'), ('test', 'abc')])

        resp = self.testapp.post('/fallback?url=http://httpbin.org/post', req_data)

        assert resp.headers['WARC-Coll'] == 'post'
        assert resp.headers['WARC-Target-URI'] == 'http://httpbin.org/post'
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'"foo": "bar"' in resp.body
        assert b'"test": "abc"' in resp.body
        assert b'"url": "http://httpbin.org/post"' in resp.body

    def test_agg_seq_fallback_1(self):
        resp = self.testapp.get('/fallback?url=http://www.iana.org/')

        assert resp.headers['WARC-Coll'] == 'live'
        assert resp.headers['WARC-Target-URI'] == 'http://www.iana.org/'
        assert b'HTTP/1.1 200 OK' in resp.body

    def test_agg_seq_fallback_2(self):
        resp = self.testapp.get('/fallback?url=http://www.example.com/')

        assert resp.headers['WARC-Coll'] == 'example'
        assert resp.headers['WARC-Date'] == '2016-02-25T04:23:29Z'
        assert resp.headers['WARC-Target-URI'] == 'http://example.com/'
        assert b'HTTP/1.1 200 OK' in resp.body

    def test_agg_local_revisit(self):
        resp = self.testapp.get('/many?url=http://www.example.com/&closest=20140127171251&sources=local')

        assert resp.headers['WARC-Coll'] == 'local'
        assert resp.headers['WARC-Target-URI'] == 'http://example.com'
        assert resp.headers['WARC-Date'] == '2014-01-27T17:12:51Z'
        assert resp.headers['WARC-Refers-To-Target-URI'] == 'http://example.com'
        assert resp.headers['WARC-Refers-To-Date'] == '2014-01-27T17:12:00Z'
        assert b'HTTP/1.1 200 OK' in resp.body
        assert b'<!doctype html>' in resp.body
