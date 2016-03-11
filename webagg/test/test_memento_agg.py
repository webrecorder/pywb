from gevent import monkey; monkey.patch_all(thread=False)

from webagg.aggregator import SimpleAggregator, GeventTimeoutAggregator
from webagg.aggregator import BaseAggregator

from webagg.indexsource import FileIndexSource, RemoteIndexSource, MementoIndexSource
from .testutils import to_json_list, to_path

import json
import pytest
import time
import six

from webagg.handlers import IndexHandler


sources = {
    'local': FileIndexSource(to_path('testdata/iana.cdxj')),
    'ia': MementoIndexSource.from_timegate_url('http://web.archive.org/web/'),
    'ait': MementoIndexSource.from_timegate_url('http://wayback.archive-it.org/all/'),
    'bl': MementoIndexSource.from_timegate_url('http://www.webarchive.org.uk/wayback/archive/'),
    'rhiz': MementoIndexSource.from_timegate_url('http://webenact.rhizome.org/vvork/', path='*')
}


aggs = {'simple': SimpleAggregator(sources),
        'gevent': GeventTimeoutAggregator(sources, timeout=5.0),
       }

agg_tm = {'gevent': GeventTimeoutAggregator(sources, timeout=0.0)}

nf = {'notfound': FileIndexSource(to_path('testdata/not-found-x'))}
agg_nf = {'simple': SimpleAggregator(nf),
          'gevent': GeventTimeoutAggregator(nf, timeout=5.0),
         }


@pytest.mark.parametrize("agg", list(aggs.values()), ids=list(aggs.keys()))
def test_mem_agg_index_1(agg):
    url = 'http://iana.org/'
    res, errs = agg(dict(url=url, closest='20140126000000', limit=5))


    exp = [{"timestamp": "20140126093743", "load_url": "http://web.archive.org/web/20140126093743id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140126200624", "filename": "iana.warc.gz", "source": "local"},
           {"timestamp": "20140123034755", "load_url": "http://web.archive.org/web/20140123034755id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140129175203", "load_url": "http://web.archive.org/web/20140129175203id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140107040552", "load_url": "http://wayback.archive-it.org/all/20140107040552id_/http://iana.org/", "source": "ait"}
          ]

    assert(to_json_list(res) == exp)
    assert(errs == {'bl': "NotFoundException('http://www.webarchive.org.uk/wayback/archive/http://iana.org/',)",
                    'rhiz': "NotFoundException('http://webenact.rhizome.org/vvork/http://iana.org/',)"})

@pytest.mark.parametrize("agg", list(aggs.values()), ids=list(aggs.keys()))
def test_mem_agg_index_2(agg):
    url = 'http://example.com/'
    res, errs = agg(dict(url=url, closest='20100512', limit=6))

    exp = [{"timestamp": "20100513010014", "load_url": "http://www.webarchive.org.uk/wayback/archive/20100513010014id_/http://example.com/", "source": "bl"},
            {"timestamp": "20100512204410", "load_url": "http://www.webarchive.org.uk/wayback/archive/20100512204410id_/http://example.com/", "source": "bl"},
            #{"timestamp": "20100513052358", "load_url": "http://web.archive.org/web/20100513052358id_/http://example.com/", "source": "ia"},
            {"timestamp": "20100511201151", "load_url": "http://wayback.archive-it.org/all/20100511201151id_/http://example.com/", "source": "ait"},
            {"timestamp": "20100514231857", "load_url": "http://web.archive.org/web/20100514231857id_/http://example.com/", "source": "ia"},
            {"timestamp": "20100514231857", "load_url": "http://wayback.archive-it.org/all/20100514231857id_/http://example.com/", "source": "ait"},
            {"timestamp": "20100519202418", "load_url": "http://web.archive.org/web/20100519202418id_/http://example.com/", "source": "ia"}]

    assert(to_json_list(res) == exp)
    assert(errs == {'rhiz': "NotFoundException('http://webenact.rhizome.org/vvork/http://example.com/',)"})


@pytest.mark.parametrize("agg", list(aggs.values()), ids=list(aggs.keys()))
def test_mem_agg_index_3(agg):
    url = 'http://vvork.com/'
    res, errs = agg(dict(url=url, closest='20141001', limit=5))

    exp = [{"timestamp": "20141006184357", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"},
           {"timestamp": "20141018133107", "load_url": "http://web.archive.org/web/20141018133107id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20141020161243", "load_url": "http://web.archive.org/web/20141020161243id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20140806161228", "load_url": "http://web.archive.org/web/20140806161228id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20131004231540", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}]

    assert(to_json_list(res) == exp)
    assert(errs == {})


@pytest.mark.parametrize("agg", list(aggs.values()), ids=list(aggs.keys()))
def test_mem_agg_index_4(agg):
    url = 'http://vvork.com/'
    res, errs = agg(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait'))

    exp = [{"timestamp": "20141006184357", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"},
           {"timestamp": "20131004231540", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}]

    assert(to_json_list(res) == exp)
    assert(errs == {})


@pytest.mark.parametrize("agg", list(agg_nf.values()), ids=list(agg_nf.keys()))
def test_mem_agg_not_found(agg):
    url = 'http://vvork.com/'
    res, errs = agg(dict(url=url, closest='20141001', limit=2))

    assert(to_json_list(res) == [])
    assert(errs == {'notfound': "NotFoundException('testdata/not-found-x',)"})


@pytest.mark.parametrize("agg", list(agg_tm.values()), ids=list(agg_tm.keys()))
def test_mem_agg_timeout(agg):
    url = 'http://vvork.com/'

    orig_source = BaseAggregator.load_child_source
    def load_child_source(self, name, source, params):
        time.sleep(0.1)
        return orig_source(name, source, params)

    BaseAggregator.load_child_source = load_child_source
    res, errs = agg(dict(url=url, closest='20141001', limit=2))
    BaseAggregator.load_child_source = orig_source

    assert(to_json_list(res) == [])
    assert(errs == {'local': 'timeout',
                    'ait': 'timeout', 'bl': 'timeout', 'ia': 'timeout', 'rhiz': 'timeout'})


def test_handler_output_cdxj():
    agg = GeventTimeoutAggregator(sources, timeout=5.0)
    handler = IndexHandler(agg)
    url = 'http://vvork.com/'
    headers, res, errs = handler(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait'))

    exp = """\
com,vvork)/ 20141006184357 {"url": "http://www.vvork.com/", "mem_rel": "memento", "memento_url": "http://webenact.rhizome.org/vvork/20141006184357/http://www.vvork.com/", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"}
com,vvork)/ 20131004231540 {"url": "http://vvork.com/", "mem_rel": "last memento", "memento_url": "http://wayback.archive-it.org/all/20131004231540/http://vvork.com/", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}
"""

    assert(headers['Content-Type'] == 'text/x-cdxj')
    assert(''.join(res) == exp)
    assert(errs == {})


def test_handler_output_json():
    agg = GeventTimeoutAggregator(sources, timeout=5.0)
    handler = IndexHandler(agg)
    url = 'http://vvork.com/'
    headers, res, errs = handler(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait', output='json'))

    exp = """\
{"urlkey": "com,vvork)/", "timestamp": "20141006184357", "url": "http://www.vvork.com/", "mem_rel": "memento", "memento_url": "http://webenact.rhizome.org/vvork/20141006184357/http://www.vvork.com/", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"}
{"urlkey": "com,vvork)/", "timestamp": "20131004231540", "url": "http://vvork.com/", "mem_rel": "last memento", "memento_url": "http://wayback.archive-it.org/all/20131004231540/http://vvork.com/", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}
"""

    assert(headers['Content-Type'] == 'application/x-ndjson')
    assert(''.join(res) == exp)
    assert(errs == {})

def test_handler_output_link():
    agg = GeventTimeoutAggregator(sources, timeout=5.0)
    handler = IndexHandler(agg)
    url = 'http://vvork.com/'
    headers, res, errs = handler(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait', output='link'))

    exp = """\
<http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/>; rel="memento"; datetime="Mon, 06 Oct 2014 18:43:57 GMT"; src="rhiz",
<http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/>; rel="memento"; datetime="Fri, 04 Oct 2013 23:15:40 GMT"; src="ait"
"""
    assert(headers['Content-Type'] == 'application/link')
    assert(''.join(res) == exp)
    assert(errs == {})


def test_handler_output_link_2():
    agg = GeventTimeoutAggregator(sources, timeout=5.0)
    handler = IndexHandler(agg)
    url = 'http://iana.org/'
    headers, res, errs = handler(dict(url=url, closest='20140126000000', limit=5, output='link'))

    exp = """\
<http://web.archive.org/web/20140126093743id_/http://iana.org/>; rel="memento"; datetime="Sun, 26 Jan 2014 09:37:43 GMT"; src="ia",
<file://iana.warc.gz:334:2258>; rel="memento"; datetime="Sun, 26 Jan 2014 20:06:24 GMT"; src="local",
<http://web.archive.org/web/20140123034755id_/http://iana.org/>; rel="memento"; datetime="Thu, 23 Jan 2014 03:47:55 GMT"; src="ia",
<http://web.archive.org/web/20140129175203id_/http://iana.org/>; rel="memento"; datetime="Wed, 29 Jan 2014 17:52:03 GMT"; src="ia",
<http://wayback.archive-it.org/all/20140107040552id_/http://iana.org/>; rel="memento"; datetime="Tue, 07 Jan 2014 04:05:52 GMT"; src="ait"
"""
    assert(headers['Content-Type'] == 'application/link')
    assert(''.join(res) == exp)

    exp_errs = {'bl': "NotFoundException('http://www.webarchive.org.uk/wayback/archive/http://iana.org/',)",
                'rhiz': "NotFoundException('http://webenact.rhizome.org/vvork/http://iana.org/',)"}

    assert(errs == exp_errs)



def test_handler_output_link_3():
    agg = GeventTimeoutAggregator(sources, timeout=5.0)
    handler = IndexHandler(agg)
    url = 'http://foo.bar.non-existent'
    headers, res, errs = handler(dict(url=url, closest='20140126000000', limit=5, output='link'))

    exp = ''

    assert(headers['Content-Type'] == 'application/link')
    assert(''.join(res) == exp)

    exp_errs = {'ait': "NotFoundException('http://wayback.archive-it.org/all/http://foo.bar.non-existent',)",
                'bl': "NotFoundException('http://www.webarchive.org.uk/wayback/archive/http://foo.bar.non-existent',)",
                'ia': "NotFoundException('http://web.archive.org/web/http://foo.bar.non-existent',)",
                'rhiz': "NotFoundException('http://webenact.rhizome.org/vvork/http://foo.bar.non-existent',)"}

    assert(errs == exp_errs)

def test_handler_output_text():
    agg = GeventTimeoutAggregator(sources, timeout=5.0)
    handler = IndexHandler(agg)
    url = 'http://vvork.com/'
    headers, res, errs = handler(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait', output='text'))

    exp = """\
com,vvork)/ 20141006184357 http://www.vvork.com/ memento http://webenact.rhizome.org/vvork/20141006184357/http://www.vvork.com/ http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/ rhiz
com,vvork)/ 20131004231540 http://vvork.com/ last memento http://wayback.archive-it.org/all/20131004231540/http://vvork.com/ http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/ ait
"""
    assert(headers['Content-Type'] == 'text/plain')
    assert(''.join(res) == exp)
    assert(errs == {})


def test_handler_list_sources():
    agg = GeventTimeoutAggregator(sources, timeout=5.0)
    handler = IndexHandler(agg)
    headers, res, errs = handler(dict(mode='list_sources'))

    assert(headers == {})
    assert(res == {'sources': {'bl': 'memento',
                               'ait': 'memento',
                               'ia': 'memento',
                               'rhiz': 'memento',
                               'local': 'file'}})
    assert(errs == {})


