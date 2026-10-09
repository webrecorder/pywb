from gevent import monkey; monkey.patch_all()
from .testutils import BaseTestClass, HttpBinLiveTests

import webtest
import pytest
from mock import patch, MagicMock

from pywb.utils.wbexception import LiveResourceException
from pywb.warcserver.basewarcserver import BaseWarcServer
from pywb.warcserver.handlers import DefaultResourceHandler
from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.cdxobject import CDXObject
from pywb.warcserver.index.indexsource import LiveIndexSource
from pywb.warcserver.liveurlfilter import LiveUrlFilter
from pywb.warcserver.resource.responseloader import LiveWebLoader, VideoLoader
from pywb.warcserver.warcserver import WarcServer


# ============================================================================
CALLS = []


def allow_all(url, cdx):
    CALLS.append((url, cdx))
    return True


def block_all(url, cdx):
    CALLS.append((url, cdx))
    return False


def raise_error(url, cdx):
    raise ValueError('filter error')


def block_target(url, cdx):
    CALLS.append((url, cdx))
    return 'blocked.example.com' not in cdx['url']


# ============================================================================
class TestLiveUrlFilter(HttpBinLiveTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestLiveUrlFilter, cls).setup_class()

        live_source = SimpleAggregator({'live': LiveIndexSource()})
        app = BaseWarcServer()
        app.add_route('/live', DefaultResourceHandler(live_source))

        cls.testapp = webtest.TestApp(app)

    def setup_method(self):
        del CALLS[:]

    def teardown_method(self):
        LiveUrlFilter.init(None)

    def test_no_filter(self):
        LiveUrlFilter.init(None)
        assert LiveUrlFilter.is_allowed('http://example.com/') == True

        resp = self.testapp.get('/live/resource?url=http://httpbin.org/get')
        assert resp.headers['Warcserver-Source-Coll'] == 'live'

    def test_config(self):
        WarcServer(config_file=None,
                   custom_config={'live_url_filter': __name__ + ':block_all'})
        assert LiveUrlFilter.func == block_all

        WarcServer(config_file=None, custom_config={})
        assert LiveUrlFilter.func == None

    def test_allow(self):
        LiveUrlFilter.init(__name__ + ':allow_all')

        resp = self.testapp.get('/live/resource?url=http://httpbin.org/get')
        assert resp.headers['Warcserver-Source-Coll'] == 'live'
        assert b'HTTP/1.1 200 OK' in resp.body

        load_url = self.httpbin_local + 'get'
        assert [url for url, cdx in CALLS] == [load_url, load_url]
        assert CALLS[-1][1]['url'] == 'http://httpbin.org/get'
        assert CALLS[-1][1]['is_live'] == 'true'

    def test_block_live_index(self):
        LiveUrlFilter.init(__name__ + ':block_all')

        resp = self.testapp.get('/live/index?url=http://httpbin.org/get&output=json')
        assert resp.text == ''

        # no HEAD request when filtering
        with patch('requests.Session.head') as mock_head:
            resp = self.testapp.get('/live/index?url=http://httpbin.org/get&filter=status:200')
            assert resp.text == ''
            assert not mock_head.called

    def test_block_live_resource(self):
        LiveUrlFilter.init(__name__ + ':block_all')

        with patch.object(LiveWebLoader, '_do_request') as mock_request:
            resp = self.testapp.get('/live/resource?url=http://httpbin.org/get', status=404)
            assert not mock_request.called

        assert 'Warcserver-Source-Coll' not in resp.headers

    def test_filter_error_blocks(self):
        LiveUrlFilter.init(__name__ + ':raise_error')

        assert LiveUrlFilter.is_allowed('http://example.com/') == False

        self.testapp.get('/live/resource?url=http://httpbin.org/get', status=404)

    def test_block_remote_load(self):
        LiveUrlFilter.init(__name__ + ':block_target')

        loader = LiveWebLoader()

        cdx = CDXObject()
        cdx['url'] = 'http://blocked.example.com/'
        cdx['load_url'] = 'http://archive.example.com/web/2020id_/http://blocked.example.com/'

        with patch.object(LiveWebLoader, '_do_request') as mock_request:
            with pytest.raises(LiveResourceException):
                loader._do_request_with_redir_check('GET', cdx['load_url'], None, {}, {}, cdx)

            assert not mock_request.called

        assert CALLS == [(cdx['load_url'], cdx)]

    def _video_load(self):
        loader = VideoLoader()
        loader.ydl = MagicMock()
        loader.ydl.extract_info.return_value = {'formats': []}

        cdx = CDXObject()
        cdx['url'] = 'http://blocked.example.com/'
        cdx['load_url'] = 'http://archive.example.com/web/2020id_/http://blocked.example.com/'
        cdx['timestamp'] = '20200101000000'

        params = {'content_type': VideoLoader.CONTENT_TYPE}
        return loader, cdx, params

    def test_block_video_load(self):
        LiveUrlFilter.init(__name__ + ':block_target')

        loader, cdx, params = self._video_load()

        with pytest.raises(LiveResourceException):
            loader.load_resource(cdx, params)

        assert not loader.ydl.extract_info.called
        assert CALLS == [(cdx['load_url'], cdx)]

    def test_allow_video_load(self):
        LiveUrlFilter.init(__name__ + ':allow_all')

        loader, cdx, params = self._video_load()

        warc_headers, _, _ = loader.load_resource(cdx, params)
        assert warc_headers.get_header('Content-Type') == VideoLoader.CONTENT_TYPE

        loader.ydl.extract_info.assert_called_once_with(cdx['load_url'])
        assert CALLS == [(cdx['load_url'], cdx)]
