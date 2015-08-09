import redis

from pywb.utils.binsearch import iter_exact

import urlparse
import urllib
import os
import logging

"""
The purpose of this module is to 'resolve' a warc/arc filename,
often found in a CDX file, to a full loadable url.

Supported resolvers are: url prefix, path index lookup and redis

make_best_resolver() attempts to guess the resolver method for given uri

"""


#=================================================================
# PrefixResolver - convert cdx file entry to url with prefix
# if url contains specified string
#=================================================================
class PrefixResolver:
    def __init__(self, prefix, contains):
        self.prefix = prefix
        self.contains = contains if contains else ''

    def __call__(self, filename):
        # use os path seperator
        filename = filename.replace('/', os.path.sep)
        return [self.prefix + filename] if (self.contains in filename) else []

    def __repr__(self):
        if self.contains:
            return ("PrefixResolver('{0}', contains = '{1}')"
                    .format(self.prefix, self.contains))
        else:
            return "PrefixResolver('{0}')".format(self.prefix)


#=================================================================
class RedisResolver:
    def __init__(self, redis_url, key_prefix=None):
        self.redis_url = redis_url
        self.key_prefix = key_prefix if key_prefix else 'w:'
        self.redis = redis.StrictRedis.from_url(redis_url)

    def __call__(self, filename):
        redis_val = self.redis.hget(self.key_prefix + filename, 'path')
        return [redis_val] if redis_val else []

    def __repr__(self):
        return "RedisResolver('{0}')".format(self.redis_url)


#=================================================================
class PathIndexResolver:
    def __init__(self, pathindex_file):
        self.pathindex_file = pathindex_file

    def __call__(self, filename):
        with open(self.pathindex_file, 'rb') as reader:
            result = iter_exact(reader, filename, '\t')

            for pathline in result:
                paths = pathline.split('\t')[1:]
                for path in paths:
                    yield path

    def __repr__(self):  # pragma: no cover
        return "PathIndexResolver('{0}')".format(self.pathindex_file)


#=================================================================
#TODO: more options (remote files, contains param, etc..)
# find best resolver given the path
def make_best_resolver(param):
    if isinstance(param, list):
        path = param[0]
        arg = param[1]
    else:
        path = param
        arg = None

    url_parts = urlparse.urlsplit(path)

    if url_parts.scheme == 'redis':
        logging.debug('Adding Redis Index: ' + path)
        return RedisResolver(path, arg)

    if url_parts.scheme == 'file':
        path = url_parts.path
        path = urllib.url2pathname(path)

    if os.path.isfile(path):
        logging.debug('Adding Path Index: ' + path)
        return PathIndexResolver(path)

    # non-file paths always treated as prefix for now
    else:
        logging.debug('Adding Archive Path Source: ' + path)
        return PrefixResolver(path, arg)


#=================================================================
def make_best_resolvers(paths):
    if hasattr(paths, '__iter__'):
        return map(make_best_resolver, paths)
    else:
        return [make_best_resolver(paths)]
