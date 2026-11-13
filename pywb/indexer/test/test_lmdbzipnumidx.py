import os

from io import StringIO

import pytest

lmdb = pytest.importorskip('lmdb')

from pywb.indexer import lmdbzipnumidx
from pywb.indexer.lmdbzipnumidx import load
from pywb.warcserver.index import lmdbidx


@pytest.fixture
def env_path(tmp_path):
    return str(tmp_path / 'idx.lmdb')


def load_idx(env_path, db_name, idx, **kwargs):
    return load(env_path, db_name, idx, out=StringIO(), **kwargs)


def db_entries(env_path):
    env = lmdb.open(env_path, readonly=True, max_dbs=lmdbidx.MAX_DBS)
    try:
        with env.begin() as txn:
            names = [key for key, _ in txn.cursor()]
        entries = {}
        for name in names:
            db = env.open_db(name, create=False)
            with env.begin(db=db) as txn:
                entries[name.decode('utf-8')] = list(txn.cursor())
        return entries
    finally:
        env.close()


def idx_lines(entries):
    return [lmdbidx.idx_line(key, value) + b'\n' for key, value in entries]


def write_idx(path, lines):
    path.write_bytes(b''.join(lines))
    return str(path)


IDX_LINES = [b'com,example)/ 20200101000000\ttest-01.cdx.gz\t0\t100\t1\n',
             b'com,example)/a 20200101000000\ttest-01.cdx.gz\t100\t100\t2\n',
             b'com,example)/a 20200101000000\ttest-01.cdx.gz\t200\t100\t3\n',
             b'org,example)/ 20200101000000\ttest-02.cdx.gz\t0\t100\t4\n']


@pytest.mark.parametrize('lines, error', [
    ([b'com,example)/ 20200101000000\ttest-01.cdx.gz\t0\t100\n'], 'line 1: expected urlkey'),
    ([b'com,example)/ 20200101000000\ttest-01.cdx.gz\tx\t100\t1\n'], 'line 1: expected urlkey'),
    ([b'\ttest-01.cdx.gz\t0\t100\t1\n'], 'line 1: expected urlkey'),
    (IDX_LINES[:3] + [IDX_LINES[3][:-1]], 'line 4: expected urlkey'),
    ([line.replace(b'\t%d\n' % i, b'\t1\n') for i, line in enumerate(IDX_LINES, 1)],
     'line 2: the line number field is 1, rebuild the .idx'),
    ([IDX_LINES[1].replace(b'\t2\n', b'\t1\n'), IDX_LINES[0].replace(b'\t1\n', b'\t2\n')], 'line 2: not sorted'),
    # sorted as lines, but not by first field: the first field sorts before its tab
    ([b'com,example)/a 2020\ttest-01.cdx.gz\t0\t100\t1\n', b'com,example)/a\ttest-01.cdx.gz\t0\t100\t2\n'],
     'line 2: not sorted'),
])
def test_load_rejects_invalid_idx(tmp_path, env_path, lines, error):
    idx = write_idx(tmp_path / 'test.idx', lines)
    load_idx(env_path, 'other', write_idx(tmp_path / 'other.idx', IDX_LINES))

    for dry_run in (True, False):
        with pytest.raises(ValueError, match=error):
            load_idx(env_path, 'test', idx, dry_run=dry_run)

    # nothing is written
    assert list(db_entries(env_path)) == ['other']


def test_load_stats_and_drop(tmp_path, env_path):
    idx = write_idx(tmp_path / 'test.idx', IDX_LINES)
    long_line = b'com,example)/' + b'a' * 600 + b' 20200101000000\ttest-01.cdx.gz\t100\t100\t2\n'
    long_idx = write_idx(tmp_path / 'long.idx', [IDX_LINES[0], long_line, IDX_LINES[3].replace(b'\t4\n', b'\t3\n')])
    load_idx(env_path, 'other', idx)

    stats = load_idx(env_path, 'test', idx)
    assert (stats.lines, stats.added, stats.repeated_keys, stats.long_keys, stats.dropped) == (4, 4, 1, 0, 0)

    with pytest.raises(ValueError, match='The database test has 4 entries, replace them with --drop'):
        load_idx(env_path, 'test', long_idx)

    stats = load_idx(env_path, 'test', long_idx, drop=True, dry_run=True)
    assert (stats.lines, stats.added, stats.updated, stats.unchanged, stats.dropped) == (3, 2, 0, 1, 3)
    assert db_entries(env_path)['test'] == db_entries(env_path)['other']

    stats = load_idx(env_path, 'test', long_idx, drop=True)
    assert (stats.lines, stats.added, stats.long_keys, stats.dropped) == (3, 3, 1, 4)

    entries = db_entries(env_path)
    assert idx_lines(entries['test']) == [IDX_LINES[0], long_line, IDX_LINES[3].replace(b'\t4\n', b'\t3\n')]
    # the other databases are kept
    assert idx_lines(entries['other']) == IDX_LINES


def test_dry_run_does_not_create_the_environment(tmp_path, env_path):
    idx = write_idx(tmp_path / 'test.idx', IDX_LINES)

    stats = load_idx(env_path, 'test', idx, dry_run=True)

    assert (stats.lines, stats.added, stats.dropped) == (4, 4, 0)
    assert not os.path.exists(env_path)


def test_main_load_and_stats(tmp_path, env_path, capsys):
    idx = write_idx(tmp_path / 'test.idx', IDX_LINES)

    assert lmdbzipnumidx.main(['load', '--env', env_path, '--db', 'test', idx]) == 0
    assert 'lines=4' in capsys.readouterr().out
    assert lmdbzipnumidx.main(['load', '--dry-run', '--env', env_path, '--db', 'test', '--recreate', idx]) == 0
    assert '[dry-run] ' in capsys.readouterr().out
    assert lmdbzipnumidx.main(['stats', '--env', env_path]) == 0
    assert 'test: entries=4' in capsys.readouterr().out


@pytest.mark.parametrize('args, error', [
    (['--db', 'test', 'missing.idx'], 'error: ZipNum .idx not found'),
    (['--db', '', 'test.idx'], 'error: The LMDB named database is required'),
    (['--db', 'test', '--map-size', '1', 'test.idx'], 'use a bigger --map-size'),
])
def test_main_reports_errors(tmp_path, env_path, capsys, monkeypatch, args, error):
    write_idx(tmp_path / 'test.idx', [b'com,example)/%08d 2020\ttest-01.cdx.gz\t0\t100\t%d\n' % (i, i)
                                      for i in range(1, 10001)])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lmdbzipnumidx, 'GIB', 64 * 1024)

    assert lmdbzipnumidx.main(['load', '--env', env_path] + args) == 1
    assert error in capsys.readouterr().err


def test_main_without_lmdb(tmp_path, env_path, capsys, monkeypatch):
    monkeypatch.setattr(lmdbzipnumidx, 'lmdb', None)

    assert lmdbzipnumidx.main(['stats', '--env', env_path]) == 1
    assert 'pip install lmdb' in capsys.readouterr().err
