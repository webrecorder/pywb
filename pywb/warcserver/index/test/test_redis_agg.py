from pywb.warcserver.index.aggregator import RedisMultiKeyIndexSource
from pywb.warcserver.test.testutils import to_path, to_json_list, FakeRedisTests, BaseTestClass, TEST_CDX_PATH
import pytest


class TestRedisAgg(FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRedisAgg, cls).setup_class()
        cls.add_cdx_to_redis(TEST_CDX_PATH + 'example2.cdxj', 'FOO:example:cdxj')
        cls.add_cdx_to_redis(TEST_CDX_PATH + 'dupes.cdxj', 'FOO:dupes:cdxj')

        # scan loader
        cls.scan_loader = RedisMultiKeyIndexSource('redis://localhost/2/{user}:{coll}:cdxj')

        cls.redis.sadd('FOO:<all>:list', 'dupes')
        cls.redis.sadd('FOO:<all>:list', 'example')

        cls.member_list_loader = RedisMultiKeyIndexSource('redis://localhost/2/{user}:{coll}:cdxj',
                                                          member_key_templ='FOO:<all>:list')

    @pytest.fixture(params=['scan', 'member-list'])
    def indexloader(self, request):
        if request.param == 'scan':
            return self.scan_loader
        else:
            return self.member_list_loader

    def test_redis_agg_all(self, indexloader):
        res, errs = indexloader({'url': 'example.com/', 'param.user': 'FOO', 'param.coll': '*'})

        exp = [
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
            {'source': 'FOO:example:cdxj', 'timestamp': '20160225042329', 'filename': 'example2.warc.gz'}
        ]

        assert(errs == {})
        assert(to_json_list(res) == exp)

    def test_redis_agg_one(self, indexloader):
        res, errs = indexloader({'url': 'example.com/', 'param.user': 'FOO', 'param.coll': 'dupes'})

        exp = [
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
        ]

        assert(errs == {})
        assert(to_json_list(res) == exp)

    def test_redis_not_found(self, indexloader):
        res, errs = indexloader({'url': 'example.com/'})

        exp = []

        assert(errs == {})
        assert(to_json_list(res) == exp)


