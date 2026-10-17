import redis

from warcio.utils import to_native_str
from pywb.utils.binsearch import INDEX_FILE_BUFFER_SIZE, iter_exact
from pywb.utils.uwsgicache import get_uwsgi_cache

from pywb.warcserver.index.indexsource import RedisIndexSource

from pywb.utils.loaders import from_file_url
import six

import os
import logging
import glob
import hashlib

"""
The purpose of this module is to 'resolve' a warc/arc filename,
often found in a CDX file, to a full loadable url.

Supported resolvers are: url prefix, path index lookup and redis

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
    """Resolves a WARC filename with a path index: a text file sorted by
    filename, where each line has a filename and one or more paths or urls,
    separated by tabs. The file is read with a binary search.

    If pywb runs in uWSGI and the uWSGI cache ``pywb-pathindex`` is
    configured, the paths found are kept in it for ``CACHE_TTL`` seconds,
    shared by all the uWSGI workers.
    """
    UWSGI_CACHE_NAME = 'pywb-pathindex'

    CACHE_TTL = 600

    def __init__(self, pathindex_file):
        self.pathindex_file = pathindex_file
        self.cache = get_uwsgi_cache(self.UWSGI_CACHE_NAME)

    def __call__(self, filename, cdx):
        if not self.cache:
            return self.lookup(filename)

        # several path index files may share the cache
        key = hashlib.sha256(repr((self.pathindex_file, filename)).encode('utf-8')).hexdigest()

        value = self.cache.get(key)
        if value is not None:
            return to_native_str(value, 'utf-8').split('\t')

        paths = self.lookup(filename)

        # not found filenames aren't cached, so that new WARCs are found
        # as soon as they are added to the path index
        if paths:
            self.cache.set(key, '\t'.join(paths).encode('utf-8'), self.CACHE_TTL)

        return paths

    def lookup(self, filename):
        """Return the list of paths of this filename in the path index file"""
        paths = []
        with open(self.pathindex_file, 'rb', buffering=INDEX_FILE_BUFFER_SIZE) as reader:
            for pathline in iter_exact(reader, filename.encode('utf-8'), b'\t'):
                paths.extend(to_native_str(path, 'utf-8') for path in pathline.split(b'\t')[1:])

        return paths

    def __repr__(self):  # pragma: no cover
        return "PathIndexResolver('{0}')".format(self.pathindex_file)


#=================================================================
class DefaultResolverMixin(object):
    @classmethod
    def make_best_resolver(cls, path):
        if hasattr(path, '__call__'):
            return path

        if path.startswith('redis://'):
            return RedisResolver(path)

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
