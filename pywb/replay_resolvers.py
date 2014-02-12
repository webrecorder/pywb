import redis
import binsearch.binsearch

import urlparse
import os
import logging

#======================================
# PrefixResolver - convert cdx file entry to url with prefix if url contains specified string
#======================================
class PrefixResolver:
    def __init__(self, prefix, contains):
        self.prefix = prefix
        self.contains = contains if contains else ''

    def __call__(self, filename):
        return [self.prefix + filename] if (self.contains in filename) else []

    def __repr__(self):
        if self.contains:
            return "PrefixResolver('{0}', contains = '{1}')".format(self.prefix, self.contains)
        else:
            return "PrefixResolver('{0}')".format(self.prefix)


#======================================
class RedisResolver:
    def __init__(self, redis_url, key_prefix = None):
        self.redis_url = redis_url
        self.key_prefix = key_prefix if key_prefix else 'w:'
        self.redis = redis.StrictRedis.from_url(redis_url)

    def __call__(self, filename):
        try:
            redis_val = self.redis.hget(self.key_prefix + filename, 'path')
            return [redis_val] if redis_val else None
        except Exception as e:
            print e
            return None

    def __repr__(self):
        return "RedisResolver('{0}')".format(self.redis_url)


#======================================
class PathIndexResolver:
    def __init__(self, pathindex_file):
        self.pathindex_file = pathindex_file
        self.reader = binsearch.binsearch.FileReader(pathindex_file)

    def __call__(self, filename):
        result = binsearch.binsearch.iter_exact(self.reader, filename, '\t')

        def gen_list(result):
            for pathline in result:
                path = pathline.split('\t')
                if len(path) == 2:
                    yield path[1]

        return gen_list(result)

    def __repr__(self):
        return "PathIndexResolver('{0}')".format(self.pathindex_file)


#TODO: more options (remote files, contains param, etc..)
# find best resolver given the path
def make_best_resolver(param):
    """
    # http path
    >>> make_best_resolver('http://myhost.example.com/warcs/')
    PrefixResolver('http://myhost.example.com/warcs/')

    # http path w/ contains param
    >>> make_best_resolver(['http://myhost.example.com/warcs/', '/'])
    PrefixResolver('http://myhost.example.com/warcs/', contains = '/')

    # redis path
    >>> make_best_resolver('redis://myhost.example.com:1234/1')
    RedisResolver('redis://myhost.example.com:1234/1')

    # a file
    >>> class_name(make_best_resolver('file://' + os.path.realpath(__file__)))
    'PathIndexResolver'

    # a dir
    >>> class_name(make_best_resolver('file://' + os.path.dirname(os.path.realpath(__file__))))
    'PrefixResolver'

    """

    if isinstance(param, list):
        path = param[0]
        arg = param[1]
    else:
        path = param
        arg = None

    url_parts = urlparse.urlsplit(path)

    if url_parts.scheme == 'redis':
        logging.info('Adding Redis Index: ' + path)
        return RedisResolver(path, arg)

    if url_parts.scheme == 'file':
        path = url_parts.path

    if os.path.isfile(path):
        logging.info('Adding Path Index: ' + path)
        return PathIndexResolver(path)

    # non-file paths always treated as prefix for now
    else:
        logging.info('Adding Archive Path Source: ' + path)
        return PrefixResolver(path, arg)


#=================================================================
def make_best_resolvers(paths):
    """
    >>> make_best_resolvers(['http://myhost.example.com/warcs/', 'redis://myhost.example.com:1234/1'])
    [PrefixResolver('http://myhost.example.com/warcs/'), RedisResolver('redis://myhost.example.com:1234/1')]
    """
    if hasattr(paths, '__iter__'):
        return map(make_best_resolver, paths)
    else:
        return [make_best_resolver(paths)]


import utils
#=================================================================
if __name__ == "__main__" or utils.enable_doctests():

    def class_name(obj):
         return obj.__class__.__name__

    import doctest
    doctest.testmod()

