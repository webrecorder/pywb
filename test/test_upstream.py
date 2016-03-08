from webagg.app import ResAggApp

import webtest
import threading

from io import BytesIO
import requests

from webagg.handlers import DefaultResourceHandler
from webagg.indexsource import LiveIndexSource
from webagg.proxyindexsource import ProxyMementoIndexSource, UpstreamAggIndexSource
from webagg.aggregator import SimpleAggregator

from wsgiref.simple_server import make_server

from pywb.warc.recordloader import ArcWarcRecordLoader


class ServerThreadRunner(object):
    def __init__(self, app):
        self.httpd = make_server('', 0, app)
        self.port = self.httpd.socket.getsockname()[1]

        def run():
            self.httpd.serve_forever()

        self.thread = threading.Thread(target=run)
        self.thread.daemon = True
        self.thread.start()

    def stop_thread(self):
        self.httpd.shutdown()


server = None


def setup_module():
    app = ResAggApp()
    app.add_route('/live',
        DefaultResourceHandler(SimpleAggregator(
                               {'live': LiveIndexSource()})
        )
    )

    global server
    server = ServerThreadRunner(app.application)

def teardown_module():
    global server
    server.stop_thread()



class TestUpstream(object):
    def setup(self):
        app = ResAggApp()

        base_url = 'http://localhost:{0}'.format(server.port)
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
        self.testapp = webtest.TestApp(app.application)


    def test_live_paths(self):
        res = requests.get(self.base_url + '/')
        assert set(res.json().keys()) == {'/live/postreq', '/live'}

    def test_upstream_paths(self):
        res = self.testapp.get('/')
        assert set(res.json.keys()) == {'/upstream/postreq', '/upstream', '/upstream_opt', '/upstream_opt/postreq'}

    def test_live_1(self):
        resp = requests.get(self.base_url + '/live/resource?url=http://httpbin.org/get', stream=True)
        assert resp.headers['Source-Coll'] == 'live'

        record = ArcWarcRecordLoader().parse_record_stream(resp.raw, no_record_parse=False)
        assert record.rec_headers.get_header('WARC-Target-URI') == 'http://httpbin.org/get'
        assert record.status_headers.get_header('Date') != ''

    def test_upstream_1(self):
        resp = self.testapp.get('/upstream/resource?url=http://httpbin.org/get')
        assert resp.headers['Source-Coll'] == 'upstream:live'

        raw = BytesIO(resp.body)

        record = ArcWarcRecordLoader().parse_record_stream(raw, no_record_parse=False)
        assert record.rec_headers.get_header('WARC-Target-URI') == 'http://httpbin.org/get'
        assert record.status_headers.get_header('Date') != ''

    def test_upstream_2(self):
        resp = self.testapp.get('/upstream_opt/resource?url=http://httpbin.org/get')
        assert resp.headers['Source-Coll'] == 'upstream_opt:live', resp.headers

        raw = BytesIO(resp.body)

        record = ArcWarcRecordLoader().parse_record_stream(raw, no_record_parse=False)
        assert record.rec_headers.get_header('WARC-Target-URI') == 'http://httpbin.org/get'
        assert record.status_headers.get_header('Date') != ''



