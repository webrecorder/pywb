from pywb.webagg.aggregator import RedisMultiKeyIndexSource
from .testutils import to_path, to_json_list, FakeRedisTests, BaseTestClass, TEST_CDX_PATH


class TestRedisAgg(FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRedisAgg, cls).setup_class()
        cls.add_cdx_to_redis(TEST_CDX_PATH + 'example2.cdxj', 'FOO:example:cdxj')
        cls.add_cdx_to_redis(TEST_CDX_PATH + 'dupes.cdxj', 'FOO:dupes:cdxj')

        cls.indexloader = RedisMultiKeyIndexSource('redis://localhost/2/{user}:{coll}:cdxj')

    def test_redis_agg_all(self):
        res, errs = self.indexloader({'url': 'example.com/', 'param.user': 'FOO', 'param.coll': '*'})

        exp = [
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
            {'source': 'FOO:example:cdxj', 'timestamp': '20160225042329', 'filename': 'example2.warc.gz'}
        ]

        assert(errs == {})
        assert(to_json_list(res) == exp)

    def test_redis_agg_one(self):
        res, errs = self.indexloader({'url': 'example.com/', 'param.user': 'FOO', 'param.coll': 'dupes'})

        exp = [
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
        ]

        assert(errs == {})
        assert(to_json_list(res) == exp)

    def test_redis_not_found(self):
        res, errs = self.indexloader({'url': 'example.com/'})

        exp = []

        assert(errs == {})
        assert(to_json_list(res) == exp)


