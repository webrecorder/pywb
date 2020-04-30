import redis

from warcio.utils import to_native_str
from pywb.utils.binsearch import iter_exact

from pywb.warcserver.index.indexsource import RedisIndexSource

from pywb.utils.loaders import from_file_url
import six

import os
import logging
import glob

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
