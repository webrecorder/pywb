import io

import pytest

from pywb.indexer import lmdbpathindex
from pywb.indexer.lmdbpathindex import LoadStats, iter_path_index, load, main


@pytest.fixture
def env_path(tmp_path):
    pytest.importorskip('lmdb')
    return str(tmp_path / 'pathindex.lmdb')


def write(path, text):
    path.write_bytes(text.encode('utf-8'))
    return str(path)


def read_db(env_path, db_name):
    import lmdb
    env = lmdb.open(env_path, readonly=True, max_dbs=8)
    try:
        db = env.open_db(db_name.encode('utf-8'), create=False)
        with env.begin(db=db) as txn:
            return {key.decode('utf-8'): value.decode('utf-8') for key, value in txn.cursor()}
    finally:
        env.close()


def parse(text):
    stats = LoadStats()
    entries = [(key.decode('utf-8'), value.decode('utf-8'))
               for key, value in iter_path_index(io.BytesIO(text.encode('utf-8')), stats)]
    return entries, stats


def test_iter_path_index_parses_like_path_index_resolver():
    entries, stats = parse('a.warc.gz\t/data/a.warc.gz  \r\n'
                           'b.warc.gz\t/data1/b.warc.gz\t/data2/b.warc.gz\n'
                           'b.warc.gz\t/data3/b.warc.gz\n'
                           'c.warc.gz\t\t/data/c.warc.gz\n')

    assert entries == [('a.warc.gz', '/data/a.warc.gz'),
                       ('b.warc.gz', '/data1/b.warc.gz\t/data2/b.warc.gz\t/data3/b.warc.gz'),
                       ('c.warc.gz', '\t/data/c.warc.gz')]
    assert (stats.lines, stats.skipped, stats.unsorted) == (4, 0, 0)


def test_iter_path_index_skips_invalid_lines():
    entries, stats = parse('\n'
                           'no-paths.warc.gz\n'
                           'empty-paths.warc.gz\t  \n'
                           '\t/data/no-name.warc.gz\n'
                           + 'x' * 512 + '\t/data/too-long.warc.gz\n'
                           'z.warc.gz\t/data/z.warc.gz\n')

    assert entries == [('z.warc.gz', '/data/z.warc.gz')]
    assert (stats.lines, stats.skipped) == (6, 5)


def test_iter_path_index_counts_unsorted_lines():
    entries, stats = parse('b\t/b\na\t/a\nc\t/c\n')

    assert [key for key, _ in entries] == ['b', 'a', 'c']
    assert stats.unsorted == 1


def test_load_creates_the_database(tmp_path, env_path):
    tsv = write(tmp_path / 'coll1.tsv', 'a.warc.gz\t/data/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n')

    stats = load(env_path, 'primary', [tsv], out=io.StringIO())

    assert (stats.files, stats.keys, stats.added) == (1, 2, 2)
    assert read_db(env_path, 'primary') == {'a.warc.gz': '/data/a.warc.gz', 'b.warc.gz': '/data/b.warc.gz'}


def test_load_updates_a_collection_keeping_the_others(tmp_path, env_path):
    coll1 = write(tmp_path / 'coll1.tsv', 'a.warc.gz\t/old/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n')
    coll2 = write(tmp_path / 'coll2.tsv', 'x.warc.gz\t/data/x.warc.gz\n')
    load(env_path, 'primary', [coll1, coll2], out=io.StringIO())

    coll1 = write(tmp_path / 'coll1.tsv', 'a.warc.gz\t/new/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n'
                                        'c.warc.gz\t/data/c.warc.gz\n')
    stats = load(env_path, 'primary', [coll1], out=io.StringIO())

    assert (stats.added, stats.updated, stats.unchanged, stats.dropped) == (1, 1, 1, 0)
    assert read_db(env_path, 'primary') == {'a.warc.gz': '/new/a.warc.gz', 'b.warc.gz': '/data/b.warc.gz',
                                            'c.warc.gz': '/data/c.warc.gz', 'x.warc.gz': '/data/x.warc.gz'}


def test_load_drop_recreates_only_its_database(tmp_path, env_path):
    old = write(tmp_path / 'old.tsv', 'a.warc.gz\t/old/a.warc.gz\nold.warc.gz\t/old/old.warc.gz\n')
    load(env_path, 'primary', [old], out=io.StringIO())
    load(env_path, 'mirror', [old], out=io.StringIO())

    new = write(tmp_path / 'new.tsv', 'a.warc.gz\t/new/a.warc.gz\n')
    stats = load(env_path, 'primary', [new], drop=True, out=io.StringIO())

    assert (stats.dropped, stats.added) == (2, 1)
    assert read_db(env_path, 'primary') == {'a.warc.gz': '/new/a.warc.gz'}
    assert read_db(env_path, 'mirror') == {'a.warc.gz': '/old/a.warc.gz', 'old.warc.gz': '/old/old.warc.gz'}


def test_load_dry_run_does_not_create_the_environment(tmp_path, env_path):
    tsv = write(tmp_path / 'coll1.tsv', 'a.warc.gz\t/data/a.warc.gz\n')
    out = io.StringIO()

    stats = load(env_path, 'primary', [tsv], dry_run=True, out=out)

    assert stats.added == 1
    assert not (tmp_path / 'pathindex.lmdb').exists()
    assert '[dry-run] total:' in out.getvalue()


@pytest.mark.parametrize('drop, expected', [
    (False, (1, 1, 1, 0)),
    (True, (3, 0, 0, 3)),
])
def test_load_dry_run_does_not_change_the_database(tmp_path, env_path, drop, expected):
    load(env_path, 'primary', [write(tmp_path / 'coll1.tsv', 'a\t/old/a\nb\t/b\nx\t/x\n')], out=io.StringIO())
    tsv = write(tmp_path / 'coll1.tsv', 'a\t/new/a\nb\t/b\nc\t/c\n')

    stats = load(env_path, 'primary', [tsv], drop=drop, dry_run=True, out=io.StringIO())

    assert (stats.added, stats.updated, stats.unchanged, stats.dropped) == expected
    assert read_db(env_path, 'primary') == {'a': '/old/a', 'b': '/b', 'x': '/x'}


def test_load_dry_run_on_a_missing_database(tmp_path, env_path):
    tsv = write(tmp_path / 'coll1.tsv', 'a\t/a\n')
    load(env_path, 'primary', [tsv], out=io.StringIO())

    stats = load(env_path, 'mirror', [tsv], drop=True, dry_run=True, out=io.StringIO())

    assert (stats.added, stats.dropped) == (1, 0)


def test_load_directory_files_matching_the_pattern(tmp_path, env_path):
    index_dir = tmp_path / 'primary'
    index_dir.mkdir()
    (index_dir / 'subdir.tsv').mkdir()
    write(index_dir / 'coll1.tsv', 'a\t/a\n')
    write(index_dir / 'coll2.tsv', 'b\t/b\n')
    write(index_dir / 'coll2.tsv.bak', 'c\t/c\n')
    write(index_dir / 'notes.txt', 'd\t/d\n')

    stats = load(env_path, 'primary', [str(index_dir)], pattern=r'.*\.tsv', out=io.StringIO())

    assert stats.files == 2
    assert read_db(env_path, 'primary') == {'a': '/a', 'b': '/b'}


def test_load_directory_without_pattern_loads_all_files(tmp_path, env_path):
    write(tmp_path / 'coll1.tsv', 'a\t/a\n')
    write(tmp_path / 'other', 'b\t/b\n')

    stats = load(env_path, 'primary', [str(tmp_path)], out=io.StringIO())

    assert stats.files == 2


def test_load_requires_a_named_database(tmp_path, env_path):
    with pytest.raises(ValueError):
        load(env_path, '', [write(tmp_path / 'coll1.tsv', 'a\t/a\n')])


def test_main_load_and_stats(tmp_path, env_path, capsys):
    tsv = write(tmp_path / 'coll1.tsv', 'a\t/a\nb\t/b\n')

    assert main(['load', '--env', env_path, '--db', 'primary', '--map-size', '1', tsv]) == 0
    assert main(['load', '--env', env_path, '--db', 'mirror', '--recreate', tsv]) == 0
    assert main(['stats', '--env', env_path]) == 0

    out = capsys.readouterr().out
    assert 'total: files=1, lines=2, skipped=0, unsorted=0, keys=2, added=2' in out
    assert 'primary: entries=2' in out
    assert 'mirror: entries=2' in out


def test_main_reports_errors(tmp_path, env_path, capsys):
    assert main(['load', '--env', env_path, '--db', 'primary', str(tmp_path / 'missing.tsv')]) == 1
    assert main(['load', '--env', env_path, '--db', 'primary', '--pattern', '(', str(tmp_path)]) == 1
    assert 'error:' in capsys.readouterr().err


def test_main_reports_a_full_map(tmp_path, env_path, capsys, monkeypatch):
    monkeypatch.setattr(lmdbpathindex, 'GIB', 64 * 1024)
    tsv = write(tmp_path / 'coll1.tsv', ''.join('{0:08d}.warc.gz\t/data/{0:08d}.warc.gz\n'.format(i)
                                               for i in range(10000)))

    assert main(['load', '--env', env_path, '--db', 'primary', '--map-size', '1', tsv]) == 1
    assert 'use a bigger --map-size' in capsys.readouterr().err


def test_main_without_lmdb(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(lmdbpathindex, 'lmdb', None)

    assert main(['stats', '--env', str(tmp_path)]) == 1
    assert 'pip install lmdb' in capsys.readouterr().err

    with pytest.raises(ImportError):
        load(str(tmp_path), 'primary', [])
