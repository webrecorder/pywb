from pywb import get_test_dir
from pywb.utils.loaders import to_file_url

from pywb.warcserver.resource.pathresolvers import PrefixResolver, PathIndexResolver, RedisResolver
from pywb.warcserver.resource.pathresolvers import DefaultResolverMixin
from pywb.warcserver.index.cdxobject import CDXObject

import os

from fakeredis import FakeStrictRedis
from mock import patch


def test_path_index_resolvers():
    path_index = PathIndexResolver(get_test_dir() + 'text_content/pathindex.txt')

    cdx = CDXObject()
    assert list(path_index('example.warc.gz', cdx)) == ['invalid_path', 'sample_archive/warcs/example.warc.gz']
    assert list(path_index('iana.warc.gz', cdx)) == ['sample_archive/warcs/iana.warc.gz']
    assert list(path_index('not-found.gz', cdx)) == []


@patch('redis.StrictRedis', FakeStrictRedis)
def test_redis_resolver():
    resolver = RedisResolver('redis://127.0.0.1:6379/0/warc_map')

    cdx = CDXObject()
    assert resolver('example.warc.gz', cdx) == None

    resolver.redis.hset(resolver.redis_key_template, 'example.warc.gz', 'some_path/example.warc.gz')

    assert resolver('example.warc.gz', cdx) == 'some_path/example.warc.gz'


def test_make_best_resolver_http():
    res = DefaultResolverMixin.make_best_resolver('http://myhost.example.com/warcs/')
    assert isinstance(res, PrefixResolver)


def test_make_best_resolver_redis():
    res = DefaultResolverMixin.make_best_resolver('redis://myhost.example.com:1234/1')
    assert isinstance(res, RedisResolver)


def test_resolver_dir_and_file():
    a_file = os.path.realpath(__file__)
    a_dir = os.path.dirname(a_file)

    # a file -- assume path index
    res = DefaultResolverMixin.make_best_resolver(a_file)
    assert isinstance(res, PathIndexResolver)

    # a dir -- asume prefix
    res = DefaultResolverMixin.make_best_resolver(a_dir)
    assert isinstance(res, PrefixResolver)

    # not a valid file -- default to prefix
    res = DefaultResolverMixin.make_best_resolver('file://test/x_invalid')
    assert isinstance(res, PrefixResolver)


def test_resolver_list():
    paths = [to_file_url(os.path.realpath(__file__)),
             'http://myhost.example.com/warcs/',
             'redis://localhost:1234/0']

    res = DefaultResolverMixin.make_resolvers(paths)
    assert isinstance(res[0], PathIndexResolver)
    assert isinstance(res[1], PrefixResolver)
    assert isinstance(res[2], RedisResolver)


#=================================================================
if __name__ == "__main__":
    import doctest
    doctest.testmod()
