import io
import math
import random
from unittest import mock

import pytest

from pywb.utils.binsearch import INDEX_FILE_BUFFER_SIZE
from pywb.warcserver.index import indexsource, zipnum
from pywb.warcserver.index.indexsource import FileIndexSource
from pywb.warcserver.index.zipnum import ZipNumIndexSource
from pywb.warcserver.resource import pathresolvers
from pywb.warcserver.resource.pathresolvers import PathIndexResolver


# io.DEFAULT_BUFFER_SIZE since Python 3.14
PY314_DEFAULT_BUFFER_SIZE = 131072

NUM_LINES = 40000


# ============================================================================
class CountingFileIO(io.FileIO):
    def __init__(self, *args, **kwargs):
        super(CountingFileIO, self).__init__(*args, **kwargs)
        self.bytes_read = 0

    def readinto(self, b):
        n = super(CountingFileIO, self).readinto(b)
        self.bytes_read += n or 0
        return n


class CountingOpen(object):
    """ open() that counts the bytes read from the files opened in binary
    mode, with the default buffer size of Python 3.14 on every version
    """
    def __init__(self):
        self.files = []

    def __call__(self, file, mode='r', buffering=-1, **kwargs):
        if mode != 'rb':
            return open(file, mode, buffering, **kwargs)

        if buffering < 0:
            buffering = PY314_DEFAULT_BUFFER_SIZE

        raw = CountingFileIO(file)
        self.files.append(raw)
        return io.BufferedReader(raw, buffer_size=buffering)

    @property
    def bytes_read(self):
        return sum(raw.bytes_read for raw in self.files)


def max_bytes_per_lookup(path):
    # each binary search step reads at most two buffers (when the line
    # crosses the end of the first one), plus the lines found at the end
    steps = math.ceil(math.log2(path.stat().st_size / 8192)) + 3
    return steps * 2 * INDEX_FILE_BUFFER_SIZE


def sample_keys():
    rand = random.Random(1)
    return [rand.randrange(NUM_LINES) for _ in range(50)]


# ============================================================================
@pytest.fixture(scope='module')
def cdxj_path(tmp_path_factory):
    path = tmp_path_factory.mktemp('buffering') / 'index.cdxj'
    with open(path, 'w') as fh:
        for i in range(NUM_LINES):
            fh.write('com,example)/page/%07d 20150101000000 {"url": "http://example.com/page/%07d", '
                     '"mime": "text/html", "status": "200", "digest": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", '
                     '"length": "1000", "offset": "%d", "filename": "example.warc.gz"}\n' % (i, i, i * 1000))

    return path


@pytest.fixture(scope='module')
def idx_path(tmp_path_factory):
    path = tmp_path_factory.mktemp('buffering') / 'index.idx'
    with open(path, 'w') as fh:
        for i in range(NUM_LINES):
            fh.write('com,example)/page/%07d 20150101000000\tindex-01\t%d\t1000\t%d\n' % (i, i * 1000, i + 1))

    with open(path.with_suffix('.loc'), 'w') as fh:
        fh.write('index-01\tindex-01.cdx.gz\n')

    return path


@pytest.fixture(scope='module')
def pathindex_path(tmp_path_factory):
    path = tmp_path_factory.mktemp('buffering') / 'pathindex.txt'
    with open(path, 'w') as fh:
        for i in range(NUM_LINES):
            fh.write('example-%07d.warc.gz\t/archive/storage-%02d/example-%07d.warc.gz\n' % (i, i % 10, i))

    return path


# ============================================================================
def test_file_index_lookup_reads_few_buffers(cdxj_path):
    counting_open = CountingOpen()
    source = FileIndexSource(str(cdxj_path))

    with mock.patch.object(indexsource, 'open', counting_open, create=True):
        for i in sample_keys():
            key = b'com,example)/page/%07d' % i
            params = {'key': key, 'end_key': key + b'!'}

            before = counting_open.bytes_read
            cdx_list = list(source.load_index(params))
            assert len(cdx_list) == 1
            assert cdx_list[0]['urlkey'] == key.decode('utf-8')

            assert counting_open.bytes_read - before <= max_bytes_per_lookup(cdxj_path)

    assert len(counting_open.files) == len(sample_keys())
    assert all(raw.closed for raw in counting_open.files)


def test_zipnum_summary_lookup_reads_few_buffers(idx_path):
    counting_open = CountingOpen()
    source = ZipNumIndexSource(str(idx_path))

    with mock.patch.object(zipnum, 'open', counting_open, create=True):
        for i in sample_keys():
            key = b'com,example)/page/%07d' % i
            params = {'url': 'http://example.com/page/%07d' % i, 'key': key, 'end_key': key + b'!',
                      'showPagedIndex': 'true'}

            before = counting_open.bytes_read
            idx_list = list(source.load_index(params))
            # the block before the key is included, as the key may start in it
            assert [idx['lineno'] for idx in idx_list] == list(range(max(i, 1), i + 2))

            # the summary is searched twice, for the start and the end of the range
            assert counting_open.bytes_read - before <= 2 * max_bytes_per_lookup(idx_path)

    assert len(counting_open.files) == len(sample_keys())


def test_path_index_lookup_reads_few_buffers(pathindex_path):
    counting_open = CountingOpen()
    resolver = PathIndexResolver(str(pathindex_path))

    with mock.patch.object(pathresolvers, 'open', counting_open, create=True):
        for i in sample_keys():
            before = counting_open.bytes_read
            paths = list(resolver('example-%07d.warc.gz' % i, None))
            assert paths == ['/archive/storage-%02d/example-%07d.warc.gz' % (i % 10, i)]

            assert counting_open.bytes_read - before <= max_bytes_per_lookup(pathindex_path)

    assert len(counting_open.files) == len(sample_keys())
    assert all(raw.closed for raw in counting_open.files)
