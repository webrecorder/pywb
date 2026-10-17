import os
import sys
import time
import types

import pytest
from mock import patch

from pywb.warcserver.index.aggregator import SimpleAggregator, DirectoryIndexSource
from pywb.warcserver.index.cdxops import cdx_sort_closest
from pywb.warcserver.index.indexcache import IndexCache, UwsgiIndexCache, init_index_cache
from pywb.warcserver.index.indexsource import FileIndexSource, LiveIndexSource
from pywb.warcserver.index.zipnum import ZipNumIndexSource
from pywb.warcserver.test.testutils import TEST_CDX_PATH, to_path, get_test_dir
from pywb.warcserver.warcserver import WarcServer


TEST_ZIPNUM_PATH = to_path(get_test_dir() + '/zipcdx/zipnum-sample.idx')


# ============================================================================
class DictIndexCache(IndexCache):
    def __init__(self, config):
        super(DictIndexCache, self).__init__(config)
        self.store = {}
        self.gets = 0
        self.sets = 0

    def get(self, key):
        self.gets += 1
        return self.store.get(key)

    def set(self, key, value):
        self.sets += 1
        self.store[key] = value


# ============================================================================
class FakeUwsgi(types.ModuleType):
    def __init__(self, cache2):
        super(FakeUwsgi, self).__init__('uwsgi')
        self.opt = {'cache2': cache2} if cache2 else {}
        self.caches = {}

    def cache_get(self, key, cache):
        value, expires = self.caches.get((cache, key), (None, 0))
        return value if expires > time.time() else None

    def cache_update(self, key, value, expires, cache):
        self.caches[(cache, key)] = (value, time.time() + expires)
        return True


@pytest.fixture
def fake_uwsgi():
    def install(cache2=b'name=pywb-index,items=100,keysize=64,bitmap=1'):
        uwsgi = FakeUwsgi(cache2)
        patcher = patch.dict(sys.modules, {'uwsgi': uwsgi})
        patcher.start()
        patchers.append(patcher)
        return uwsgi

    patchers = []
    yield install
    for patcher in patchers:
        patcher.stop()


# ============================================================================
def file_source(name='iana.cdxj'):
    return FileIndexSource(os.path.join(TEST_CDX_PATH, name))


class ClosestWindowSource(FileIndexSource):
    """Reads only the captures closest to 'closest', up to the limit of the
    query, like an index source that seeks to 'closest'
    """
    def load_index(self, params):
        cdx_iter = super(ClosestWindowSource, self).load_index(params)
        window = params.get('limit') or params.get('_closest_limit')
        if not params.get('closest') or not window:
            return cdx_iter

        cdx_list = cdx_sort_closest(params['closest'], cdx_iter, limit=int(window))
        return iter(sorted(cdx_list, key=lambda cdx: cdx['timestamp']))


def new_agg(index_cache, sources=None, name=('coll',)):
    agg = SimpleAggregator(sources or {'iana': file_source()})
    if index_cache:
        assert index_cache.enable_for(agg, name)
    return agg


def query(agg, url, **params):
    params['url'] = url
    cdx_iter, errs = agg(params)
    return [(cdx['urlkey'], cdx['timestamp'], cdx['source'], cdx.to_json()) for cdx in cdx_iter], errs


def count_reads():
    return patch.object(FileIndexSource, 'load_index', autospec=True,
                        side_effect=FileIndexSource.load_index)


QUERIES = [
    ('http://www.iana.org/_js/2013.1/jquery.js', {}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'closest': '20140126201000'}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'closest': '20140126201000', 'limit': '1'}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'closest': '20140126201000', 'limit': '2'}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'from': '20140126200700', 'to': '20140126201000'}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'reverse': 'true', 'limit': '3'}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'filter': '!status:200'}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'content_type': 'application/x-javascript'}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'fl': 'timestamp,status'}),
    ('http://www.iana.org/_js/2013.1/jquery.js', {'collapseTime': '10'}),
    ('http://www.iana.org/', {'closest': '20140126200624'}),
    ('http://www.iana.org/not-archived', {}),
]


# ============================================================================
class TestIndexCache(object):
    @pytest.mark.parametrize('url, params', QUERIES)
    def test_same_results(self, url, params):
        no_cache = new_agg(None)
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)

        expected = query(no_cache, url, **params)
        assert query(agg, url, **params) == expected

        # the captures may not all be read with a limit
        if 'limit' in params:
            assert index_cache.sets == 0
            return

        assert index_cache.sets == 1

        # from the cache
        with count_reads() as reads:
            assert query(agg, url, **params) == expected
            assert reads.call_count == 0

    def test_all_queries_one_read(self):
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        no_cache = new_agg(None)

        jquery = [params for url, params in QUERIES if url.endswith('jquery.js')]

        with count_reads() as reads:
            for params in jquery:
                res = query(agg, 'http://www.iana.org/_js/2013.1/jquery.js', **params)
                assert res == query(no_cache, 'http://www.iana.org/_js/2013.1/jquery.js', **params)

            # one read for the cached aggregator, one per query for the other
            assert reads.call_count == 1 + len(jquery)

        assert index_cache.sets == 1

    def test_zipnum_and_dir(self):
        for source in (SimpleAggregator({'zipnum': ZipNumIndexSource(TEST_ZIPNUM_PATH, None)}),
                       DirectoryIndexSource(TEST_CDX_PATH)):
            index_cache = DictIndexCache({})
            assert index_cache.enable_for(source, ('coll',))

            res = query(source, 'http://www.iana.org/_css/2013.1/screen.css', closest='20140126201000')
            assert len(res[0]) > 1
            assert index_cache.sets == 1

            with count_reads() as reads:
                assert query(source, 'http://www.iana.org/_css/2013.1/screen.css', closest='20140126201000') == res
                assert reads.call_count == 0

            assert index_cache.sets == 1
            assert len(index_cache.store) == 1

    def test_not_stored_over_max_captures(self):
        index_cache = DictIndexCache({'max_captures': 5})
        agg = new_agg(index_cache)
        res = query(agg, 'http://www.iana.org/_js/2013.1/jquery.js')
        assert len(res[0]) > 5
        assert index_cache.sets == 0

        # max_captures is a maximum, so 5 captures are stored
        res = query(agg, 'http://www.iana.org/', closest='20140126200624')
        assert index_cache.sets == 1

    def test_not_stored_with_limit(self):
        # with fewer captures than 'limit', all captures were read
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        res = query(agg, 'http://www.iana.org/_js/2013.1/jquery.js', limit='4')
        assert len(res[0]) == 4
        assert index_cache.sets == 0

        # captures are only stored if fewer than the limit
        res = query(agg, 'http://www.iana.org/_js/2013.1/jquery.js', limit=str(len(QUERIES) * 10))
        assert index_cache.sets == 1

    def test_not_stored_with_closest_limit(self):
        # replay lookups have no 'limit', but a '_closest_limit' set by the
        # ResourceHandler, and the index source may read only that many
        # captures around 'closest'
        url = 'http://www.iana.org/_js/2013.1/jquery.js'
        sources = {'iana': ClosestWindowSource(os.path.join(TEST_CDX_PATH, 'iana.cdxj'))}
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache, sources)
        no_cache = new_agg(None, sources)

        for closest in ('20140126200625', '20140126201307', '20140126200625'):
            res = query(agg, url, closest=closest, _closest_limit='3')
            assert res == query(no_cache, url, closest=closest, _closest_limit='3')
            assert [cdx[1] for cdx in res[0]][0] == closest
            assert len(res[0]) == 3

        assert index_cache.sets == 0

        # with fewer captures than '_closest_limit', all captures were read
        res = query(agg, url, closest='20140126201307', _closest_limit='17')
        assert len(res[0]) == 16
        assert index_cache.sets == 1

        # an explicit limit takes precedence
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache, sources)
        res = query(agg, url, closest='20140126201307', limit='17', _closest_limit='3')
        assert len(res[0]) == 16
        assert index_cache.sets == 1

    def test_closest_limit_without_closest(self):
        # '_closest_limit' only applies to closest queries
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        res = query(agg, 'http://www.iana.org/_js/2013.1/jquery.js', _closest_limit='3')
        assert len(res[0]) == 16
        assert index_cache.sets == 1

    def test_not_stored_if_not_all_read(self):
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        cdx_iter, errs = agg({'url': 'http://www.iana.org/_js/2013.1/jquery.js'})
        next(cdx_iter)
        cdx_iter.close()
        assert index_cache.sets == 0

    def test_not_stored_with_errors(self):
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache, {'iana': file_source(),
                                    'missing': file_source('missing.cdxj')})
        res = query(agg, 'http://www.iana.org/_js/2013.1/jquery.js')
        assert res[1]
        assert index_cache.sets == 0

    def test_empty_stored(self):
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        assert query(agg, 'http://example.com/not-archived') == ([], {})
        assert index_cache.sets == 1

        with count_reads() as reads:
            assert query(agg, 'http://example.com/not-archived') == ([], {})
            assert reads.call_count == 0

    def test_prefix_not_cached(self):
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        res = query(agg, 'http://www.iana.org/_js/', matchType='prefix')
        assert len(res[0]) > 1
        res = query(agg, 'http://www.iana.org/_js/*')
        assert len(res[0]) > 1
        assert index_cache.gets == 0
        assert index_cache.sets == 0

    def test_mode_and_revisit_lookup_share_entry(self):
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        query(agg, 'http://www.iana.org/_js/2013.1/jquery.js', closest='2014', mode='resource')

        # lookup of the original of a revisit
        query(agg, 'https://www.iana.org/_js/2013.1/jquery.js', closest='20140126200625',
              filter=['!mime:warc/revisit', 'digest:AAW2RS7JB7HTF666XNZDQYJFA6PDQBPO'])

        query(agg, 'http://www.iana.org/_js/2013.1/jquery.js', output='json', mode='index')

        assert index_cache.sets == 1
        assert index_cache.gets == 3

    def test_names_and_sources_keys(self):
        index_cache = DictIndexCache({})
        agg_a = new_agg(index_cache, name=('A',))
        agg_b = new_agg(index_cache, {'iana': file_source('example.cdxj')}, name=('B',))

        res_a = query(agg_a, 'http://www.iana.org/')
        res_b = query(agg_b, 'http://www.iana.org/')
        assert len(res_a[0]) == 1
        assert res_b == ([], {})
        assert len(index_cache.store) == 2

        # sources selection
        query(agg_a, 'http://www.iana.org/', sources='iana')
        assert len(index_cache.store) == 3

    def test_bad_entry(self):
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        expected = query(agg, 'http://www.iana.org/')
        for key in index_cache.store:
            index_cache.store[key] = b'\x00bad'

        assert query(agg, 'http://www.iana.org/') == expected
        assert index_cache.sets == 2

    def test_cached_cdx_not_changed(self):
        index_cache = DictIndexCache({})
        agg = new_agg(index_cache)
        cdx = next(agg({'url': 'http://www.iana.org/'})[0])
        cdx['timestamp'] = '2000'
        assert next(agg({'url': 'http://www.iana.org/'})[0])['timestamp'] == '20140126200624'

    def test_can_cache(self):
        index_cache = DictIndexCache({})
        assert index_cache.can_cache(new_agg(None))
        assert index_cache.can_cache(DirectoryIndexSource(TEST_CDX_PATH))
        assert not index_cache.can_cache(LiveIndexSource())

        agg = new_agg(None, {'iana': file_source(), 'live': LiveIndexSource()})
        assert not index_cache.enable_for(agg, ('coll',))
        assert agg.index_cache is None


# ============================================================================
class TestInitIndexCache(object):
    def test_not_in_uwsgi(self):
        assert init_index_cache(None) is None
        assert init_index_cache(False) is None
        assert init_index_cache({'ttl': 10}) is None

    def test_uwsgi(self, fake_uwsgi):
        fake_uwsgi()
        index_cache = init_index_cache(None)
        assert isinstance(index_cache, UwsgiIndexCache)
        assert index_cache.cache_name == 'pywb-index'
        assert index_cache.ttl == 60
        assert index_cache.max_captures == 1000

        assert init_index_cache(False) is None

    def test_uwsgi_config(self, fake_uwsgi):
        fake_uwsgi([b'name=other,items=10', b'name=idx,items=100'])
        assert init_index_cache(None) is None

        index_cache = init_index_cache({'uwsgi_cache': 'idx', 'ttl': 5, 'max_captures': 10})
        assert index_cache.cache_name == 'idx'
        assert index_cache.ttl == 5
        assert index_cache.max_captures == 10

    def test_uwsgi_no_cache(self, fake_uwsgi):
        fake_uwsgi(None)
        assert init_index_cache(None) is None
        assert init_index_cache({}) is None

    def test_custom_class(self):
        index_cache = init_index_cache({'class': 'pywb.warcserver.index.test.test_index_cache:DictIndexCache',
                                        'ttl': 30})
        assert isinstance(index_cache, DictIndexCache)
        assert index_cache.ttl == 30

    def test_invalid(self):
        with pytest.raises(Exception):
            init_index_cache('uwsgi')

    def test_uwsgi_cache(self, fake_uwsgi):
        uwsgi = fake_uwsgi()
        index_cache = init_index_cache({'ttl': 1})
        agg = new_agg(index_cache)

        expected = query(agg, 'http://www.iana.org/')
        assert len(uwsgi.caches) == 1

        with count_reads() as reads:
            assert query(agg, 'http://www.iana.org/') == expected
            assert reads.call_count == 0

            # expired
            for key, (value, expires) in uwsgi.caches.items():
                uwsgi.caches[key] = (value, time.time() - 1)

            assert query(agg, 'http://www.iana.org/') == expected
            assert reads.call_count == 1


# ============================================================================
class TestWarcServerIndexCache(object):
    def test_warcserver(self, fake_uwsgi):
        fake_uwsgi()
        config = {
            'collections': {
                'iana': os.path.join(TEST_CDX_PATH, 'iana.cdxj'),
                'live': '$live',
                'seq': {'sequence': [
                    {'index': os.path.join(TEST_CDX_PATH, 'iana.cdxj'), 'name': 'a'},
                    {'index': os.path.join(TEST_CDX_PATH, 'example.cdxj'), 'name': 'a'},
                ]},
            },
            'index_cache': {'ttl': 10},
        }

        server = WarcServer(custom_config=config)
        assert server.index_cache.ttl == 10

        iana = server.fixed_routes['iana'].index_source
        assert iana.index_cache is server.index_cache
        assert iana.index_cache_name == ('iana',)

        live = server.fixed_routes['live'].index_source
        assert live.index_cache is None

        seq = [h.index_source for h in server.fixed_routes['seq'].handlers]
        assert [agg.index_cache_name for agg in seq] == [('seq', 0), ('seq', 1)]

    def test_warcserver_disabled(self, fake_uwsgi):
        fake_uwsgi()
        config = {
            'collections': {'iana': os.path.join(TEST_CDX_PATH, 'iana.cdxj')},
            'index_cache': False,
        }

        server = WarcServer(custom_config=config)
        assert server.index_cache is None
        assert server.fixed_routes['iana'].index_source.index_cache is None
