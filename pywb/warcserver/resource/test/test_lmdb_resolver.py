import io
import multiprocessing
import os
import random
import subprocess
import sys

import pytest

from werkzeug.test import Client
from werkzeug.wrappers import Response

import pywb
from pywb import get_test_dir
from pywb.warcserver.index.cdxobject import CDXObject
from pywb.warcserver.resource.pathresolvers import DefaultResolverMixin, LMDBResolver
from pywb.warcserver.resource.pathresolvers import PathIndexResolver, PrefixResolver
from pywb.warcserver.warcserver import WarcServer

lmdb = pytest.importorskip('lmdb')

from pywb.indexer.lmdbpathindex import load


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(pywb.__file__)))

EXAMPLE_WARC = os.path.join(os.path.abspath(get_test_dir()), 'warcs', 'example.warc.gz')

requires_fork = pytest.mark.skipif(not hasattr(os, 'fork'), reason='requires fork()')


# ============================================================================
@pytest.fixture(autouse=True)
def close_envs():
    yield
    LMDBResolver.close_envs()


@pytest.fixture
def env_path(tmp_path):
    return str(tmp_path / 'pathindex.lmdb')


def load_text(env_path, db_name, path, text, **kwargs):
    path.write_bytes(text.encode('utf-8'))
    load(env_path, db_name, [str(path)], out=io.StringIO(), **kwargs)


def load_text_process(env_path, db_name, path, text, *args):
    # load in another process, as an environment can only be opened once per process
    path.write_bytes(text.encode('utf-8'))
    cmd = [sys.executable, '-m', 'pywb.indexer.lmdbpathindex', 'load', '--env', env_path, '--db', db_name]
    cmd += list(args) + [str(path)]
    subprocess.check_call(cmd, cwd=ROOT_DIR, stdout=subprocess.DEVNULL)


def random_path_index(rnd, size):
    lines = []
    for i in range(size):
        name = 'C{0}-{1:014d}-{2:05d}.warc.gz'.format(rnd.randint(1, 30), rnd.randint(0, 10 ** 14), i)
        lines.append('{0}\t/data/{1}/{0}'.format(name, rnd.randint(1, 9)))
        if rnd.random() < 0.1:
            lines.append('{0}\t/mirror/{0}\thttp://warcs.example.com/{0}'.format(name))
        if rnd.random() < 0.05:
            lines[-1] += ' \r'

    lines.append(u'nação-çá.warc.gz\t/data/nação-çá.warc.gz')
    lines.append('prefix.warc\t/data/prefix.warc')
    lines.append('prefix.warc.gz\t/data/prefix.warc.gz')
    lines.sort(key=lambda line: line.partition('\t')[0].encode('utf-8'))
    return '\n'.join(lines) + '\n'


def lookup_in_worker(resolver, names, queue):
    queue.put([resolver(name, CDXObject()) for name in names])


# ============================================================================
class TestLMDBResolver(object):
    def test_same_results_as_path_index_resolver(self, tmp_path, env_path):
        rnd = random.Random(1672)
        path_index = tmp_path / 'pathindex.txt'
        load_text(env_path, 'primary', path_index, random_path_index(rnd, 5000))

        names = [line.partition('\t')[0] for line in path_index.read_text('utf-8').splitlines()]
        names += [name + '.missing' for name in rnd.sample(names, 500)]
        names += [name[:-3] for name in rnd.sample(names, 500)]
        names += ['', 'prefix', 'prefix.war', 'zzz.warc.gz', 'x' * 600]

        path_index_resolver = PathIndexResolver(str(path_index))
        resolver = LMDBResolver(env_path, 'primary')
        cdx = CDXObject()
        for name in names:
            assert resolver(name, cdx) == list(path_index_resolver(name, cdx)), name

        assert resolver('prefix.warc', cdx) == ['/data/prefix.warc']
        assert resolver(u'nação-çá.warc.gz', cdx) == [u'/data/nação-çá.warc.gz']

    def test_sample_path_index(self, env_path):
        path_index = os.path.join(get_test_dir(), 'text_content', 'pathindex.txt')
        load(env_path, 'primary', [path_index], out=io.StringIO())
        resolver = LMDBResolver(env_path, 'primary')

        cdx = CDXObject()
        assert resolver('example.warc.gz', cdx) == ['invalid_path', 'sample_archive/warcs/example.warc.gz']
        assert resolver('iana.warc.gz', cdx) == ['sample_archive/warcs/iana.warc.gz']
        assert resolver('not-found.gz', cdx) == []

    @pytest.mark.parametrize('uri, env_path, db_name', [
        ('lmdb:///data/pathindex.lmdb?db=primary', '/data/pathindex.lmdb', 'primary'),
        ('lmdb:///data/path%20index/?db=db%20B', '/data/path index', 'db B'),
        ('lmdb:///data/pathindex.lmdb', '/data/pathindex.lmdb', None),
    ])
    def test_from_uri(self, uri, env_path, db_name):
        resolver = LMDBResolver.from_uri(uri)

        assert (resolver.env_path, resolver.db_name) == (env_path, db_name)

    @pytest.mark.parametrize('uri', ['lmdb://host/data/pathindex.lmdb', 'lmdb://', 'file:///data/pathindex.lmdb'])
    def test_from_uri_invalid(self, uri):
        with pytest.raises(ValueError):
            LMDBResolver.from_uri(uri)

    def test_make_best_resolver_lmdb(self):
        res = DefaultResolverMixin.make_best_resolver('lmdb:///data/pathindex.lmdb?db=primary')
        assert isinstance(res, LMDBResolver)
        assert repr(res) == "LMDBResolver('/data/pathindex.lmdb', db='primary')"

    def test_resolver_list(self, tmp_path):
        resolvers = DefaultResolverMixin.make_resolvers(['lmdb:///data/pathindex.lmdb?db=primary',
                                                         'lmdb:///data/pathindex.lmdb?db=mirror',
                                                         str(tmp_path) + '/'])

        assert [type(res) for res in resolvers] == [LMDBResolver, LMDBResolver, PrefixResolver]
        assert [res.db_name for res in resolvers[:2]] == ['primary', 'mirror']

    def test_creating_the_resolver_does_not_open_the_env(self, env_path):
        DefaultResolverMixin.make_resolvers(['lmdb://' + env_path + '?db=primary'])

        assert env_path not in LMDBResolver._envs
        assert not os.path.exists(env_path)

    def test_missing_env_and_database(self, tmp_path, env_path, monkeypatch, caplog):
        monkeypatch.setattr(LMDBResolver, 'RETRY_INTERVAL', 3600)
        resolver_a = LMDBResolver(env_path, 'primary')
        resolver_b = LMDBResolver(env_path, 'mirror')

        assert resolver_a('a.warc.gz', CDXObject()) == []
        assert 'not available' in caplog.text

        load_text(env_path, 'primary', tmp_path / 'a.txt', 'a.warc.gz\t/primary/a.warc.gz\n')

        # opened again only after the retry interval
        assert resolver_a('a.warc.gz', CDXObject()) == []
        resolver_a._retry_at = 0
        assert resolver_a('a.warc.gz', CDXObject()) == ['/primary/a.warc.gz']

        # a missing database doesn't affect the other databases
        assert resolver_b('a.warc.gz', CDXObject()) == []
        assert resolver_a('a.warc.gz', CDXObject()) == ['/primary/a.warc.gz']

    def test_named_databases_are_independent(self, tmp_path, env_path):
        load_text(env_path, 'primary', tmp_path / 'a.txt', 'a.warc.gz\t/primary/a.warc.gz\n')
        load_text(env_path, 'mirror', tmp_path / 'b.txt', 'a.warc.gz\t/mirror/a.warc.gz\nb.warc.gz\t/mirror/b\n')
        resolver_a = LMDBResolver(env_path, 'primary')
        resolver_b = LMDBResolver(env_path, 'mirror')

        cdx = CDXObject()
        assert resolver_a('a.warc.gz', cdx) == ['/primary/a.warc.gz']
        assert resolver_a('b.warc.gz', cdx) == []
        assert resolver_b('a.warc.gz', cdx) == ['/mirror/a.warc.gz']
        assert resolver_b('b.warc.gz', cdx) == ['/mirror/b']

        # both use the same environment
        assert list(LMDBResolver._envs.keys()) == [env_path]

    def test_sees_the_updates_of_the_loader(self, tmp_path, env_path):
        load_text(env_path, 'primary', tmp_path / 'a.txt', 'a.warc.gz\t/old/a.warc.gz\n', map_size=1024 * 1024)
        resolver = LMDBResolver(env_path, 'primary')
        assert resolver('a.warc.gz', CDXObject()) == ['/old/a.warc.gz']

        # the loader grows the map beyond the size known by the resolver
        big = ''.join('{0:08d}.warc.gz\t/data/{1}/{0:08d}.warc.gz\n'.format(i, 'x' * 400) for i in range(40000))
        load_text_process(env_path, 'primary', tmp_path / 'a.txt', 'a.warc.gz\t/new/a.warc.gz\n' + big,
                          '--drop', '--map-size', '1')

        assert resolver('a.warc.gz', CDXObject()) == ['/new/a.warc.gz']
        assert resolver('00039999.warc.gz', CDXObject()) == ['/data/{0}/00039999.warc.gz'.format('x' * 400)]
        assert LMDBResolver.get_env(env_path).info()['map_size'] == 1024 ** 3

    @requires_fork
    def test_workers_forked_after_creating_the_resolver(self, tmp_path, env_path):
        # uWSGI creates the app, and the resolvers, before forking the workers
        text = ''.join('{0:05d}.warc.gz\t/data/{0:05d}.warc.gz\n'.format(i) for i in range(1000))
        load_text(env_path, 'primary', tmp_path / 'a.txt', text)
        resolver = LMDBResolver(env_path, 'primary')

        context = multiprocessing.get_context('fork')
        queue = context.Queue()
        names = ['{0:05d}.warc.gz'.format(i) for i in range(0, 1000, 7)] + ['missing.warc.gz']
        workers = [context.Process(target=lookup_in_worker, args=(resolver, names, queue)) for _ in range(4)]
        for worker in workers:
            worker.start()

        results = [queue.get(timeout=30) for _ in workers]
        for worker in workers:
            worker.join(timeout=30)
            assert worker.exitcode == 0

        expected = [['/data/' + name] for name in names[:-1]] + [[]]
        assert results == [expected] * 4
        assert resolver('00007.warc.gz', CDXObject()) == ['/data/00007.warc.gz']

    @requires_fork
    def test_worker_forked_after_opening_does_not_close_the_parent_env(self, tmp_path, env_path):
        load_text(env_path, 'primary', tmp_path / 'a.txt', 'a.warc.gz\t/data/a.warc.gz\n')
        resolver = LMDBResolver(env_path, 'primary')
        assert resolver('a.warc.gz', CDXObject()) == ['/data/a.warc.gz']

        def reader_pids(env):
            return [int(line.split()[0]) for line in env.readers().splitlines()[1:]]

        env = LMDBResolver.get_env(env_path)
        context = multiprocessing.get_context('fork')
        queue = context.Queue()

        # a lookup of the parent while the child does its lookups
        with env.begin():
            assert reader_pids(env) == [os.getpid()]

            worker = context.Process(target=lookup_in_worker, args=(resolver, ['a.warc.gz'] * 2, queue))
            worker.start()

            # py-lmdb doesn't open again in the child an environment opened
            # before fork() (without this check, the child opens its own)
            assert queue.get(timeout=30) in ([[], []], [['/data/a.warc.gz']] * 2)
            worker.join(timeout=30)
            assert worker.exitcode == 0

            # closing it in the child would have released the reader slot of the parent
            assert os.getpid() in reader_pids(env)

        assert resolver('a.warc.gz', CDXObject()) == ['/data/a.warc.gz']

    def test_lookup_errors_skip_the_resolver(self, tmp_path, env_path, caplog):
        load_text(env_path, 'primary', tmp_path / 'a.txt', 'a.warc.gz\t/data/a.warc.gz\n')
        resolver = LMDBResolver(env_path, 'primary')
        assert resolver('a.warc.gz', CDXObject()) == ['/data/a.warc.gz']

        LMDBResolver.get_env(env_path).close()

        assert resolver('a.warc.gz', CDXObject()) == []
        assert 'lookup failed' in caplog.text


# ============================================================================
class TestLMDBWarcServer(object):
    URL = '/coll/resource?url=http://example.com?example=1'

    def replay(self, env_path, db_names):
        app = WarcServer(config_file=None, custom_config={
            'collections': {'coll': {
                'index_paths': os.path.join(get_test_dir(), 'cdxj', 'example.cdxj'),
                'archive_paths': ['lmdb://{0}?db={1}'.format(env_path, name) for name in db_names],
            }},
            'enable_auto_colls': False,
        })
        return Client(app, Response).get(self.URL)

    def test_replay_sample_warc(self, tmp_path, env_path):
        load_text(env_path, 'primary', tmp_path / 'a.txt', 'example.warc.gz\t' + EXAMPLE_WARC + '\n')

        res = self.replay(env_path, ['primary'])

        assert res.status_code == 200
        assert res.headers['WARC-Target-URI'] == 'http://example.com?example=1'
        assert b'Example Domain' in res.data

    def test_not_found_in_the_database(self, tmp_path, env_path):
        load_text(env_path, 'primary', tmp_path / 'a.txt', 'other.warc.gz\t' + EXAMPLE_WARC + '\n')

        res = self.replay(env_path, ['primary'])

        assert res.status_code == 503

    @pytest.mark.parametrize('primary_text', [
        # the WARC is missing in the primary database
        'other.warc.gz\t/missing/other.warc.gz\n',
        # the WARC is missing at the path of the primary database
        'example.warc.gz\t/missing/example.warc.gz\n',
    ])
    def test_replay_from_the_next_database(self, tmp_path, env_path, primary_text):
        load_text(env_path, 'primary', tmp_path / 'a.txt', primary_text)
        load_text(env_path, 'mirror', tmp_path / 'b.txt', 'example.warc.gz\t' + EXAMPLE_WARC + '\n')

        res = self.replay(env_path, ['primary', 'mirror'])

        assert res.status_code == 200
        assert b'Example Domain' in res.data

    def test_replay_with_a_missing_next_database(self, tmp_path, env_path):
        load_text(env_path, 'primary', tmp_path / 'a.txt', 'example.warc.gz\t' + EXAMPLE_WARC + '\n')

        res = self.replay(env_path, ['primary', 'mirror'])

        assert res.status_code == 200
        assert b'Example Domain' in res.data
