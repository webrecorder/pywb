"""
# PathIndexResolver tests
>>> list(PathIndexResolver(get_test_dir() + 'text_content/pathindex.txt')('example.warc.gz'))
['invalid_path', 'sample_archive/warcs/example.warc.gz']

>>> list(PathIndexResolver(get_test_dir() + 'text_content/pathindex.txt')('iana.warc.gz'))
['sample_archive/warcs/iana.warc.gz']

>>> list(PathIndexResolver(get_test_dir() + 'text_content/pathindex.txt')('not-found.gz'))
[]

# RedisResolver tests
# not set, no match
>>> redis_resolver('example.warc.gz')
[]

>>> hset_path('example.warc.gz', 'some_path/example.warc.gz')
>>> redis_resolver('example.warc.gz')
['some_path/example.warc.gz']


make_best_resolver tests
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
>>> r = make_best_resolver(to_file_url(os.path.realpath(__file__)))
>>> r.__class__.__name__
'PathIndexResolver'

# a dir
>>> path = os.path.realpath(__file__)
>>> r = make_best_resolver(to_file_url(os.path.dirname(path)))
>>> r.__class__.__name__
'PrefixResolver'


# make_best_resolvers
>>> r = make_best_resolvers(['http://example.com/warcs/',\
                            'redis://example.com:1234/1'])
>>> map(lambda x: x.__class__.__name__, r)
['PrefixResolver', 'RedisResolver']
"""

from pywb import get_test_dir
from pywb.warc.pathresolvers import PrefixResolver, PathIndexResolver, RedisResolver
from pywb.warc.pathresolvers import make_best_resolver, make_best_resolvers
from pywb.utils.loaders import to_file_url

import os

from fakeredis import FakeStrictRedis
from mock import patch

@patch('redis.StrictRedis', FakeStrictRedis)
def init_redis_resolver():
    return RedisResolver('redis://127.0.0.1:6379/0')


def hset_path(filename, path):
    redis_resolver.redis.hset(redis_resolver.key_prefix + filename, 'path', path)

redis_resolver = init_redis_resolver()

#=================================================================
if __name__ == "__main__":
    import doctest
    doctest.testmod()
