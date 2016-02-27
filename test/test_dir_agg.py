import tempfile
import os
import shutil
import json

from rezag.aggindexsource import DirectoryIndexAggregator, SimpleAggregator


#=============================================================================
root_dir = None
orig_cwd = None
dir_agg = None

def setup_module():
    global root_dir
    root_dir = tempfile.mkdtemp()

    coll_A = to_path(root_dir + '/colls/A/indexes')
    coll_B = to_path(root_dir + '/colls/B/indexes')

    os.makedirs(coll_A)
    os.makedirs(coll_B)

    dir_prefix = to_path(root_dir)
    dir_path ='colls/{coll}/indexes'

    shutil.copy(to_path('testdata/example.cdxj'), coll_A)
    shutil.copy(to_path('testdata/iana.cdxj'), coll_B)

    global dir_agg
    dir_agg = DirectoryIndexAggregator(dir_prefix, dir_path)

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


def to_path(path):
    if os.path.sep != '/':
        path = path.replace('/', os.path.sep)

    return path


def to_json_list(cdxlist, fields=['timestamp', 'load_url', 'filename', 'source']):
    return list([json.loads(cdx.to_json(fields)) for cdx in cdxlist])


def test_agg_no_coll_set():
    res = dir_agg(dict(url='example.com/'))
    assert(to_json_list(res) == [])


def test_agg_collA_found():
    res = dir_agg({'url': 'example.com/', 'param.coll': 'A'})

    exp = [{'source': 'colls/A/indexes', 'timestamp': '20160225042329', 'filename': 'example.warc.gz'}]

    assert(to_json_list(res) == exp)

def test_agg_collB():
    res = dir_agg({'url': 'example.com/', 'param.coll': 'B'})

    exp = []

    assert(to_json_list(res) == exp)

def test_agg_collB_found():
    res = dir_agg({'url': 'iana.org/', 'param.coll': 'B'})

    exp = [{'source': 'colls/B/indexes', 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'}]

    assert(to_json_list(res) == exp)


def test_agg_all_found():
    res = dir_agg({'url': 'iana.org/', 'param.coll': '*'})

    exp = [{'source': 'colls/B/indexes', 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'}]

    assert(to_json_list(res) == exp)


def test_extra_agg_all():
    agg_dir_agg = SimpleAggregator({'dir': dir_agg})
    res = agg_dir_agg({'url': 'iana.org/', 'param.coll': '*'})

    exp = [{'source': 'dir.colls/B/indexes', 'timestamp': '20140126200624', 'filename': 'iana.warc.gz'}]

    assert(to_json_list(res) == exp)



