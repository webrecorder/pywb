from gevent import monkey; monkey.patch_all()
from rezag.aggindexsource import SimpleAggregator, GeventTimeoutAggregator

from rezag.indexsource import FileIndexSource, RemoteIndexSource, MementoIndexSource
import json
import pytest

from rezag.handlers import IndexHandler


sources = {
    'local': FileIndexSource('testdata/iana.cdxj'),
    'ia': MementoIndexSource.from_timegate_url('http://web.archive.org/web/'),
    'ait': MementoIndexSource.from_timegate_url('http://wayback.archive-it.org/all/'),
    'bl': MementoIndexSource.from_timegate_url('http://www.webarchive.org.uk/wayback/archive/'),
    'rhiz': MementoIndexSource.from_timegate_url('http://webenact.rhizome.org/vvork/', path='*')
}

#@pytest.mark.parametrize("agg", aggs, ids=["simple", "gevent_timeout"])
def pytest_generate_tests(metafunc):
    metafunc.parametrize("agg", aggs, ids=["simple", "gevent_timeout"])


aggs = [SimpleAggregator(sources),
        GeventTimeoutAggregator(sources, timeout=5.0)
       ]


def json_list(cdxlist, fields=['timestamp', 'load_url', 'filename', 'source']):
    return list([json.loads(cdx.to_json(fields)) for cdx in cdxlist])


def test_mem_agg_index_1(agg):
    url = 'http://iana.org/'
    res = agg(dict(url=url, closest='20140126000000', limit=5))


    exp = [{"timestamp": "20140126093743", "load_url": "http://web.archive.org/web/20140126093743id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140126200624", "filename": "iana.warc.gz", "source": "local"},
           {"timestamp": "20140123034755", "load_url": "http://web.archive.org/web/20140123034755id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140129175203", "load_url": "http://web.archive.org/web/20140129175203id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140107040552", "load_url": "http://wayback.archive-it.org/all/20140107040552id_/http://iana.org/", "source": "ait"}
          ]

    assert(json_list(res) == exp)


def test_mem_agg_index_2(agg):
    url = 'http://example.com/'
    res = agg(dict(url=url, closest='20100512', limit=6))

    exp = [{"timestamp": "20100513010014", "load_url": "http://www.webarchive.org.uk/wayback/archive/20100513010014id_/http://example.com/", "source": "bl"},
            {"timestamp": "20100512204410", "load_url": "http://www.webarchive.org.uk/wayback/archive/20100512204410id_/http://example.com/", "source": "bl"},
            {"timestamp": "20100513052358", "load_url": "http://web.archive.org/web/20100513052358id_/http://example.com/", "source": "ia"},
            {"timestamp": "20100511201151", "load_url": "http://wayback.archive-it.org/all/20100511201151id_/http://example.com/", "source": "ait"},
            {"timestamp": "20100514231857", "load_url": "http://wayback.archive-it.org/all/20100514231857id_/http://example.com/", "source": "ait"},
            {"timestamp": "20100514231857", "load_url": "http://web.archive.org/web/20100514231857id_/http://example.com/", "source": "ia"}]

    assert(json_list(res) == exp)


def test_mem_agg_index_3(agg):
    url = 'http://vvork.com/'
    res = agg(dict(url=url, closest='20141001', limit=5))

    exp = [{"timestamp": "20141006184357", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"},
           {"timestamp": "20141018133107", "load_url": "http://web.archive.org/web/20141018133107id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20141020161243", "load_url": "http://web.archive.org/web/20141020161243id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20140806161228", "load_url": "http://web.archive.org/web/20140806161228id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20131004231540", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}]

    assert(json_list(res) == exp)


def test_mem_agg_index_4(agg):
    url = 'http://vvork.com/'
    res = agg(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait'))

    exp = [{"timestamp": "20141006184357", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"},
           {"timestamp": "20131004231540", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}]

    assert(json_list(res) == exp)


def test_handler_output_cdxj(agg):
    loader = IndexHandler(agg)
    url = 'http://vvork.com/'
    res = loader(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait'))

    exp = """\
com,vvork)/ 20141006184357 {"url": "http://www.vvork.com/", "mem_rel": "memento", "memento_url": "http://webenact.rhizome.org/vvork/20141006184357/http://www.vvork.com/", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"}
com,vvork)/ 20131004231540 {"url": "http://vvork.com/", "mem_rel": "last memento", "memento_url": "http://wayback.archive-it.org/all/20131004231540/http://vvork.com/", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}
"""

    assert(''.join(res) == exp)


def test_handler_output_json(agg):
    loader = IndexHandler(agg)
    url = 'http://vvork.com/'
    res = loader(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait', output='json'))

    exp = """\
{"urlkey": "com,vvork)/", "timestamp": "20141006184357", "url": "http://www.vvork.com/", "mem_rel": "memento", "memento_url": "http://webenact.rhizome.org/vvork/20141006184357/http://www.vvork.com/", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"}
{"urlkey": "com,vvork)/", "timestamp": "20131004231540", "url": "http://vvork.com/", "mem_rel": "last memento", "memento_url": "http://wayback.archive-it.org/all/20131004231540/http://vvork.com/", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}
"""

    assert(''.join(res) == exp)


def test_handler_output_link(agg):
    loader = IndexHandler(agg)
    url = 'http://vvork.com/'
    res = loader(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait', output='link'))

    exp = """\
<http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/>; rel="memento"; datetime="Mon, 06 Oct 2014 18:43:57 GMT"; src="rhiz",
<http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/>; rel="memento"; datetime="Fri, 04 Oct 2013 23:15:40 GMT"; src="ait"\
"""
    assert(''.join(res) == exp)


def test_handler_output_text(agg):
    loader = IndexHandler(agg)
    url = 'http://vvork.com/'
    res = loader(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait', output='text'))

    exp = """\
com,vvork)/ 20141006184357 http://www.vvork.com/ memento http://webenact.rhizome.org/vvork/20141006184357/http://www.vvork.com/ http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/ rhiz
com,vvork)/ 20131004231540 http://vvork.com/ last memento http://wayback.archive-it.org/all/20131004231540/http://vvork.com/ http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/ ait
"""
    assert(''.join(res) == exp)


def test_handler_list_sources(agg):
    loader = IndexHandler(agg)
    res = loader(dict(mode='sources'))

    assert(res == {'sources': {'bl': 'memento',
                               'ait': 'memento',
                               'ia': 'memento',
                               'rhiz': 'memento',
                               'local': 'file'}})


