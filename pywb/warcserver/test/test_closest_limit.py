from datetime import datetime, timedelta
import json
import os

import pytest
import webtest

from pywb.utils.wbexception import NotFoundException
from pywb.warcserver.basewarcserver import BaseWarcServer
from pywb.warcserver.handlers import ResourceHandler
from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.indexsource import FileIndexSource
from pywb.warcserver.index.query import CDXQuery


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


def make_handler(index_source, closest_limit=10):
    loader = FailingLoader()
    handler = ResourceHandler(index_source, [loader])
    # the default limit can be changed by code, eg. in a subclass
    handler.CLOSEST_LIMIT = closest_limit
    return handler, loader


# ============================================================================
class TestResourceClosestLimit(object):
    def test_default(self, index_source):
        loader = FailingLoader()
        handler = ResourceHandler(index_source, [loader])
        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST}, status=404)

        assert ResourceHandler.CLOSEST_LIMIT == 100
        assert len(loader.tried) == 100
        assert loader.tried[0] == CLOSEST

    def test_closest_no_limit(self, index_source):
        handler, loader = make_handler(index_source)
        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST}, status=404)

        assert len(loader.tried) == 10
        # still the closest captures, closest first
        assert loader.tried[0] == CLOSEST
        assert set(loader.tried) <= set(timestamp(NUM_CAPTURES // 2 + i) for i in range(-5, 6))

    def test_closest_explicit_limit(self, index_source):
        handler, loader = make_handler(index_source)
        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST, 'limit': '3'},
                              status=404)

        assert len(loader.tried) == 3

    def test_closest_explicit_limit_above(self, index_source):
        handler, loader = make_handler(index_source)
        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST, 'limit': '200'},
                              status=404)

        assert len(loader.tried) == 200

    def test_no_closest(self, index_source):
        handler, loader = make_handler(index_source)
        make_app(handler).get('/coll/resource', params={'url': URL}, status=404)

        assert len(loader.tried) == NUM_CAPTURES

    @pytest.mark.parametrize('closest_limit', [None, 0])
    def test_disabled(self, index_source, closest_limit):
        handler, loader = make_handler(index_source, closest_limit=closest_limit)
        make_app(handler).get('/coll/resource', params={'url': URL, 'closest': CLOSEST}, status=404)

        assert len(loader.tried) == NUM_CAPTURES

    def test_index_mode(self, index_source):
        handler, loader = make_handler(index_source)
        resp = make_app(handler).get('/coll/index', params={'url': URL, 'closest': CLOSEST})

        assert len(resp.text.splitlines()) == NUM_CAPTURES
        assert loader.tried == []

    def test_fuzzy_keeps_fuzzy_search_limit(self, index_source):
        # fuzzy lookups have no closest and keep their own limit (fuzzy_search_limit: 100)
        handler, loader = make_handler(index_source)
        make_app(handler).get('/coll/resource', params={'url': FUZZY_URL, 'closest': CLOSEST}, status=404)

        assert len(loader.tried) == 100


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
