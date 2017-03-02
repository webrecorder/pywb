import webtest

from io import BytesIO
from pywb.webagg.app import ResAggApp
import requests

from pywb.webagg.handlers import DefaultResourceHandler
from pywb.webagg.aggregator import SimpleAggregator
from pywb.webagg.proxyindexsource import ProxyMementoIndexSource, UpstreamAggIndexSource

from warcio.recordloader import ArcWarcRecordLoader

from .testutils import LiveServerTests, BaseTestClass


class TestUpstream(LiveServerTests, BaseTestClass):
    def setup(self):
        app = ResAggApp()

        base_url = 'http://localhost:{0}'.format(self.server.port)
        app.add_route('/upstream',
            DefaultResourceHandler(SimpleAggregator(
                           {'upstream': UpstreamAggIndexSource(base_url + '/live')})
            )
        )

        app.add_route('/upstream_opt',
            DefaultResourceHandler(SimpleAggregator(
                           {'upstream_opt': ProxyMementoIndexSource.upstream_resource(base_url + '/live')})
            )
        )

        self.base_url = base_url
        self.testapp = webtest.TestApp(app)


    def test_live_paths(self):
        res = requests.get(self.base_url + '/')
        assert set(res.json().keys()) == {'/live/postreq', '/live'}

    def test_upstream_paths(self):
        res = self.testapp.get('/')
        assert set(res.json.keys()) == {'/upstream/postreq', '/upstream', '/upstream_opt', '/upstream_opt/postreq'}

    def test_live_1(self):
        resp = requests.get(self.base_url + '/live/resource?url=http://httpbin.org/get', stream=True)
        assert resp.headers['WebAgg-Source-Coll'] == 'live'

        record = ArcWarcRecordLoader().parse_record_stream(resp.raw, no_record_parse=False)
        assert record.rec_headers.get_header('WARC-Target-URI') == 'http://httpbin.org/get'
        assert record.http_headers.get_header('Date') != ''

    def test_upstream_1(self):
        resp = self.testapp.get('/upstream/resource?url=http://httpbin.org/get')
        assert resp.headers['WebAgg-Source-Coll'] == 'upstream:live'

        raw = BytesIO(resp.body)

        record = ArcWarcRecordLoader().parse_record_stream(raw, no_record_parse=False)
        assert record.rec_headers.get_header('WARC-Target-URI') == 'http://httpbin.org/get'
        assert record.http_headers.get_header('Date') != ''

    def test_upstream_2(self):
        resp = self.testapp.get('/upstream_opt/resource?url=http://httpbin.org/get')
        assert resp.headers['WebAgg-Source-Coll'] == 'upstream_opt:live', resp.headers

        raw = BytesIO(resp.body)

        record = ArcWarcRecordLoader().parse_record_stream(raw, no_record_parse=False)
        assert record.rec_headers.get_header('WARC-Target-URI') == 'http://httpbin.org/get'
        assert record.http_headers.get_header('Date') != ''



