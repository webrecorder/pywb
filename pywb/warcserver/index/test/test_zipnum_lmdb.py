import gzip
import itertools
import multiprocessing
import os
import random
import shutil
import subprocess
import sys

from io import BytesIO, StringIO

import pytest

lmdb = pytest.importorskip('lmdb')

from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter
from werkzeug.test import Client
from werkzeug.wrappers import Response

import pywb
from pywb import get_test_dir
from pywb.indexer.cdxindexer import write_cdx_index
from pywb.indexer.lmdbzipnumidx import load
from pywb.utils import binsearch
from pywb.utils.canonicalize import canonicalize
from pywb.utils.loaders import read_last_line
from pywb.warcserver.index import lmdbidx
from pywb.warcserver.index.cdxobject import CDXException
from pywb.warcserver.index.lmdbidx import LMDBIdxReader
from pywb.warcserver.index.zipnum import IdxFileReader, ZipNumIndexSource
from pywb.warcserver.warcserver import WarcServer, init_index_agg, init_index_source


TEST_ZIPNUM_DIR = get_test_dir() + 'zipcdx/'

LONG_PATH = 'http://example.com/long/' + 'a' * 600


@pytest.fixture(autouse=True)
def close_environments():
    yield
    lmdbidx.close_environments()


@pytest.fixture
def env_path(tmp_path):
    return str(tmp_path / 'idx.lmdb')


def lmdb_uri(env_path, db_name='test'):
    return 'lmdb://{0}?db={1}'.format(env_path, db_name)


def load_idx(env_path, db_name, idx, **kwargs):
    return load(env_path, db_name, idx, out=StringIO(), **kwargs)


# ============================================================================
# the sample ZipNum index, with the queries of test_zipnum.py
SAMPLE_QUERIES = [
    dict(url='http://iana.org'),
    dict(url='http://example.com/'),
    dict(url='http://iana.org/domains/', matchType='prefix', showPagedIndex=True),
    dict(url='http://iana.org/domains/*'),
    dict(url='http://iana.org/domains/', matchType='domain', showPagedIndex=True, pageSize=4, page=0),
    dict(url='*.iana.org/path_part_ignored/', showPagedIndex=True, pageSize=4),
    dict(url='http://iana.org/domains/', matchType='domain', output='json', showPagedIndex=True, pageSize=4, page=1),
    dict(url='http://iana.org/domains/', matchType='domain', showPagedIndex=True, pageSize=4, page=9),
    dict(url='http://iana.org/domains/', matchType='domain', pageSize=4, page=9),
    dict(url='http://iana.org/domains/', matchType='domain', reverse=True, pageSize=4, page=9),
    dict(url='http://iana.org/domains/', matchType='domain', showPagedIndex=True, pageSize=4, page=10),
    dict(url='http://iana.org/time-zones*'),
    dict(url='http://iana.org/time-zones/*'),
    dict(url='http://iana.org/time-zones/Y'),
    dict(url='http://aaa.aaa/', matchType='exact', showPagedIndex=True),
    dict(url='http://aaa.aaa/', matchType='domain', showPagedIndex=True),
    dict(url='http://aaa.zz/', matchType='domain', showPagedIndex=True),
    dict(url='http://aaa.zz/', matchType='domain'),
    dict(url='http://iana.org/domains/example', matchType='exact', showNumPages=True),
    dict(url='http://iana.org/domains/', matchType='domain', showNumPages=True),
    dict(url='http://iana.org/domains/', matchType='domain', pageSize=4, showNumPages=True),
    dict(url='*.iana.org', pageSize='4', showNumPages=True),
    dict(url='iana.org/domains/int/blah', pageSize=4, showNumPages=True),
    dict(url='*.foo.bar', showNumPages=True),
    dict(url='http://aaa.zz/', matchType='domain', showNumPages=True),
    dict(url='*.iana.org', pageSize='4', showNumPages=True, filter='=status:200'),
    dict(url='*.iana.org', pageSize='4', showNumPages=True, closest='20140126000000'),
    dict(url='http://iana.org/', closest='20140126201000', limit=2),
    dict(url='http://iana.org/domains/example', matchType='exact', pageSize='not-an-integer'),
    dict(url='http://iana.org/domains/example', matchType='exact', page='not-an-integer'),
]


def sample_results(config, params):
    params = dict(params, output=params.get('output', 'raw'), nosource='true')
    try:
        cdx_iter, errs = init_index_agg({'zip': config})(params)
        return [x.to_json() if params['output'] == 'json' else str(x) for x in cdx_iter]
    except Exception as e:
        return ['error: {0}: {1}'.format(type(e).__name__, e)]


def test_sample_zipnum_same_results_as_the_idx_file(tmp_path, env_path):
    sample_idx = TEST_ZIPNUM_DIR + 'zipnum-sample.idx'
    for name in ('zipnum-sample.idx', 'zipnum-sample.loc', 'zipnum-sample.cdx.gz'):
        shutil.copy(TEST_ZIPNUM_DIR + name, str(tmp_path))
    idx = str(tmp_path / 'zipnum-sample.idx')

    stats = load_idx(env_path, 'sample', idx)
    assert (stats.lines, stats.added) == (38, 38)
    # only the LMDB .idx can be used
    os.remove(idx)

    file_config = {'type': 'zipnum', 'path': sample_idx}
    lmdb_config = {'type': 'zipnum', 'path': idx, 'lmdb': lmdb_uri(env_path, 'sample')}

    for params in SAMPLE_QUERIES:
        expected = sample_results(file_config, params)
        assert sample_results(lmdb_config, params) == expected, params

    assert sample_results(lmdb_config, dict(url='http://iana.org/domains/', matchType='domain',
                                            showNumPages=True)) == [str({"pages": 4, "pageSize": 10, "blocks": 38})]
    assert len(sample_results(lmdb_config, dict(url='http://iana.org'))) == 3


def test_sample_bad_idx_is_rejected(env_path):
    # zipnum-bad.idx doesn't have the line numbers
    with pytest.raises(ValueError, match='line 3: the line number field is 2'):
        load_idx(env_path, 'bad', TEST_ZIPNUM_DIR + 'zipnum-bad.idx')


# ============================================================================
# a generated ZipNum index, with first fields longer than the key prefix and
# blocks starting with the same first field
def cdxj_line(url, timestamp, **fields):
    json_fields = ', '.join('"{0}": "{1}"'.format(name, value) for name, value in dict(url=url, **fields).items())
    return '{0} {1} {{{2}}}\n'.format(canonicalize(url), timestamp, json_fields).encode('utf-8')


def build_zipnum(directory, lines, lines_per_block, base='test', shards=2):
    """ Write a ZipNum index of the sorted CDXJ lines: <base>-NN.cdx.gz shards
    of gzip blocks, the <base>.idx with the 1-based line numbers and the
    <base>.loc. Return the .idx path
    """
    os.makedirs(directory, exist_ok=True)
    blocks = [lines[i:i + lines_per_block] for i in range(0, len(lines), lines_per_block)]
    blocks_per_shard = -(-len(blocks) // shards)
    idx_lines = []
    loc_lines = []
    for shard in range(shards):
        part = '{0}-{1:02d}.cdx.gz'.format(base, shard + 1)
        loc_lines.append('{0}\t{0}\n'.format(part))
        with open(os.path.join(directory, part), 'wb') as out:
            for block in blocks[shard * blocks_per_shard:(shard + 1) * blocks_per_shard]:
                data = gzip.compress(b''.join(block), mtime=0)
                first_field = block[0].partition(b' {')[0]
                idx_lines.append(b'%s\t%s\t%d\t%d\t%d\n' % (first_field, part.encode('ascii'), out.tell(),
                                                             len(data), len(idx_lines) + 1))
                out.write(data)

    idx = os.path.join(directory, base + '.idx')
    with open(idx, 'wb') as out:
        out.writelines(idx_lines)
    with open(os.path.join(directory, base + '.loc'), 'w') as out:
        out.writelines(loc_lines)
    return idx


def sample_urls():
    urls = ['http://{0}/page{1}'.format(host, i) for host in ('example.com', 'sub.example.com', 'example.org',
                                                             'example.pt', 'www.example.pt') for i in range(40)]
    urls += ['http://example.com/page{0}?q={1}'.format(i, j) for i in range(3) for j in range(5)]
    # first fields longer than the key prefix, some only different after it
    urls += [LONG_PATH + '/{0}'.format(i) for i in range(12)]
    urls += ['http://example.com/long/{0}/{1}'.format('b' * 495, i) for i in range(4)]
    urls += ['http://example.com/nação/{0}'.format(i) for i in range(3)]
    return urls


def sample_cdxj(rnd):
    lines = []
    for url in sample_urls():
        for _ in range(rnd.choice([1, 1, 2, 3, 8, 30])):
            lines.append(cdxj_line(url, rnd.randint(19960101000000, 20251231235959), status='200'))
    # blocks starting with the same first field, with offsets that are not sorted as text
    for i in range(1000):
        lines.append(cdxj_line('http://example.org/same', 20190101000000, n=i))
    for i in range(40):
        lines.append(cdxj_line(LONG_PATH + '/same', 20200101000000, n=i))
    return sorted(lines)


def queries(rnd):
    urls = sample_urls()
    urls += ['http://example.org/same', LONG_PATH + '/same', LONG_PATH, 'http://example.com/long/',
             'http://example.com/page1/missing', 'http://example.com/pagf', 'http://other.example.com/',
             'http://a.ac/', 'http://zz.zz/', LONG_PATH + '/missing']
    for url in urls:
        yield {'url': url}
        yield {'url': url, 'showPagedIndex': 'true'}
    for url in rnd.sample(urls, 60) + ['http://example.org/same', LONG_PATH]:
        for match_type in ('prefix', 'host', 'domain'):
            yield {'url': url, 'matchType': match_type}
            yield {'url': url, 'matchType': match_type, 'showNumPages': 'true'}
            yield {'url': url, 'matchType': match_type, 'showNumPages': 'true', 'pageSize': '2'}
            for page in range(4):
                yield {'url': url, 'matchType': match_type, 'page': str(page), 'pageSize': '2'}
                yield {'url': url, 'matchType': match_type, 'page': str(page), 'pageSize': '3',
                       'showPagedIndex': 'true'}
    yield {'url': 'http://example.com/', 'matchType': 'prefix', 'page': 'x'}


def results(source, params):
    try:
        return [str(line) for line in source.load_index(dict(params))]
    except CDXException as e:
        return ['error: ' + str(e)]


def make_sources(idx, env_path, db_name='test', **config):
    file_source = ZipNumIndexSource(idx, dict(config, type='zipnum', path=idx))
    lmdb_source = ZipNumIndexSource(idx, dict(config, type='zipnum', path=idx, lmdb=lmdb_uri(env_path, db_name)))
    return file_source, lmdb_source


@pytest.fixture(params=[1, 4, 13])
def zipnum(request, tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1675)), request.param)
    load_idx(env_path, 'test', idx)
    return idx


def test_sample_has_long_and_repeated_keys(zipnum):
    with open(zipnum, 'rb') as reader:
        lines = reader.read().splitlines()
    first_fields = [line.partition(b'\t')[0] for line in lines]

    assert max(len(field) for field in first_fields) > 600
    assert len(first_fields) - len(set(first_fields)) > 10
    # repeated first fields with offsets that don't sort as text
    assert any(line > next_line for line, next_line in zip(lines, lines[1:]))


@pytest.mark.parametrize('max_blocks', [2, 10])
def test_same_results_as_the_idx_file(zipnum, env_path, max_blocks):
    file_source, lmdb_source = make_sources(zipnum, env_path, max_blocks=max_blocks)
    rnd = random.Random(1675)

    compared = 0
    for params in queries(rnd):
        expected = results(file_source, params)
        assert results(lmdb_source, params) == expected, params
        compared += bool(expected)
    assert compared > 1000


def test_search_same_lines_as_binsearch(zipnum, env_path):
    _, lmdb_source = make_sources(zipnum, env_path)
    with open(zipnum, 'rb') as reader:
        lines = reader.read().splitlines()
    # the keys of the queries, without tabs, as the lines with the same first
    # field may not be sorted after it
    first_fields = [line.partition(b'\t')[0] for line in lines]
    keys = [field[:length] for field in first_fields for length in (5, 20, 40, 300, 499, 500, 501, 520, -2)]
    keys += [field + suffix for field in first_fields for suffix in (b'', b'\x00', b' ', b'!')]
    keys += [b'', b'0', b'~']

    for key in keys:
        reader = lmdb_source.open_idx(zipnum)
        assert isinstance(reader, LMDBIdxReader)
        for prev_size in (0, 1, 2):
            with open(zipnum, 'rb') as idx_file:
                expected = list(itertools.islice(binsearch.search(idx_file, key, prev_size=prev_size), 20))
            lines = list(itertools.islice(reader.search(key, prev_size), len(expected) + prev_size))
            # binsearch reads from the start of a 8 KiB block, so it may have
            # less previous lines, but always the one used (prev_size=1) when
            # there is a line >= key, or without one, the last line or none
            skipped = [i for i in range(prev_size + 1) if lines[i:i + len(expected)] == expected]
            assert skipped, (key, prev_size)
            if prev_size == 0 or prev_size == 1 and expected:
                assert lines[:len(expected)] == expected, (key, prev_size)

        end = key + b'!'
        with open(zipnum, 'rb') as idx_file:
            expected = list(itertools.islice(binsearch.iter_range(idx_file, key, end, prev_size=1), 20))
        lines = list(itertools.islice(reader.iter_range(key, end, 1), 20))
        assert lines == expected or not expected and len(lines) <= 1, key
        reader.close()

    reader = lmdb_source.open_idx(zipnum)
    with open(zipnum, 'rb') as idx_file:
        assert reader.read_last_line() == read_last_line(idx_file)
    reader.close()


def test_lmdb_option(tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    load_idx(env_path, 'test', idx)

    source = init_index_source({'type': 'zipnum', 'path': idx, 'lmdb': lmdb_uri(env_path)})
    assert type(source) is ZipNumIndexSource
    assert source.lmdb_idx.env_path == env_path and source.lmdb_idx.db_name == 'test'
    reader = source.open_idx(idx)
    assert isinstance(reader, LMDBIdxReader)
    reader.close()

    for source in (init_index_source({'type': 'zipnum', 'path': idx}), init_index_source(idx)):
        assert source.lmdb_idx is None
        reader = source.open_idx(idx)
        assert isinstance(reader, IdxFileReader)
        reader.close()


@pytest.mark.parametrize('uri', ['lmdb:///data/idx.lmdb', 'lmdb://host/data/idx.lmdb?db=test', 'file:///x?db=a'])
def test_invalid_lmdb_uri(tmp_path, uri):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)

    with pytest.raises(ValueError):
        ZipNumIndexSource(idx, {'type': 'zipnum', 'path': idx, 'lmdb': uri})


def test_lmdb_package_is_required(tmp_path, env_path, monkeypatch):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    monkeypatch.setattr(lmdbidx, 'lmdb', None)

    with pytest.raises(ImportError, match='pip install lmdb'):
        ZipNumIndexSource(idx, {'type': 'zipnum', 'path': idx, 'lmdb': lmdb_uri(env_path)})


def test_without_the_lmdb_package(env_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(pywb.__file__)))
    code = ("import sys; sys.modules['lmdb'] = None\n"
            "from pywb.indexer import lmdbzipnumidx\n"
            "from pywb.warcserver.index.zipnum import ZipNumIndexSource\n"
            "idx = sys.argv[1]\n"
            "print(ZipNumIndexSource(idx).lmdb_idx)\n"
            "try:\n"
            "    ZipNumIndexSource(idx, {'type': 'zipnum', 'path': idx, 'lmdb': sys.argv[2]})\n"
            "except ImportError as e:\n"
            "    print(e)\n"
            "print(lmdbzipnumidx.main(['stats', '--env', sys.argv[3]]))\n")

    env = dict(os.environ, PYTHONPATH=root)
    out = subprocess.run([sys.executable, '-c', code, TEST_ZIPNUM_DIR + 'zipnum-sample.idx', lmdb_uri(env_path),
                          env_path], cwd=root, env=env, check=True, capture_output=True, text=True)

    assert out.stdout.splitlines() == ['None', 'The lmdb option of a zipnum index needs the lmdb package: '
                                       'pip install lmdb', '1']
    assert 'pip install lmdb' in out.stderr


def test_creating_the_source_does_not_open_the_environment(tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)

    make_sources(idx, env_path)

    assert not os.path.exists(env_path)


@pytest.mark.parametrize('db_name', ['test', 'other'])
def test_missing_environment_or_database_uses_the_idx_file(tmp_path, env_path, monkeypatch, caplog, db_name):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    if db_name == 'other':
        load_idx(env_path, 'test', idx)
    file_source, lmdb_source = make_sources(idx, env_path, db_name=db_name)
    params = {'url': 'http://example.org/same'}
    expected = results(file_source, params)

    assert results(lmdb_source, params) == expected
    assert 'not available' in caplog.text
    assert lmdb_source.lmdb_idx.open_reader() is None

    # loaded later, used after the retry interval
    lmdbidx.close_environments()
    load_idx(env_path, db_name, idx, drop=True)
    monkeypatch.setattr(lmdbidx.time, 'monotonic', lambda: lmdb_source.lmdb_idx._retry_at + 1)
    os.remove(idx)

    assert results(lmdb_source, params) == expected


def test_lookup_errors_use_the_idx_file(tmp_path, env_path, caplog):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    load_idx(env_path, 'test', idx)
    file_source, lmdb_source = make_sources(idx, env_path)
    params = {'url': 'http://example.org/same'}
    assert results(lmdb_source, params) == results(file_source, params)

    lmdbidx.get_environment(env_path).close()

    assert results(lmdb_source, params) == results(file_source, params)
    assert 'lookup failed' in caplog.text


def load_process(env_path, db_name, idx, *args):
    """ load on another process, as the environment can only be opened once per process
    """
    return subprocess.run([sys.executable, '-m', 'pywb.indexer.lmdbzipnumidx', 'load', '--env', env_path,
                           '--db', db_name] + list(args) + [idx], check=True, capture_output=True)


def test_reload_while_reading(tmp_path, env_path):
    old_idx = build_zipnum(str(tmp_path / 'old'), sample_cdxj(random.Random(1)), 5)
    new_idx = build_zipnum(str(tmp_path / 'new'), sample_cdxj(random.Random(2)), 3)
    load_idx(env_path, 'test', old_idx, map_size=1024 ** 2)
    old_file, lmdb_source = make_sources(old_idx, env_path)
    new_file = ZipNumIndexSource(new_idx, {'type': 'zipnum', 'path': new_idx})
    params = {'url': 'http://example.com/', 'matchType': 'domain', 'showPagedIndex': 'true'}

    reading = lmdb_source.load_index(dict(params))
    first = str(next(reading))
    # a bigger map size, the reader has to adopt it
    load_process(env_path, 'test', new_idx, '--drop', '--map-size', '1')

    # the query that started before the load still reads the old .idx
    assert [first] + [str(line) for line in reading] == results(old_file, params)
    assert results(lmdb_source, params) == results(new_file, params)


def query_in_worker(source, params, queue):
    queue.put(results(source, params))
    lmdbidx.close_environments()


def test_forked_workers(tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    load_idx(env_path, 'test', idx)
    file_source, lmdb_source = make_sources(idx, env_path)
    params = {'url': 'http://example.org/', 'matchType': 'domain'}
    expected = results(file_source, params)
    # opened before forking, like a uWSGI worker without lazy-apps
    assert results(lmdb_source, params) == expected

    context = multiprocessing.get_context('fork')
    queue = context.Queue()
    workers = [context.Process(target=query_in_worker, args=(lmdb_source, params, queue)) for _ in range(3)]
    for worker in workers:
        worker.start()
    worker_results = [queue.get(timeout=30) for _ in workers]
    for worker in workers:
        worker.join(timeout=30)

    assert worker_results == [expected] * 3
    assert results(lmdb_source, params) == expected


def write_warc(path):
    http_headers = StatusAndHeaders('200 OK', [('Content-Type', 'text/plain')], protocol='HTTP/1.0')
    with open(str(path), 'wb') as out:
        writer = WARCWriter(out, gzip=True)
        record = writer.create_warc_record('http://example.com/', 'response', payload=BytesIO(b'ARCHIVED PAGE'),
                                           http_headers=http_headers)
        writer.write_record(record)


def test_warcserver_with_the_lmdb_idx(tmp_path, env_path):
    write_warc(tmp_path / 'test.warc.gz')
    cdxj = BytesIO()
    with open(str(tmp_path / 'test.warc.gz'), 'rb') as warc:
        write_cdx_index(cdxj, warc, 'test.warc.gz', cdxj=True)
    lines = [line + b'\n' for line in cdxj.getvalue().splitlines() if not line.startswith(b'!')]
    lines += [cdxj_line('http://example.org/{0}'.format(i), 20200101000000) for i in range(10)]
    idx = build_zipnum(str(tmp_path / 'zipnum'), sorted(lines), 2)
    load_idx(env_path, 'pywb', idx)
    # only the LMDB .idx is used
    os.remove(idx)

    app = WarcServer(config_file=None, custom_config={
        'collections': {'pywb': {
            'index': {'type': 'zipnum', 'path': idx, 'lmdb': lmdb_uri(env_path, 'pywb')},
            'archive_paths': str(tmp_path) + '/',
        }},
        'enable_auto_colls': False,
    })
    client = Client(app, Response)

    res = client.get('/pywb/resource?url=http://example.com/')
    assert res.status_code == 200
    assert b'ARCHIVED PAGE' in res.data

    res = client.get('/pywb/index?url=http://example.org/&matchType=domain&output=text')
    assert res.status_code == 200
    assert len(res.data.splitlines()) == 10

    assert client.get('/pywb/resource?url=http://example.net/').status_code == 404


def test_empty_database(tmp_path, env_path):
    idx = tmp_path / 'empty.idx'
    idx.write_bytes(b'')
    (tmp_path / 'empty.loc').write_bytes(b'')
    load_idx(env_path, 'test', str(idx))
    file_source, lmdb_source = make_sources(str(idx), env_path)

    for source in (file_source, lmdb_source):
        with pytest.raises(IndexError):
            results(source, {'url': 'http://example.com/'})


def test_entries_size(tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    load_idx(env_path, 'test', idx)

    env = lmdb.open(env_path, readonly=True, max_dbs=lmdbidx.MAX_DBS)
    try:
        db = env.open_db(b'test', create=False)
        with env.begin(db=db) as txn:
            entries = list(txn.cursor())
    finally:
        env.close()

    with open(idx, 'rb') as reader:
        lines = reader.read().splitlines()
    assert [lmdbidx.idx_line(key, value) for key, value in entries] == lines
    assert max(len(key) for key, _ in entries) == lmdbidx.KEY_PREFIX_SIZE + lmdbidx.KEY_SUFFIX_SIZE
    # the key prefix isn't repeated on the value
    assert all(len(key) + len(value) == len(line) + lmdbidx.KEY_SUFFIX_SIZE
               for (key, value), line in zip(entries, lines))
