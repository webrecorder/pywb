import time

import pytest
import webtest

from pywb.utils.wbexception import LiveResourceException, NotFoundException
from pywb.warcserver.http import DefaultAdapters
from pywb.warcserver.index.indexsource import BaseIndexSource
from pywb.warcserver.index.indexsource import LiveIndexSource, MementoIndexSource
from pywb.warcserver.index.indexsource import RemoteIndexSource, WBMementoIndexSource
from pywb.warcserver.index.indexsource import XmlQueryIndexSource
from pywb.warcserver.resource.responseloader import LiveWebLoader
from pywb.warcserver import warcserver
from pywb.warcserver.warcserver import WarcServer

from .testutils import SilentServer


# the requests are retried, so they give up after about 4 times this timeout
TIMEOUT = 0.2

# well below the time after which the SilentServer is closed
MAX_TIME = 5.0


# ============================================================================
@pytest.fixture
def server():
    server = SilentServer()
    yield server
    server.close()


@pytest.fixture
def short_default_timeout(monkeypatch):
    monkeypatch.setattr(DefaultAdapters, 'timeout', TIMEOUT)


@pytest.fixture
def long_default_timeout(monkeypatch):
    monkeypatch.setattr(DefaultAdapters, 'timeout', 60.0)


def assert_gives_up(func, exc_type=None):
    start = time.time()
    if exc_type:
        with pytest.raises(exc_type):
            func()
    else:
        func()

    assert time.time() - start < MAX_TIME


# ============================================================================
def test_default_timeout():
    assert DefaultAdapters.timeout > 0
    assert DefaultAdapters.get_timeout({}) == DefaultAdapters.timeout
    assert DefaultAdapters.get_timeout({'_timeout': 2.5}) == 2.5


@pytest.mark.parametrize('is_live', [True, False])
def test_live_loader_default_timeout(server, short_default_timeout, is_live):
    loader = LiveWebLoader()
    assert_gives_up(lambda: loader._do_request('GET', server.url, None, {}, {}, is_live),
                    LiveResourceException)


def test_live_loader_timeout_param(server, long_default_timeout):
    # the request must use the '_timeout' param, not the default
    loader = LiveWebLoader()
    params = {'_timeout': TIMEOUT}
    assert_gives_up(lambda: loader._do_request('GET', server.url, None, {}, params, True),
                    LiveResourceException)


def remote_cdx(url):
    return RemoteIndexSource(url + 'cdx?url={url}', url + '{timestamp}id_/{url}')


def memento(url):
    return MementoIndexSource.from_timegate_url(url)


def wb_memento(url):
    return WBMementoIndexSource(url + '{url}', url + 'timemap/link/{url}',
                                url + '{timestamp}im_/{url}')


@pytest.mark.parametrize('make_source, closest', [
    (remote_cdx, None),
    (remote_cdx, '20200101000000'),
    (memento, None),
    (memento, '20200101000000'),
    (wb_memento, '20200101000000'),
    (XmlQueryIndexSource, None),
])
def test_remote_index_default_timeout(server, short_default_timeout, make_source, closest):
    source = make_source(server.url)
    params = {'url': 'http://example.com/'}
    if closest:
        params['closest'] = closest

    assert_gives_up(lambda: source.load_index(params), NotFoundException)


def test_live_index_head_default_timeout(server, short_default_timeout):
    # with a filter, the live index makes a HEAD request for the status and mime
    params = {'url': server.url, 'key': b'1,0,0,127)/', 'filter': '=status:200'}
    assert_gives_up(lambda: LiveIndexSource().load_index(params))


# ============================================================================
def make_warcserver(collections):
    return webtest.TestApp(WarcServer(config_file=None,
                                      custom_config={'collections': collections,
                                                     'enable_auto_colls': False}))


@pytest.mark.parametrize('index, query', [
    ('$live', 'resource?url={url}'),
    ('cdx+{url}cdx', 'index?url=http://example.com/'),
])
def test_index_entry_timeout(server, long_default_timeout, index, query):
    # the 'timeout' of an 'index' entry must be used, not the default
    app = make_warcserver({'coll': {'index': index.format(url=server.url),
                                    'timeout': TIMEOUT}})

    url = '/coll/' + query.format(url=server.url)
    assert_gives_up(lambda: app.get(url, expect_errors=True))


# ============================================================================
class RecordTimeoutSource(BaseIndexSource):
    """Records the request timeout of each lookup, by source name"""
    timeouts = {}

    def __init__(self, name):
        self.name = name

    def load_index(self, params):
        self.timeouts.setdefault(self.name, set()).add(DefaultAdapters.get_timeout(params))
        raise NotFoundException(params['url'])

    @classmethod
    def init_from_string(cls, value):
        if value.startswith('record+'):
            return cls(value[len('record+'):])

    @classmethod
    def init_from_config(cls, config):
        return None


@pytest.fixture
def record_timeouts(monkeypatch):
    monkeypatch.setattr(warcserver, 'SOURCE_LIST',
                        [RecordTimeoutSource] + warcserver.SOURCE_LIST)
    monkeypatch.setattr(RecordTimeoutSource, 'timeouts', {})
    return RecordTimeoutSource.timeouts


def test_sequence_timeouts(record_timeouts):
    # each entry must use its own timeout, or the default,
    # not the one set by a previous entry
    app = make_warcserver({'seq': {'sequence': [
        {'index_group': {'group': 'record+group'}, 'timeout': 2},
        {'index': 'record+no_timeout'},
        {'index': 'record+timeout', 'timeout': 3},
        {'index': 'record+no_timeout_2'},
    ]}})

    res = app.get('/seq/resource?url=http://example.com/', expect_errors=True)
    assert res.status_int == 404

    default = DefaultAdapters.timeout
    assert record_timeouts == {'group': {2.0},
                               'no_timeout': {default},
                               'timeout': {3.0},
                               'no_timeout_2': {default}}
