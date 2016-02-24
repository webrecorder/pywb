from gevent import monkey; monkey.patch_all()
from aggindexsource import AggIndexSource

from indexsource import FileIndexSource, RemoteIndexSource, MementoIndexSource
import json


sources = {
    'local': FileIndexSource('sample.cdxj'),
    'ia': MementoIndexSource.from_timegate_url('http://web.archive.org/web/'),
    'ait': MementoIndexSource.from_timegate_url('http://wayback.archive-it.org/all/'),
    'bl': MementoIndexSource.from_timegate_url('http://www.webarchive.org.uk/wayback/archive/'),
    'rhiz': MementoIndexSource.from_timegate_url('http://webenact.rhizome.org/vvork/', path='*')
}

source = AggIndexSource(sources, timeout=5.0)

def select_json(cdxlist, fields=['timestamp', 'load_url', 'filename', 'source']):
    return list([json.loads(cdx.to_json(fields)) for cdx in cdxlist])


def test_agg_index_1():
    url = 'http://iana.org/'
    res = source(dict(url=url, closest='20140126000000', limit=5))


    exp = [{"timestamp": "20140126093743", "load_url": "http://web.archive.org/web/20140126093743id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140126200624", "filename": "iana.warc.gz", "source": "local"},
           {"timestamp": "20140123034755", "load_url": "http://web.archive.org/web/20140123034755id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140129175203", "load_url": "http://web.archive.org/web/20140129175203id_/http://iana.org/", "source": "ia"},
           {"timestamp": "20140107040552", "load_url": "http://wayback.archive-it.org/all/20140107040552id_/http://iana.org/", "source": "ait"}
          ]

    assert(select_json(res) == exp)


def test_agg_index_2():
    url = 'http://example.com/'
    res = source(dict(url=url, closest='20100512', limit=6))

    exp = [{"timestamp": "20100513010014", "load_url": "http://www.webarchive.org.uk/wayback/archive/20100513010014id_/http://example.com/", "source": "bl"},
            {"timestamp": "20100512204410", "load_url": "http://www.webarchive.org.uk/wayback/archive/20100512204410id_/http://example.com/", "source": "bl"},
            {"timestamp": "20100513052358", "load_url": "http://web.archive.org/web/20100513052358id_/http://example.com/", "source": "ia"},
            {"timestamp": "20100511201151", "load_url": "http://wayback.archive-it.org/all/20100511201151id_/http://example.com/", "source": "ait"},
            {"timestamp": "20100514231857", "load_url": "http://wayback.archive-it.org/all/20100514231857id_/http://example.com/", "source": "ait"},
            {"timestamp": "20100514231857", "load_url": "http://web.archive.org/web/20100514231857id_/http://example.com/", "source": "ia"}]

    assert(select_json(res) == exp)


def test_agg_index_3():
    url = 'http://vvork.com/'
    res = source(dict(url=url, closest='20141001', limit=5))

    exp = [{"timestamp": "20141006184357", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"},
           {"timestamp": "20141018133107", "load_url": "http://web.archive.org/web/20141018133107id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20141020161243", "load_url": "http://web.archive.org/web/20141020161243id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20140806161228", "load_url": "http://web.archive.org/web/20140806161228id_/http://vvork.com/", "source": "ia"},
           {"timestamp": "20131004231540", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}]

    assert(select_json(res) == exp)


def test_agg_index_4():
    url = 'http://vvork.com/'
    res = source(dict(url=url, closest='20141001', limit=2, sources='rhiz,ait'))

    exp = [{"timestamp": "20141006184357", "load_url": "http://webenact.rhizome.org/vvork/20141006184357id_/http://www.vvork.com/", "source": "rhiz"},
           {"timestamp": "20131004231540", "load_url": "http://wayback.archive-it.org/all/20131004231540id_/http://vvork.com/", "source": "ait"}]

    assert(select_json(res) == exp)


