import tempfile
import os
import shutil
import json

from .testutils import to_path

from rezag.aggindexsource import DirectoryIndexSource, SimpleAggregator
from rezag.indexsource import MementoIndexSource


#=============================================================================
root_dir = None
orig_cwd = None
dir_loader = None

def setup_module():
    global root_dir
    root_dir = tempfile.mkdtemp()

    coll_A = to_path(root_dir + '/colls/A/indexes')
    coll_B = to_path(root_dir + '/colls/B/indexes')
    coll_C = to_path(root_dir + '/colls/C/indexes')

    os.makedirs(coll_A)
    os.makedirs(coll_B)
    os.makedirs(coll_C)

    dir_prefix = to_path(root_dir)
    dir_path ='colls/{coll}/indexes'

    shutil.copy(to_path('testdata/example.cdxj'), coll_A)
    shutil.copy(to_path('testdata/iana.cdxj'), coll_B)
    shutil.copy(to_path('testdata/dupes.cdxj'), coll_C)

    with open(to_path(root_dir) + 'somefile', 'w') as fh:
        fh.write('foo')

    global dir_loader
    dir_loader = DirectoryIndexSource(dir_prefix, dir_path)

    global orig_cwd
    orig_cwd = os.getcwd()
    os.chdir(root_dir)

    # use actually set dir
    root_dir = os.getcwd()

def teardown_module():
    global orig_cwd
    os.chdir(orig_cwd)

    global root_dir
    shutil.rmtree(root_dir)


def to_json_list(cdxlist, fields=['timestamp', 'load_url', 'filename', 'source']):
    return list([json.loads(cdx.to_json(fields)) for cdx in cdxlist])


def test_agg_no_coll_set():
    res = dir_loader(dict(url='example.com/'))
    assert(to_json_list(res) == [])


def test_agg_collA_found():
    res = dir_loader({'url': 'example.com/', 'param.coll': 'A'})

    exp = [{'source': 'colls/A/indexes', 'timestamp': '20160225042329', 'filename': 'example.warc.gz'}]

    assert(to_json_list(res) == exp)

def test_agg_collB():
    res = dir_loader({'url': 'example.com/', 'param.coll': 'B'})

    exp = []

    assert(to_json_list(res) == exp)

def test_agg_collB_found():
    res = dir_loader({'url': 'iana.org/', 'param.coll': 'B'})

    exp = [{'source': 'colls/B/indexes', 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'}]

    assert(to_json_list(res) == exp)


def test_extra_agg_collB():
    agg_source = SimpleAggregator({'dir': dir_loader})
    res = agg_source({'url': 'iana.org/', 'param.coll': 'B'})

    exp = [{'source': 'dir:colls/B/indexes', 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'}]

    assert(to_json_list(res) == exp)


def test_agg_all_found_1():
    res = dir_loader({'url': 'iana.org/', 'param.coll': '*'})

    exp = [
        {'source': 'colls/B/indexes', 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'},
        {'source': 'colls/C/indexes', 'timestamp': '20140127171238', 'filename': 'dupes.warc.gz'},
        {'source': 'colls/C/indexes', 'timestamp': '20140127171238', 'filename': 'dupes.warc.gz'},
    ]

    assert(to_json_list(res) == exp)


def test_agg_all_found_2():
    res = dir_loader({'url': 'example.com/', 'param.coll': '*'})

    exp = [
        {'source': 'colls/C/indexes', 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
        {'source': 'colls/C/indexes', 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
        {'source': 'colls/A/indexes', 'timestamp': '20160225042329', 'filename': 'example.warc.gz'}
    ]

    assert(to_json_list(res) == exp)



def test_agg_dir_and_memento():
    sources = {'ia': MementoIndexSource.from_timegate_url('http://web.archive.org/web/'),
               'local': dir_loader}
    agg_source = SimpleAggregator(sources)

    res = agg_source({'url': 'example.com/', 'param.local.coll': '*', 'closest': '20100512', 'limit': 6})

    exp = [
        {'source': 'ia', 'timestamp': '20100513052358', 'load_url': 'http://web.archive.org/web/20100513052358id_/http://example.com/'},
        {'source': 'ia', 'timestamp': '20100514231857', 'load_url': 'http://web.archive.org/web/20100514231857id_/http://example.com/'},
        {'source': 'ia', 'timestamp': '20100506013442', 'load_url': 'http://web.archive.org/web/20100506013442id_/http://example.com/'},
        {'source': 'local:colls/C/indexes', 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
        {'source': 'local:colls/C/indexes', 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
        {'source': 'local:colls/A/indexes', 'timestamp': '20160225042329', 'filename': 'example.warc.gz'}
    ]

    assert(to_json_list(res) == exp)


def test_agg_no_dir_1():
    res = dir_loader({'url': 'example.com/', 'param.coll': 'X'})

    exp = []

    assert(to_json_list(res) == exp)


def test_agg_no_dir_2():
    loader = DirectoryIndexSource(root_dir, '')
    res = loader({'url': 'example.com/', 'param.coll': 'X'})

    exp = []

    assert(to_json_list(res) == exp)


def test_agg_dir_sources_1():
    res = dir_loader.get_source_list({'url': 'example.com/', 'param.coll': '*'})
    exp = {'sources': {'colls/A/indexes': 'file',
                       'colls/B/indexes': 'file',
                       'colls/C/indexes': 'file'}
          }

    assert(res == exp)


def test_agg_dir_sources_2():
    res = dir_loader.get_source_list({'url': 'example.com/', 'param.coll': '[A,C]'})
    exp = {'sources': {'colls/A/indexes': 'file',
                       'colls/C/indexes': 'file'}
          }

    assert(res == exp)


def test_agg_dir_sources_single_dir():
    loader = DirectoryIndexSource('testdata/', '')
    res = loader.get_source_list({'url': 'example.com/'})

    exp = {'sources': {}}

    assert(res == exp)


