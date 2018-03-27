from pywb import get_test_dir
from pywb.utils.loaders import to_file_url

from pywb.warcserver.resource.pathresolvers import PrefixResolver, PathIndexResolver, RedisResolver
from pywb.warcserver.resource.pathresolvers import DefaultResolverMixin
from pywb.warcserver.index.cdxobject import CDXObject

import os

from fakeredis import FakeStrictRedis
from mock import patch


# ============================================================================
class TestPathIndex(object):
    def test_path_index_resolvers(self):
        path = os.path.join(get_test_dir(), 'text_content', 'pathindex.txt')
        path_index = PathIndexResolver(path)

        cdx = CDXObject()
        assert list(path_index('example.warc.gz', cdx)) == ['invalid_path', 'sample_archive/warcs/example.warc.gz']
        assert list(path_index('iana.warc.gz', cdx)) == ['sample_archive/warcs/iana.warc.gz']
        assert list(path_index('not-found.gz', cdx)) == []

    def test_resolver_dir_wildcard(self):
        resolver = DefaultResolverMixin.make_best_resolver(os.path.join(get_test_dir(), '*', ''))

        cdx = CDXObject()
        res = resolver('example.warc.gz', cdx)
        assert len(res) == 1
        assert res[0] == os.path.join(get_test_dir(), 'warcs', 'example.warc.gz')

    def test_resolver_dir_wildcard_with_coll(self):
        resolver = DefaultResolverMixin.make_best_resolver('s3://bucket/colls/*/archives/')

        cdx = CDXObject()
        cdx['source'] = 'my-coll/indexes/index.cdxj'
        cdx['source-coll'] = 'my-coll'

        res = resolver('example.warc.gz', cdx)
        assert res == 's3://bucket/colls/my-coll/archives/example.warc.gz'

    def test_resolver_dir_wildcard_as_file_url(self):
        url = to_file_url(get_test_dir()) +  '/*/'
        resolver = DefaultResolverMixin.make_best_resolver(url)

        cdx = CDXObject()
        res = resolver('example.warc.gz', cdx)
        assert len(res) == 1
        assert res[0] == os.path.abspath(os.path.join(get_test_dir(), 'warcs', 'example.warc.gz'))

    def test_resolver_http_prefix(self):
        resolver = DefaultResolverMixin.make_best_resolver('http://example.com/prefix/')

        cdx = CDXObject()
        res = resolver('example.warc.gz', cdx)
        assert res == 'http://example.com/prefix/example.warc.gz'

    def test_resolver_http_prefix_not_wildcard(self):
        resolver = DefaultResolverMixin.make_best_resolver('http://example.com/*/')

        cdx = CDXObject()
        res = resolver('example.warc.gz', cdx)
        assert res == 'http://example.com/*/example.warc.gz'

    @patch('redis.StrictRedis', FakeStrictRedis)
    def test_redis_resolver(self):
        resolver = RedisResolver('redis://127.0.0.1:6379/0/warc_map')

        cdx = CDXObject()
        assert resolver('example.warc.gz', cdx) == None

        resolver.redis.hset(resolver.redis_key_template, 'example.warc.gz', 'some_path/example.warc.gz')

        assert resolver('example.warc.gz', cdx) == 'some_path/example.warc.gz'

    @patch('redis.StrictRedis', FakeStrictRedis)
    def test_redis_resolver_multi_key(self):
        resolver = RedisResolver('redis://127.0.0.1:6379/0/*:warc')

        cdx = CDXObject()
        assert resolver('example.warc.gz', cdx) == None

        resolver.redis.hset('A:warc', 'example.warc.gz', 'some_path/example.warc.gz')
        resolver.redis.hset('B:warc', 'example-2.warc.gz', 'some_path/example-2.warc.gz')

        assert resolver('example.warc.gz', cdx) == 'some_path/example.warc.gz'
        assert resolver('example-2.warc.gz', cdx) == 'some_path/example-2.warc.gz'

    @patch('redis.StrictRedis', FakeStrictRedis)
    def test_redis_resolver_multi_key_with_member_set(self):
        resolver = RedisResolver('redis://127.0.0.1:6379/0/*:warc',
                                 member_key_templ='member_set')

        cdx = CDXObject()
        assert resolver('example.warc.gz', cdx) == None

        resolver.redis.hset('A:warc', 'example.warc.gz', 'some_path/example.warc.gz')
        resolver.redis.hset('B:warc', 'example-2.warc.gz', 'some_path/example-2.warc.gz')

        resolver.redis.sadd('member_set', 'A')

        # only A:warc used
        assert resolver('example.warc.gz', cdx) == 'some_path/example.warc.gz'
        assert resolver('example-2.warc.gz', cdx) == None

        resolver.redis.sadd('member_set', 'B')

        # A:warc and B:warc used
        assert resolver('example.warc.gz', cdx) == 'some_path/example.warc.gz'
        assert resolver('example-2.warc.gz', cdx) == 'some_path/example-2.warc.gz'

        assert resolver.member_key_type == 'set'

    @patch('redis.StrictRedis', FakeStrictRedis)
    def test_redis_resolver_multi_key_with_member_hash(self):
        resolver = RedisResolver('redis://127.0.0.1:6379/0/*:warc',
                                 member_key_templ='member_hash')

        cdx = CDXObject()
        assert resolver('example.warc.gz', cdx) == None

        resolver.redis.hset('A:warc', 'example.warc.gz', 'some_path/example.warc.gz')
        resolver.redis.hset('B:warc', 'example-2.warc.gz', 'some_path/example-2.warc.gz')

        resolver.redis.hset('member_hash', '1', 'A')

        # only A:warc used
        assert resolver('example.warc.gz', cdx) == 'some_path/example.warc.gz'
        assert resolver('example-2.warc.gz', cdx) == None

        resolver.redis.hset('member_hash', '2', 'B')

        # A:warc and B:warc used
        assert resolver('example.warc.gz', cdx) == 'some_path/example.warc.gz'
        assert resolver('example-2.warc.gz', cdx) == 'some_path/example-2.warc.gz'

        assert resolver.member_key_type == 'hash'

    def test_make_best_resolver_http(self):
        res = DefaultResolverMixin.make_best_resolver('http://myhost.example.com/warcs/')
        assert isinstance(res, PrefixResolver)
        assert repr(res) == "PrefixResolver('http://myhost.example.com/warcs/')"

    def test_make_best_resolver_redis(self):
        res = DefaultResolverMixin.make_best_resolver('redis://myhost.example.com:1234/1')
        assert isinstance(res, RedisResolver)
        assert repr(res) == "RedisResolver('redis://myhost.example.com:1234/1')"

    def test_make_best_resolver_pathindex(self):
        path = os.path.join(get_test_dir(), 'text_content', 'pathindex.txt')
        res = DefaultResolverMixin.make_best_resolver(path)
        assert isinstance(res, PathIndexResolver)
        assert repr(res) == "PathIndexResolver('{0}')".format(path)

    def test_resolver_dir_and_file(self):
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

    def test_resolver_list(self):
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
