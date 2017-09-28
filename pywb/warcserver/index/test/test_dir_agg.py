import tempfile
import os
import shutil
import json

from pywb.warcserver.test.testutils import to_path, to_json_list, TempDirTests, BaseTestClass, TEST_CDX_PATH

from mock import patch

import time

from pywb.warcserver.index.aggregator import DirectoryIndexSource, CacheDirectoryIndexSource
from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.indexsource import MementoIndexSource


#=============================================================================
linkheader = """\
<http://example.com/>; rel="original", <http://web.archive.org/web/timemap/link/http://example.com/>; rel="timemap"; type="application/link-format", <http://web.archive.org/web/20020120142510/http://example.com/>; rel="first memento"; datetime="Sun, 20 Jan 2002 14:25:10 GMT", <http://web.archive.org/web/20100501123414/http://example.com/>; rel="prev memento"; datetime="Sat, 01 May 2010 12:34:14 GMT", <http://web.archive.org/web/20100514231857/http://example.com/>; rel="memento"; datetime="Fri, 14 May 2010 23:18:57 GMT", <http://web.archive.org/web/20100519202418/http://example.com/>; rel="next memento"; datetime="Wed, 19 May 2010 20:24:18 GMT", <http://web.archive.org/web/20160307200619/http://example.com/>; rel="last memento"; datetime="Mon, 07 Mar 2016 20:06:19 GMT"\
"""


def mock_link_header(*args, **kwargs):
    return linkheader


class TestDirAgg(TempDirTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestDirAgg, cls).setup_class()
        coll_A = to_path(cls.root_dir + '/colls/A/indexes')
        coll_B = to_path(cls.root_dir + '/colls/B/indexes')
        coll_C = to_path(cls.root_dir + '/colls/C/indexes')

        os.makedirs(coll_A)
        os.makedirs(coll_B)
        os.makedirs(coll_C)

        dir_prefix = os.path.join(cls.root_dir, 'colls')
        dir_path = '{coll}/indexes'
        dir_name = 'colls'

        shutil.copy(to_path(TEST_CDX_PATH + 'example2.cdxj'), coll_A)
        shutil.copy(to_path(TEST_CDX_PATH + 'iana.cdxj'), coll_B)
        shutil.copy(to_path(TEST_CDX_PATH + 'dupes.cdxj'), coll_C)

        with open(to_path(cls.root_dir) + '/somefile', 'w') as fh:
            fh.write('foo')

        cls.dir_loader = DirectoryIndexSource(dir_prefix, dir_path, dir_name)
        cls.cache_dir_loader = CacheDirectoryIndexSource(dir_prefix, dir_path, dir_name)

    def test_agg_no_coll_set(self):
        res, errs = self.dir_loader(dict(url='example.com/'))
        assert(to_json_list(res) == [])
        assert(errs == {})

    def test_agg_collA_found(self):
        res, errs = self.dir_loader({'url': 'example.com/', 'param.coll': 'A'})

        exp = [{'source': to_path('colls:A/indexes/example2.cdxj'), 'timestamp': '20160225042329', 'filename': 'example2.warc.gz'}]

        assert(to_json_list(res) == exp)
        assert(errs == {})

    def test_agg_collB(self):
        res, errs = self.dir_loader({'url': 'example.com/', 'param.coll': 'B'})

        exp = []

        assert(to_json_list(res) == exp)
        assert(errs == {})

    def test_agg_collB_found(self):
        res, errs = self.dir_loader({'url': 'iana.org/', 'param.coll': 'B'})

        exp = [{'source': to_path('colls:B/indexes/iana.cdxj'), 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'}]

        assert(to_json_list(res) == exp)
        assert(errs == {})


    def test_extra_agg_collB(self):
        agg_source = SimpleAggregator({'dir': self.dir_loader})
        res, errs = agg_source({'url': 'iana.org/', 'param.coll': 'B'})

        exp = [{'source': to_path('dir:colls:B/indexes/iana.cdxj'), 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'}]

        assert(to_json_list(res) == exp)
        assert(errs == {})


    def test_agg_all_found_1(self):
        res, errs = self.dir_loader({'url': 'iana.org/', 'param.coll': '*'})

        exp = [
            {'source': to_path('colls:B/indexes/iana.cdxj'), 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'},
            {'source': to_path('colls:C/indexes/dupes.cdxj'), 'timestamp': '20140127171238', 'filename': 'dupes.warc.gz'},
            {'source': to_path('colls:C/indexes/dupes.cdxj'), 'timestamp': '20140127171238', 'filename': 'dupes.warc.gz'},
        ]

        assert(to_json_list(res) == exp)
        assert(errs == {})


    def test_agg_all_found_2(self):
        res, errs = self.dir_loader({'url': 'example.com/', 'param.coll': '*'})

        exp = [
            {'source': to_path('colls:C/indexes/dupes.cdxj'), 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
            {'source': to_path('colls:C/indexes/dupes.cdxj'), 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
            {'source': to_path('colls:A/indexes/example2.cdxj'), 'timestamp': '20160225042329', 'filename': 'example2.warc.gz'}
        ]

        assert(to_json_list(res) == exp)
        assert(errs == {})

    @patch('pywb.warcserver.index.indexsource.MementoIndexSource.get_timegate_links', mock_link_header)
    def test_agg_dir_and_memento(self):
        sources = {'ia': MementoIndexSource.from_timegate_url('http://web.archive.org/web/'),
                   'local': self.dir_loader}
        agg_source = SimpleAggregator(sources)

        res, errs = agg_source({'url': 'example.com/', 'param.local.coll': '*', 'closest': '20100512', 'limit': 6})

        exp = [
            {'source': 'ia', 'timestamp': '20100514231857', 'load_url': 'http://web.archive.org/web/20100514231857id_/http://example.com/'},
            {'source': 'ia', 'timestamp': '20100519202418', 'load_url': 'http://web.archive.org/web/20100519202418id_/http://example.com/'},
            {'source': 'ia', 'timestamp': '20100501123414', 'load_url': 'http://web.archive.org/web/20100501123414id_/http://example.com/'},
            {'source': to_path('local:colls:C/indexes/dupes.cdxj'), 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
            {'source': to_path('local:colls:C/indexes/dupes.cdxj'), 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
            {'source': to_path('local:colls:A/indexes/example2.cdxj'), 'timestamp': '20160225042329', 'filename': 'example2.warc.gz'}
        ]

        assert(to_json_list(res) == exp)
        assert(errs == {})


    def test_agg_no_dir_1(self):
        res, errs = self.dir_loader({'url': 'example.com/', 'param.coll': 'X'})

        exp = []

        assert(to_json_list(res) == exp)
        assert(errs == {})


    def test_agg_no_dir_2(self):
        loader = DirectoryIndexSource(self.root_dir, '')
        res, errs = loader({'url': 'example.com/', 'param.coll': 'X'})

        exp = []

        assert(to_json_list(res) == exp)
        assert(errs == {})


    def test_agg_dir_sources_1(self):
        res = self.dir_loader.get_source_list({'url': 'example.com/', 'param.coll': '*'})
        exp = {'sources': {to_path('colls:A/indexes/example2.cdxj'): 'file',
                           to_path('colls:B/indexes/iana.cdxj'): 'file',
                           to_path('colls:C/indexes/dupes.cdxj'): 'file'}
              }

        assert(res == exp)

    def test_agg_dir_sources_2(self):
        res = self.dir_loader.get_source_list({'url': 'example.com/', 'param.coll': '[A,C]'})
        exp = {'sources': {to_path('colls:A/indexes/example2.cdxj'): 'file',
                           to_path('colls:C/indexes/dupes.cdxj'): 'file'}
              }

        assert(res == exp)


    def test_agg_dir_sources_single_dir(self):
        loader = DirectoryIndexSource(os.path.join(self.root_dir, 'colls', 'A', 'indexes'), '')
        res = loader.get_source_list({'url': 'example.com/'})

        exp = {'sources': {'example2.cdxj': 'file'}}

        assert(res == exp)


    def test_agg_dir_sources_not_found_dir(self):
        loader = DirectoryIndexSource(os.path.join(self.root_dir, 'colls', 'Z', 'indexes'), '')
        res = loader.get_source_list({'url': 'example.com/'})

        exp = {'sources': {}}

        assert(res == exp)



    def test_cache_dir_sources_1(self):
        exp = {'sources': {to_path('colls:A/indexes/example2.cdxj'): 'file',
                           to_path('colls:B/indexes/iana.cdxj'): 'file',
                           to_path('colls:C/indexes/dupes.cdxj'): 'file'}
              }

        res = self.cache_dir_loader.get_source_list({'url': 'example.com/', 'param.coll': '*'})
        assert(res == exp)

        res = self.cache_dir_loader.get_source_list({'url': 'example.com/', 'param.coll': '*'})
        assert(res == exp)

        new_file = os.path.join(self.root_dir, to_path('colls/C/indexes/empty.cdxj'))

        # ensure new file is created at least a second later
        time.sleep(1.0)

        with open(new_file, 'a') as fh:
            os.utime(new_file, None)

        res = self.cache_dir_loader.get_source_list({'url': 'example.com/', 'param.coll': '*'})

        # New File Included
        exp['sources'][to_path('colls:C/indexes/empty.cdxj')] = 'file'
        assert(res == exp)
