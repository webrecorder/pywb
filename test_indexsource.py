from indexsource import FileIndexSource, RemoteIndexSource, MementoIndexSource, RedisIndexSource
from indexsource import LiveIndexSource

from pywb.utils.timeutils import timestamp_now

import redis
import pytest

def key_ts_res(cdxlist, extra='filename'):
    return '\n'.join([cdx['urlkey'] + ' ' + cdx['timestamp'] + ' ' + cdx[extra] for cdx in cdxlist])

def setup_module():
    r = redis.StrictRedis(db=2)
    r.delete('test:rediscdx')
    with open('sample.cdxj', 'rb') as fh:
        for line in fh:
            r.zadd('test:rediscdx', 0, line.rstrip())


def teardown_module():
    r = redis.StrictRedis(db=2)
    r.delete('test:rediscdx')


local_sources = [
    FileIndexSource('sample.cdxj'),
    RedisIndexSource('redis://localhost:6379/2/test:rediscdx')
]


remote_sources = [
    RemoteIndexSource('http://webenact.rhizome.org/all-cdx',
                      'http://webenact.rhizome.org/all/{timestamp}id_/{url}'),

    MementoIndexSource('http://webenact.rhizome.org/all/',
                       'http://webenact.rhizome.org/all/timemap/*/',
                       'http://webenact.rhizome.org/all/{timestamp}id_/{url}')
]



# Url Match -- Local Loaders
# ============================================================================
@pytest.mark.parametrize("source", local_sources, ids=["file", "redis"])
def test_local_cdxj_loader(source):
    url = 'http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf'
    res = source(dict(url=url, limit=3))

    expected = """\
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200826 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200912 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200930 iana.warc.gz"""

    assert(key_ts_res(res) == expected)


# Closest -- Local Loaders
# ============================================================================
@pytest.mark.parametrize("source", local_sources, ids=["file", "redis"])
def test_local_closest_loader(source):
    url = 'http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf'
    res = source(dict(url=url,
                  closest='20140126200930',
                  limit=3))

    expected = """\
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200930 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200912 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200826 iana.warc.gz"""

    assert(key_ts_res(res) == expected)


# Prefix -- Local Loaders
# ============================================================================
@pytest.mark.parametrize("source", local_sources, ids=["file", "redis"])
def test_file_prefix_loader(source):
    res = source(dict(url='http://iana.org/domains/root/*'))

    expected = """\
org,iana)/domains/root/db 20140126200927 iana.warc.gz
org,iana)/domains/root/db 20140126200928 iana.warc.gz
org,iana)/domains/root/servers 20140126201227 iana.warc.gz"""

    assert(key_ts_res(res) == expected)


# Url Match -- Remote Loaders
# ============================================================================
@pytest.mark.parametrize("source", remote_sources, ids=["remote_cdx", "memento"])
def test_remote_loader(source):
    url = 'http://instagram.com/amaliaulman'
    res = source(dict(url=url))

    expected = """\
com,instagram)/amaliaulman 20141014150552 http://webenact.rhizome.org/all/20141014150552id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014155217 http://webenact.rhizome.org/all/20141014155217id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014162333 http://webenact.rhizome.org/all/20141014162333id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014171636 http://webenact.rhizome.org/all/20141014171636id_/http://instagram.com/amaliaulman"""

    assert(key_ts_res(res, 'load_url') == expected)


# Url Match -- Remote Loaders
# ============================================================================
@pytest.mark.parametrize("source", remote_sources, ids=["remote_cdx", "memento"])
def test_remote_closest_loader(source):
    url = 'http://instagram.com/amaliaulman'
    res = source(dict(url=url, closest='20141014162332', limit=1))

    expected = """\
com,instagram)/amaliaulman 20141014162333 http://webenact.rhizome.org/all/20141014162333id_/http://instagram.com/amaliaulman"""

    assert(key_ts_res(res, 'load_url') == expected)


# Url Match -- Memento
# ============================================================================
@pytest.mark.parametrize("source", remote_sources, ids=["remote_cdx", "memento"])
def test_remote_closest_loader(source):
    url = 'http://instagram.com/amaliaulman'
    res = source(dict(url=url, closest='20141014162332', limit=1))

    expected = """\
com,instagram)/amaliaulman 20141014162333 http://webenact.rhizome.org/all/20141014162333id_/http://instagram.com/amaliaulman"""

    assert(key_ts_res(res, 'load_url') == expected)

# Live Index -- No Load!
# ============================================================================
def test_live():
    url = 'http://example.com/'
    source = LiveIndexSource()
    res = source(dict(url=url))

    expected = 'com,example)/ {0} http://example.com/'.format(timestamp_now())

    assert(key_ts_res(res, 'load_url') == expected)




# Errors -- Not Found All
# ============================================================================
@pytest.mark.parametrize("source", local_sources + remote_sources, ids=["file", "redis", "remote_cdx", "memento"])
def test_all_not_found(source):
    url = 'http://x-not-found-x.notfound/'
    res = source(dict(url=url, limit=3))

    expected = ''
    assert(key_ts_res(res) == expected)



# ============================================================================
def test_another_remote_not_found():
    source = MementoIndexSource.from_timegate_url('http://www.webarchive.org.uk/wayback/archive/')
    url = 'http://x-not-found-x.notfound/'
    res = source(dict(url=url, limit=3))


    expected = ''
    assert(key_ts_res(res) == expected)


