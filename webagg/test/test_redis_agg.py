from webagg.aggregator import RedisMultiKeyIndexSource
from .testutils import to_path, to_json_list, FakeRedisTests, BaseTestClass


class TestRedisAgg(FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRedisAgg, cls).setup_class()
        cls.add_cdx_to_redis(to_path('testdata/example.cdxj'), 'FOO:example:cdxj')
        cls.add_cdx_to_redis(to_path('testdata/dupes.cdxj'), 'FOO:dupes:cdxj')

        cls.indexloader = RedisMultiKeyIndexSource('redis://localhost/2/{user}:{coll}:cdxj')

    def test_redis_agg_all(self):
        res, errs = self.indexloader({'url': 'example.com/', 'param.user': 'FOO', 'param.coll': '*'})

        exp = [
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171200', 'filename': 'dupes.warc.gz'},
            {'source': 'FOO:dupes:cdxj', 'timestamp': '20140127171251', 'filename': 'dupes.warc.gz'},
            {'source': 'FOO:example:cdxj', 'timestamp': '20160225042329', 'filename': 'example.warc.gz'}
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


