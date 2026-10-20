"""
Exact url lookups with closest= in local CDX/CDXJ files only read the
captures around the closest timestamp (see FileIndexSource): check that the
results are identical to reading every capture of the url.
"""
import io
import json
import os
import random
from datetime import datetime, timedelta, timezone

import pytest
import webtest
from warcio.timeutils import datetime_to_timestamp, timestamp_to_sec

from pywb.utils.wbexception import NotFoundException
from pywb.warcserver.basewarcserver import BaseWarcServer
from pywb.warcserver.handlers import ResourceHandler
from pywb.warcserver.index import indexsource
from pywb.warcserver.index.aggregator import DirectoryIndexSource, SimpleAggregator
from pywb.warcserver.index.cdxobject import CDXObject
from pywb.warcserver.index.cdxops import closest_seek_limit
from pywb.warcserver.index.fuzzymatcher import FuzzyMatcher
from pywb.warcserver.index.indexsource import FileIndexSource


URL = 'http://example.com/script.js'
URLKEY = 'com,example)/script.js'

# urlkeys sorting right before and after URLKEY
NEIGHBOURS_BEFORE = ['com,example)/', 'com,example)/script.j']
NEIGHBOURS_AFTER = ['com,example)/script.js/', 'com,example)/script.js?v=1', 'com,example)/script.jsx']

START = datetime(2010, 1, 1, tzinfo=timezone.utc)
SECONDS = int((datetime(2021, 1, 1, tzinfo=timezone.utc) - START).total_seconds())

LIMITS = [1, 2, 3, 7, 25, 100]


# ============================================================================
def random_timestamp(rnd):
    ts = datetime_to_timestamp(START + timedelta(seconds=rnd.randrange(SECONDS)))
    # a few 17-digit timestamps, which share their second with 14-digit ones
    if rnd.random() < 0.02:
        ts += '%03d' % rnd.randrange(1000)
    return ts


def cdxj_line(rnd, urlkey, ts, filename):
    revisit = rnd.random() < 0.2
    data = {'url': 'http://example.com/',
            'mime': 'warc/revisit' if revisit else 'application/javascript',
            'status': rnd.choice(['200', '200', '200', '404']),
            'digest': 'SHA1:DIGEST{0}'.format(rnd.randrange(20)),
            'length': str(rnd.randrange(100, 2000)),
            'offset': str(rnd.randrange(10 ** 8)),
            'filename': filename}
    return '{0} {1} {2}'.format(urlkey, ts, json.dumps(data))


def write_cdxj(path, lines):
    with open(path, 'w') as fh:
        fh.write('\n'.join(sorted(lines)) + '\n')


@pytest.fixture(scope='module')
def index_dir(tmp_path_factory):
    """
    URLKEY captured at random times, many of them repeated in the same and
    in different files, spread over files with and without other urlkeys
    around it.
    """
    rnd = random.Random(1671)
    the_dir = tmp_path_factory.mktemp('closest_seek')

    timestamps = []
    files = {name: [] for name in ('a.cdxj', 'b.cdxj', 'c.cdxj', 'd.cdxj', 'e.cdxj')}

    def add(name, urlkey):
        if urlkey == URLKEY and timestamps and rnd.random() < 0.15:
            ts = rnd.choice(timestamps)
        else:
            ts = random_timestamp(rnd)
            timestamps.append(ts)
        files[name].append(cdxj_line(rnd, urlkey, ts, name + '.warc.gz'))

    for _ in range(800):
        add('a.cdxj', URLKEY)
    for urlkey in NEIGHBOURS_BEFORE + NEIGHBOURS_AFTER:
        for _ in range(30):
            add('a.cdxj', urlkey)

    # only URLKEY: starts at the beginning and ends at the end of the file
    for _ in range(500):
        add('b.cdxj', URLKEY)

    # other urlkeys only before URLKEY
    for _ in range(300):
        add('c.cdxj', URLKEY)
    for _ in range(30):
        add('c.cdxj', NEIGHBOURS_BEFORE[-1])

    # single capture
    add('d.cdxj', URLKEY)
    add('d.cdxj', NEIGHBOURS_AFTER[0])

    # no capture of URLKEY
    for urlkey in NEIGHBOURS_BEFORE + NEIGHBOURS_AFTER:
        add('e.cdxj', urlkey)

    for name, lines in files.items():
        write_cdxj(str(the_dir / name), lines)

    return str(the_dir)


@pytest.fixture(scope='module')
def capture_timestamps(index_dir):
    timestamps = set()
    for name in os.listdir(index_dir):
        with open(os.path.join(index_dir, name)) as fh:
            for line in fh:
                if line.startswith(URLKEY + ' '):
                    timestamps.add(line.split(' ')[1])
    return sorted(timestamps)


def query(index_dir, **params):
    params.setdefault('url', URL)
    cdx_iter, errs = DirectoryIndexSource(index_dir)(params)
    assert errs == {}
    return [list(cdx.items()) for cdx in cdx_iter]


def query_full_scan(index_dir, monkeypatch, **params):
    with monkeypatch.context() as m:
        m.setattr(indexsource, 'closest_seek_limit', lambda params: None)
        return query(index_dir, **params)


@pytest.fixture
def seek_calls(monkeypatch):
    """ record the params of every lookup that reads only around closest """
    calls = []
    orig_iter_closest = FileIndexSource._iter_closest

    def _iter_closest(self, fh, params, limit):
        calls.append(dict(params))
        return orig_iter_closest(self, fh, params, limit)

    monkeypatch.setattr(FileIndexSource, '_iter_closest', _iter_closest)
    return calls


def closest_values(timestamps):
    rnd = random.Random(44)

    # before the first and after the last capture
    values = ['1996', '19960101000000', '2009', '2030', '29991231235959']

    # exact hits, including repeated timestamps and 17-digit timestamps
    values += rnd.sample(timestamps, 10)
    values += [ts for ts in timestamps if len(ts) > 14][:5]
    values += [timestamps[0], timestamps[-1]]

    # one second around existing timestamps
    for ts in rnd.sample(timestamps, 5):
        sec = timestamp_to_sec(ts)
        for delta in (-1, 1):
            dt = datetime.fromtimestamp(sec + delta, tz=timezone.utc)
            values.append(datetime_to_timestamp(dt))

    # exactly between two captures: same distance to both
    for i in rnd.sample(range(len(timestamps) - 1), 5):
        sec_1 = timestamp_to_sec(timestamps[i])
        sec_2 = timestamp_to_sec(timestamps[i + 1])
        if (sec_1 + sec_2) % 2 == 0:
            dt = datetime.fromtimestamp((sec_1 + sec_2) // 2, tz=timezone.utc)
            values.append(datetime_to_timestamp(dt))

    # random
    values += [random_timestamp(rnd) for _ in range(10)]

    # short, long and out of range closest values
    values += ['2015', '201506', '2015061', '20150615', '2015061512', '201506151230',
               '20150615123045123', '20151399', '20151340000000', '2015abc']

    return values


# ============================================================================
def test_closest_seek_limit():
    def limit(**params):
        params.setdefault('url', URL)
        params.setdefault('closest', '20150615000000')
        params.setdefault('key', URLKEY.encode('utf-8'))
        params.setdefault('end_key', URLKEY.encode('utf-8') + b'!')
        params.setdefault('matchType', 'exact')
        return closest_seek_limit(params)

    assert limit() == 100000
    assert limit(limit='10') == 10
    assert limit(limit=1) == 1
    assert limit(reverse='false', resolveRevisits='0', showNumPages='false') == 100000

    # results are not just the captures closest to closest=
    assert limit(closest=None) is None
    assert limit(closest='') is None
    assert limit(matchType='prefix') is None
    assert limit(end_key=URLKEY.encode('utf-8') + b'/') is None
    assert limit(filter='=status:200') is None
    assert limit(filter=['!mime:warc/revisit']) is None
    assert limit(**{'from': '2015'}) is None
    assert limit(from_ts='2015') is None
    assert limit(to='2015') is None
    assert limit(collapseTime='8') is None
    assert limit(reverse='true') is None
    assert limit(sort='reverse') is None
    assert limit(resolveRevisits='true') is None
    assert limit(showNumPages='true') is None
    assert limit(showPagedIndex='true') is None
    assert limit(limit='0') is None
    assert limit(limit='-1') is None
    assert limit(limit='abc') is None

    # default limit of replay lookups, set by the ResourceHandler
    assert limit(_closest_limit=100) == 100
    assert limit(_closest_limit=100, limit='10') == 10
    assert limit(_closest_limit=100, limit='500') == 500
    assert limit(_closest_limit=None) == 100000
    assert limit(_closest_limit=0) == 100000


def test_closest_same_as_full_scan(index_dir, capture_timestamps, monkeypatch, seek_calls):
    for closest in closest_values(capture_timestamps):
        # with a smaller limit, cdx_sort_closest() returns the start of the same list
        full_scan = query_full_scan(index_dir, monkeypatch, closest=closest)
        assert len(full_scan) == 1601

        for limit in LIMITS:
            del seek_calls[:]
            assert query(index_dir, closest=closest, limit=str(limit)) == full_scan[:limit], (closest, limit)
            # once per file
            assert len(seek_calls) == 5

        # default limit
        assert query(index_dir, closest=closest) == full_scan, closest


@pytest.mark.parametrize('limit', [1, 3, 25])
def test_closest_same_as_full_scan_single_file(index_dir, capture_timestamps, monkeypatch, seek_calls, limit):
    agg = SimpleAggregator({'a': FileIndexSource(os.path.join(index_dir, 'a.cdxj'))})

    def query_single(**params):
        cdx_iter, errs = agg(dict(params, url=URL, limit=limit))
        return [list(cdx.items()) for cdx in cdx_iter]

    for closest in closest_values(capture_timestamps):
        with monkeypatch.context() as m:
            m.setattr(indexsource, 'closest_seek_limit', lambda params: None)
            full_scan = query_single(closest=closest)

        assert query_single(closest=closest) == full_scan, closest

    assert len(seek_calls) == len(closest_values(capture_timestamps))


@pytest.mark.parametrize('params', [
    dict(filter='=status:200'),
    dict(filter=['!mime:warc/revisit', 'digest:SHA1:DIGEST1']),
    dict(content_type='application/javascript'),
    {'from': '2015'},
    dict(to='2016'),
    {'from': '2014', 'to': '2016'},
    dict(collapseTime='6'),
    dict(reverse='true'),
    dict(sort='reverse'),
    dict(resolveRevisits='true'),
    dict(matchType='prefix'),
    dict(url=URL + '*'),
    dict(url='*.example.com'),
    dict(limit='0'),
])
def test_closest_fallback_full_scan(index_dir, monkeypatch, seek_calls, params):
    params = dict(params, closest='20150615000000', limit=params.get('limit', '5'))

    full_scan = query_full_scan(index_dir, monkeypatch, **params)
    assert query(index_dir, **params) == full_scan
    assert seek_calls == []

    if params['limit'] != '0':
        assert len(full_scan) > 0


def test_closest_fallback_fuzzy(index_dir, monkeypatch, seek_calls):
    params = dict(url=URL + '?_=1234', closest='20150615000000', limit='5')

    def query_fuzzy():
        agg = DirectoryIndexSource(index_dir)
        cdx_iter, errs = FuzzyMatcher()(agg, dict(params))
        return [list(cdx.items()) for cdx in cdx_iter]

    with monkeypatch.context() as m:
        m.setattr(indexsource, 'closest_seek_limit', lambda params: None)
        full_scan = query_fuzzy()

    assert len(full_scan) > 0
    assert all(dict(cdx)['is_fuzzy'] == '1' for cdx in full_scan)

    del seek_calls[:]
    assert query_fuzzy() == full_scan

    # only the initial exact lookup reads around closest, the fuzzy lookup reads everything
    assert len(seek_calls) == 5
    assert all(call['matchType'] == 'exact' and not call.get('is_fuzzy') for call in seek_calls)


# ============================================================================
class CountingFileIO(io.FileIO):
    bytes_read = 0

    def readinto(self, buff):
        res = super(CountingFileIO, self).readinto(buff)
        CountingFileIO.bytes_read += res or 0
        return res


class CountingCDXObject(CDXObject):
    count = 0

    def __init__(self, *args, **kwargs):
        CountingCDXObject.count += 1
        super(CountingCDXObject, self).__init__(*args, **kwargs)


@pytest.fixture(scope='module')
def big_index(tmp_path_factory):
    """ a single file with 30k captures of URLKEY, one every 3 hours """
    rnd = random.Random(1)
    path = str(tmp_path_factory.mktemp('closest_seek_big') / 'big.cdxj')

    lines = []
    for i in range(30000):
        ts = datetime_to_timestamp(START + timedelta(hours=3 * i))
        lines.append(cdxj_line(rnd, URLKEY, ts, 'big.warc.gz'))

    for urlkey in NEIGHBOURS_BEFORE + NEIGHBOURS_AFTER:
        for _ in range(800):
            lines.append(cdxj_line(rnd, urlkey, random_timestamp(rnd), 'big.warc.gz'))

    write_cdxj(path, lines)
    return path


@pytest.mark.parametrize('closest,limit', [
    ('20130615123000', 1),
    ('20130615120000', 100),
    ('2000', 10),
    ('2030', 10),
])
def test_closest_reads_only_window(big_index, monkeypatch, closest, limit):
    def query_counting():
        CountingFileIO.bytes_read = 0
        CountingCDXObject.count = 0
        agg = SimpleAggregator({'big': FileIndexSource(big_index)})
        cdx_iter, errs = agg(dict(url=URL, closest=closest, limit=str(limit)))
        return [cdx['timestamp'] for cdx in cdx_iter]

    monkeypatch.setattr(FileIndexSource, '_do_open',
                        lambda self, filename: io.BufferedReader(CountingFileIO(filename), 8192))
    monkeypatch.setattr(indexsource, 'CDXObject', CountingCDXObject)

    with monkeypatch.context() as m:
        m.setattr(indexsource, 'closest_seek_limit', lambda params: None)
        full_scan = query_counting()

    assert query_counting() == full_scan
    assert len(full_scan) == limit

    # at most 'limit' captures on each side of closest, no repeated timestamps here
    assert CountingCDXObject.count <= 2 * limit

    # binary search plus a few blocks around closest
    assert CountingFileIO.bytes_read < 300000
    # cdx_sort_closest() may also stop the full scan early, after closest,
    # so compare with the size of the index instead
    assert CountingFileIO.bytes_read * 20 < os.path.getsize(big_index)


def test_closest_resource_reads_only_window(big_index, monkeypatch):
    # replay lookups have no limit, the ResourceHandler.CLOSEST_LIMIT is used
    tried = []

    def failing_loader(cdx, params):
        tried.append(cdx['timestamp'])
        raise NotFoundException('not loaded: ' + cdx['timestamp'])

    handler = ResourceHandler(SimpleAggregator({'big': FileIndexSource(big_index)}), [failing_loader])
    app = BaseWarcServer()
    app.add_route('/coll', handler)

    monkeypatch.setattr(indexsource, 'CDXObject', CountingCDXObject)
    CountingCDXObject.count = 0

    webtest.TestApp(app).get('/coll/resource', params={'url': URL, 'closest': '20130615120000'}, status=404)

    assert len(tried) == ResourceHandler.CLOSEST_LIMIT == 100
    assert tried[0] == '20130615120000'
    assert CountingCDXObject.count <= 2 * ResourceHandler.CLOSEST_LIMIT
