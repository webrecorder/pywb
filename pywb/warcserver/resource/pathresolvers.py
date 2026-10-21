import redis

from six.moves.urllib.parse import urlsplit, parse_qs, unquote
from warcio.utils import to_native_str
from pywb.utils.binsearch import iter_exact

from pywb.warcserver.index.indexsource import RedisIndexSource

from pywb.utils.loaders import from_file_url
import six

import os
import logging
import glob
import threading
import time

# optional, only needed for lmdb:// archive paths
try:
    import lmdb
except ImportError:  # pragma: no cover
    lmdb = None

"""
The purpose of this module is to 'resolve' a warc/arc filename,
often found in a CDX file, to a full loadable url.

Supported resolvers are: url prefix, path index lookup, redis and lmdb

make_best_resolver() attempts to guess the resolver method for given uri

"""


#=============================================================================
# PrefixResolver - convert cdx file entry to url with prefix
# if url contains specified string
#=============================================================================
class PrefixResolver(object):
    def __init__(self, template):
        self.template = template

    def __call__(self, filename, cdx):
        full_path = self.template

        if hasattr(cdx, '_formatter') and cdx._formatter:
            full_path = cdx._formatter.format(full_path)

        #path = os.path.join(full_path, filename)
        path = full_path + filename
        if '*' not in path:
            return path

        #res_path = self.resolve_coll(path, cdx.get('source'))
        coll = cdx.get('source-coll')
        if coll:
            return path.replace('*', coll)

        if '://' in path:
            return path

        paths = glob.glob(path)
        if paths:
            return paths
        else:
            return path

    def resolve_coll(self, path, source):
        if not source:
            return

        if os.path.sep != '/':
            source = source.replace(os.path.sep, '/')

        coll = source.split('/', 1)[0]
        return path.replace('*', coll)

    def __repr__(self):
        return "PrefixResolver('{0}')".format(self.template)


#=============================================================================
class RedisResolver(RedisIndexSource):
    def __call__(self, filename, cdx):
        redis_key = self.redis_key_template
        params = {}
        if hasattr(cdx, '_formatter') and cdx._formatter:
            redis_key = cdx._formatter.format(redis_key)
            params = cdx._formatter.params

        res = None

        if '*' in redis_key:
            for key in self.scan_keys(redis_key, params):
                res = self.redis.hget(key, filename)
                if res:
                    break
        else:
            res = self.redis.hget(redis_key, filename)

        res = to_native_str(res, 'utf-8')

        return res

    def __repr__(self):
        return "RedisResolver('{0}')".format(self.redis_url)


#=================================================================
class PathIndexResolver(object):
    def __init__(self, pathindex_file):
        self.pathindex_file = pathindex_file

    def __call__(self, filename, cdx):
        with open(self.pathindex_file, 'rb') as reader:
            result = iter_exact(reader, filename.encode('utf-8'), b'\t')

            for pathline in result:
                paths = pathline.split(b'\t')[1:]
                for path in paths:
                    yield to_native_str(path, 'utf-8')

    def __repr__(self):  # pragma: no cover
        return "PathIndexResolver('{0}')".format(self.pathindex_file)


#=================================================================
class LMDBResolver(object):
    """Resolve a WARC filename to its paths, from an LMDB database.

    Configured as ``lmdb:///path/to/env?db=name``: the LMDB environment
    (directory) and the named database, created by ``lmdb-pathindex``.
    The value of each key is the tab-separated list of paths of the
    path index, returned in the same order as ``PathIndexResolver``.

    The environment is opened read-only on the first lookup of each
    process, as LMDB can't be used across fork() (eg. uWSGI workers), and
    shared by the resolvers of that process. If the environment or the
    database can't be opened, the resolver returns no paths and tries
    again after RETRY_INTERVAL seconds.

    An environment opened before fork() is not closed by the child
    process, as LMDB would release the reader slots of the parent, and
    py-lmdb then refuses to open it again in the child: no lookups should
    be made before forking the workers.
    """
    SCHEME = 'lmdb'

    # max named databases in an environment
    MAX_DBS = 64

    # LMDB default max key size, in bytes
    MAX_KEY_SIZE = 511

    # seconds to wait before opening a missing environment or database again
    RETRY_INTERVAL = 60

    logger = logging.getLogger('warcserver')

    _lock = threading.Lock()

    # environment path -> (pid, lmdb.Environment)
    _envs = {}

    # environments opened before fork(), kept open by the child process
    _inherited_envs = []

    def __init__(self, env_path, db_name=None):
        if lmdb is None:
            raise ImportError('The lmdb package is required for lmdb:// archive paths, '
                              'install it with: pip install lmdb')

        self.env_path = os.path.abspath(env_path)
        self.db_name = db_name
        self._opened = None
        self._opened_pid = None
        self._retry_at = 0

    @classmethod
    def from_uri(cls, uri):
        return cls(*cls.parse_uri(uri))

    @classmethod
    def parse_uri(cls, uri):
        """ Return the environment path and the named database (or None)
        of a ``lmdb:///path/to/env?db=name`` uri
        """
        parts = urlsplit(uri)
        if parts.scheme != cls.SCHEME or parts.netloc or not parts.path:
            raise ValueError('Invalid LMDB uri, expected lmdb:///path/to/env?db=name: ' + uri)

        db_names = parse_qs(parts.query).get('db')
        return unquote(parts.path), db_names[-1] if db_names else None

    def __call__(self, filename, cdx):
        key = filename.encode('utf-8')
        if not key or len(key) > self.MAX_KEY_SIZE:
            return []

        value = self._get(key)
        if value is None:
            return []

        return value.decode('utf-8').split('\t')

    def _get(self, key):
        opened = self._open()
        if not opened:
            return None

        env, db = opened
        try:
            try:
                with env.begin(db=db) as txn:
                    return txn.get(key)
            except lmdb.MapResizedError:
                # the database was grown by the loader, use the new size
                env.set_mapsize(0)
                with env.begin(db=db) as txn:
                    return txn.get(key)
        except lmdb.Error as e:
            self._opened = None
            self._retry_at = time.monotonic() + self.RETRY_INTERVAL
            self.logger.warning('LMDB path index {0} lookup failed, retrying in {1} s: {2}'.format(
                self, self.RETRY_INTERVAL, e))
            return None

    def _open(self):
        pid = os.getpid()
        if self._opened is not None and self._opened_pid == pid:
            return self._opened

        if time.monotonic() < self._retry_at:
            return None

        try:
            env = self.get_env(self.env_path)
            db = env.open_db(self.db_name.encode('utf-8'), create=False) if self.db_name else None
        except lmdb.Error as e:
            self._retry_at = time.monotonic() + self.RETRY_INTERVAL
            self.logger.warning('LMDB path index {0} not available, retrying in {1} s: {2}'.format(
                self, self.RETRY_INTERVAL, e))
            return None

        self._opened = (env, db)
        self._opened_pid = pid
        return self._opened

    @classmethod
    def get_env(cls, env_path):
        """ Return the read-only LMDB environment of this process for env_path
        """
        pid = os.getpid()
        with cls._lock:
            opened = cls._envs.get(env_path)
            if opened and opened[0] == pid:
                return opened[1]

            if opened:
                cls._inherited_envs.append(cls._envs.pop(env_path)[1])

            # lock: needed to read a consistent version while the loader writes
            # readahead: disabled, as lookups are random reads
            env = lmdb.open(env_path, readonly=True, lock=True, readahead=False,
                            max_dbs=cls.MAX_DBS)

            cls._envs[env_path] = (pid, env)
            return env

    @classmethod
    def close_envs(cls):
        """ Close the environments opened by this process
        """
        pid = os.getpid()
        with cls._lock:
            for env_path, (env_pid, env) in list(cls._envs.items()):
                if env_pid == pid:
                    env.close()
                    del cls._envs[env_path]

    def __repr__(self):
        return "LMDBResolver('{0}', db='{1}')".format(self.env_path, self.db_name or '')


#=================================================================
class DefaultResolverMixin(object):
    @classmethod
    def make_best_resolver(cls, path):
        if hasattr(path, '__call__'):
            return path

        if path.startswith('redis://'):
            return RedisResolver(path)

        if path.startswith('lmdb://'):
            return LMDBResolver.from_uri(path)

        path = from_file_url(path)

        if os.path.isfile(path):
            return PathIndexResolver(path)

        else:
            return PrefixResolver(path)

    @classmethod
    def make_resolvers(cls, paths):
        if isinstance(paths, six.string_types):
            paths = [paths]
        elif paths is None:
            paths = []

        return [cls.make_best_resolver(path) for path in paths]
