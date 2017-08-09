from gevent import monkey; monkey.patch_all(thread=False)
import time
from pywb.warcserver.index.indexsource import FileIndexSource

from pywb.warcserver.index.aggregator import SimpleAggregator, TimeoutMixin
from pywb.warcserver.index.aggregator import GeventTimeoutAggregator, GeventTimeoutAggregator

from pywb.warcserver.test.testutils import to_json_list, TEST_CDX_PATH


class TimeoutFileSource(FileIndexSource):
    def __init__(self, filename, timeout):
        super(TimeoutFileSource, self).__init__(filename)
        self.timeout = timeout
        self.calls = 0

    def load_index(self, params):
        self.calls += 1
        print('Sleeping')
        time.sleep(self.timeout)
        return super(TimeoutFileSource, self).load_index(params)


class TestTimeouts(object):
    @classmethod
    def setup_class(cls):
        cls.sources = {'slow': TimeoutFileSource(TEST_CDX_PATH + 'example2.cdxj', 0.2),
                       'slower': TimeoutFileSource(TEST_CDX_PATH + 'dupes.cdxj', 0.5)
                      }

    def test_timeout_long_all_pass(self):
        agg = GeventTimeoutAggregator(self.sources, timeout=1.0)

        res, errs = agg(dict(url='http://example.com/'))

        exp = [{'source': 'slower', 'timestamp': '20140127171200'},
               {'source': 'slower', 'timestamp': '20140127171251'},
               {'source': 'slow', 'timestamp': '20160225042329'}]

        assert(to_json_list(res, fields=['source', 'timestamp']) == exp)

        assert(errs == {})

    def test_timeout_slower_skipped_1(self):
        agg = GeventTimeoutAggregator(self.sources, timeout=0.40)

        res, errs = agg(dict(url='http://example.com/'))

        exp = [{'source': 'slow', 'timestamp': '20160225042329'}]

        assert(to_json_list(res, fields=['source', 'timestamp']) == exp)

        assert(errs == {'slower': 'timeout'})

    def test_timeout_slower_all_skipped(self):
        agg = GeventTimeoutAggregator(self.sources, timeout=0.10)

        res, errs = agg(dict(url='http://example.com/'))

        exp = []

        assert(to_json_list(res, fields=['source', 'timestamp']) == exp)

        assert(errs == {'slower': 'timeout', 'slow': 'timeout'})

    def test_timeout_skipping(self):
        assert(self.sources['slow'].calls == 3)
        assert(self.sources['slower'].calls == 3)

        agg = GeventTimeoutAggregator(self.sources, timeout=0.40,
                                      t_count=2, t_duration=1.0)

        exp = [{'source': 'slow', 'timestamp': '20160225042329'}]

        res, errs = agg(dict(url='http://example.com/'))
        assert(to_json_list(res, fields=['source', 'timestamp']) == exp)
        assert(self.sources['slow'].calls == 4)
        assert(self.sources['slower'].calls == 4)

        assert(errs == {'slower': 'timeout'})

        res, errs = agg(dict(url='http://example.com/'))
        assert(to_json_list(res, fields=['source', 'timestamp']) == exp)
        assert(self.sources['slow'].calls == 5)
        assert(self.sources['slower'].calls == 5)

        assert(errs == {'slower': 'timeout'})

        res, errs = agg(dict(url='http://example.com/'))
        assert(to_json_list(res, fields=['source', 'timestamp']) == exp)
        assert(self.sources['slow'].calls == 6)
        assert(self.sources['slower'].calls == 5)

        assert(errs == {})

        res, errs = agg(dict(url='http://example.com/'))
        assert(to_json_list(res, fields=['source', 'timestamp']) == exp)
        assert(self.sources['slow'].calls == 7)
        assert(self.sources['slower'].calls == 5)

        assert(errs == {})

        time.sleep(1.5)

        res, errs = agg(dict(url='http://example.com/'))
        assert(to_json_list(res, fields=['source', 'timestamp']) == exp)
        assert(self.sources['slow'].calls == 8)
        assert(self.sources['slower'].calls == 6)

        assert(errs == {'slower': 'timeout'})

