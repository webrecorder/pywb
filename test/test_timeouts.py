from gevent import monkey; monkey.patch_all(thread=False)
import time
from rezag.indexsource import FileIndexSource

from rezag.aggindexsource import SimpleAggregator, TimeoutMixin
from rezag.aggindexsource import GeventTimeoutAggregator, GeventTimeoutAggregator

from .testutils import json_list


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

TimeoutAggregator = GeventTimeoutAggregator



def setup_module():
    global sources
    sources = {'slow': TimeoutFileSource('testdata/example.cdxj', 0.2),
               'slower': TimeoutFileSource('testdata/dupes.cdxj', 0.5)
              }



def test_timeout_long_all_pass():
    agg = TimeoutAggregator(sources, timeout=1.0)

    res = agg(dict(url='http://example.com/'))

    exp = [{'source': 'slower', 'timestamp': '20140127171200'},
           {'source': 'slower', 'timestamp': '20140127171251'},
           {'source': 'slow', 'timestamp': '20160225042329'}]

    assert(json_list(res, fields=['source', 'timestamp']) == exp)


def test_timeout_slower_skipped_1():
    agg = GeventTimeoutAggregator(sources, timeout=0.49)

    res = agg(dict(url='http://example.com/'))

    exp = [{'source': 'slow', 'timestamp': '20160225042329'}]

    assert(json_list(res, fields=['source', 'timestamp']) == exp)



def test_timeout_slower_skipped_2():
    agg = GeventTimeoutAggregator(sources, timeout=0.19)

    res = agg(dict(url='http://example.com/'))

    exp = []

    assert(json_list(res, fields=['source', 'timestamp']) == exp)



def test_timeout_skipping():
    assert(sources['slow'].calls == 3)
    assert(sources['slower'].calls == 3)

    agg = GeventTimeoutAggregator(sources, timeout=0.49,
                                  t_count=2, t_duration=2.0)

    exp = [{'source': 'slow', 'timestamp': '20160225042329'}]

    res = agg(dict(url='http://example.com/'))
    assert(json_list(res, fields=['source', 'timestamp']) == exp)
    assert(sources['slow'].calls == 4)
    assert(sources['slower'].calls == 4)

    res = agg(dict(url='http://example.com/'))
    assert(json_list(res, fields=['source', 'timestamp']) == exp)
    assert(sources['slow'].calls == 5)
    assert(sources['slower'].calls == 5)

    res = agg(dict(url='http://example.com/'))
    assert(json_list(res, fields=['source', 'timestamp']) == exp)
    assert(sources['slow'].calls == 6)
    assert(sources['slower'].calls == 5)

    res = agg(dict(url='http://example.com/'))
    assert(json_list(res, fields=['source', 'timestamp']) == exp)
    assert(sources['slow'].calls == 7)
    assert(sources['slower'].calls == 5)

    time.sleep(2.01)

    res = agg(dict(url='http://example.com/'))
    assert(json_list(res, fields=['source', 'timestamp']) == exp)
    assert(sources['slow'].calls == 8)
    assert(sources['slower'].calls == 6)


