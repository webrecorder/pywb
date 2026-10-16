from datetime import datetime, timedelta
import json
import os

import pytest
import webtest

from pywb.utils.wbexception import NotFoundException
from pywb.warcserver.basewarcserver import BaseWarcServer
from pywb.warcserver.handlers import ResourceHandler, HandlerSeq
from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.indexsource import FileIndexSource
from pywb.warcserver.index.query import CDXQuery
from pywb.warcserver.warcserver import WarcServer


NUM_CAPTURES = 250
NUM_FUZZY_CAPTURES = 150

URL = 'http://example.com/'
FUZZY_URL = 'http://example.com/script.js?v=req'

START = datetime(2020, 1, 1)


def timestamp(i):
    return (START + timedelta(hours=i)).strftime('%Y%m%d%H%M%S')


CLOSEST = timestamp(NUM_CAPTURES // 2)


# ============================================================================
@pytest.fixture(scope='module')
def index_source(tmp_path_factory):
    """ An index with NUM_CAPTURES captures of URL, and NUM_FUZZY_CAPTURES
    captures of urls only matching FUZZY_URL with a fuzzy lookup
    """
    def cdxj_line(urlkey, ts, url):
        cdx = {'url': url, 'mime': 'text/html', 'status': '200',
               'length': '100', 'offset': '0', 'filename': 'missing.warc.gz'}
        return '{0} {1} {2}\n'.format(urlkey, ts, json.dumps(cdx))

    lines = [cdxj_line('com,example)/', timestamp(i), URL)
             for i in range(NUM_CAPTURES)]

    lines += [cdxj_line('com,example)/script.js?v={0:04d}'.format(i), timestamp(i),
                        'http://example.com/script.js?v={0:04d}'.format(i))
              for i in range(NUM_FUZZY_CAPTURES)]

    path = os.path.join(str(tmp_path_factory.mktemp('closest_limit')), 'index.cdxj')
    with open(path, 'w') as fh:
        fh.writelines(sorted(lines))

    return SimpleAggregator({'test': FileIndexSource(path)})


# ============================================================================
class FailingLoader(object):
    """ Resource loader that never loads a capture, recording each one tried
    """
    def __init__(self):
        self.tried = []

    def __call__(self, cdx, params):
        self.tried.append(cdx['timestamp'])
        raise NotFoundException('not loaded: ' + cdx['timestamp'])


def make_app(handler):
    app = BaseWarcServer()
    app.add_route('/coll', handler)
    return webtest.TestApp(app)


def make_handler(index_source, closest_limit=None):
    loader = FailingLoader()
    handler = ResourceHandler(index_source, [loader], closest_limit=closest_limit)
    return handler, loader


# ============================================================================
class TestResourceClosestLimit(object):
    def test_closest_no_limit(self, index_source):
        handler, loader = make_handler(index_source, closest_limit=10)
        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST}, status=404)

        assert len(loader.tried) == 10
        # still the closest captures, closest first
        assert loader.tried[0] == CLOSEST
        assert set(loader.tried) <= set(timestamp(NUM_CAPTURES // 2 + i) for i in range(-5, 6))

    def test_closest_explicit_limit(self, index_source):
        handler, loader = make_handler(index_source, closest_limit=10)
        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST, 'limit': '3'},
                              status=404)

        assert len(loader.tried) == 3

    def test_closest_explicit_limit_above(self, index_source):
        handler, loader = make_handler(index_source, closest_limit=10)
        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST, 'limit': '200'},
                              status=404)

        assert len(loader.tried) == 200

    def test_no_closest(self, index_source):
        handler, loader = make_handler(index_source, closest_limit=10)
        make_app(handler).get('/coll/resource', params={'url': URL}, status=404)

        assert len(loader.tried) == NUM_CAPTURES

    @pytest.mark.parametrize('closest_limit', [None, 0, '0', ''])
    def test_disabled(self, index_source, closest_limit):
        handler, loader = make_handler(index_source, closest_limit=closest_limit)
        assert handler.closest_limit is None

        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST}, status=404)

        assert len(loader.tried) == NUM_CAPTURES

    def test_string_value(self, index_source):
        handler, loader = make_handler(index_source, closest_limit='7')
        assert handler.closest_limit == 7

        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST}, status=404)

        assert len(loader.tried) == 7

    def test_index_mode(self, index_source):
        handler, loader = make_handler(index_source, closest_limit=10)
        resp = make_app(handler).get('/coll/index', params={'url': URL, 'closest': CLOSEST})

        assert len(resp.text.splitlines()) == NUM_CAPTURES
        assert loader.tried == []

    def test_fuzzy_keeps_fuzzy_search_limit(self, index_source):
        # fuzzy lookups have no closest and keep their own limit (fuzzy_search_limit: 100)
        handler, loader = make_handler(index_source, closest_limit=10)
        make_app(handler).get('/coll/resource', params={'url': FUZZY_URL, 'closest': CLOSEST}, status=404)

        assert len(loader.tried) == 100

    def test_params_not_shared_in_sequence(self, index_source):
        first, first_loader = make_handler(index_source, closest_limit=10)
        second, second_loader = make_handler(index_source)
        third, third_loader = make_handler(index_source, closest_limit=20)

        app = make_app(HandlerSeq([first, second, third]))
        app.get('/coll/resource', params={'url': URL, 'closest': CLOSEST}, status=404)

        assert len(first_loader.tried) == 10
        assert len(second_loader.tried) == NUM_CAPTURES
        assert len(third_loader.tried) == 20


# ============================================================================
class TestCDXQueryClosestLimit(object):
    def query(self, **params):
        params.setdefault('url', URL)
        return CDXQuery(params)

    def test_default(self):
        assert self.query().limit == 100000
        assert self.query(closest=CLOSEST).limit == 100000

    def test_closest_limit(self):
        assert self.query(closest=CLOSEST, _closest_limit=10).limit == 10

    def test_closest_limit_no_closest(self):
        assert self.query(_closest_limit=10).limit == 100000

    def test_explicit_limit_wins(self):
        assert self.query(closest=CLOSEST, _closest_limit=10, limit='500').limit == 500
        assert self.query(closest=CLOSEST, _closest_limit=10, limit='5').limit == 5


# ============================================================================
class TestWarcServerClosestLimit(object):
    def init_warcserver(self, tmp_path, **config):
        root = tmp_path / 'collections'
        (root / 'auto').mkdir(parents=True)
        config['collections_root'] = str(root)
        return WarcServer(config_file=None, custom_config=config)

    def test_default(self, tmp_path):
        warcserver = self.init_warcserver(tmp_path, collections={'live': '$live'})

        assert warcserver.auto_handler.closest_limit == 100
        assert warcserver.fixed_routes['live'].closest_limit == 100

    def test_top_level(self, tmp_path):
        warcserver = self.init_warcserver(tmp_path, closest_limit=20,
                                          collections={'live': '$live',
                                                       'live_dict': {'index': '$live'}})

        assert warcserver.auto_handler.closest_limit == 20
        assert warcserver.fixed_routes['live'].closest_limit == 20
        assert warcserver.fixed_routes['live_dict'].closest_limit == 20

    def test_disabled(self, tmp_path):
        warcserver = self.init_warcserver(tmp_path, closest_limit=None,
                                          collections={'live': '$live'})

        assert warcserver.auto_handler.closest_limit is None
        assert warcserver.fixed_routes['live'].closest_limit is None

    def test_per_collection(self, tmp_path):
        warcserver = self.init_warcserver(tmp_path, closest_limit=20,
                                          collections={'five': {'index': '$live', 'closest_limit': 5},
                                                       'off': {'index': '$live', 'closest_limit': 0},
                                                       'group': {'index_group': {'live': '$live'},
                                                                 'closest_limit': 30},
                                                       'seq': {'sequence': [
                                                           {'index': '$live', 'closest_limit': 40},
                                                           {'index': '$live'}]}})

        assert warcserver.auto_handler.closest_limit == 20
        assert warcserver.fixed_routes['five'].closest_limit == 5
        assert warcserver.fixed_routes['off'].closest_limit is None
        assert warcserver.fixed_routes['group'].closest_limit == 30

        seq = warcserver.fixed_routes['seq']
        assert isinstance(seq, HandlerSeq)
        assert [h.closest_limit for h in seq.handlers] == [40, 20]
