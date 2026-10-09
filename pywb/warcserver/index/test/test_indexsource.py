from gevent import monkey; monkey.patch_all()
from pywb.warcserver.index.indexsource import FileIndexSource, RemoteIndexSource, MementoIndexSource, RedisIndexSource
from pywb.warcserver.index.indexsource import LiveIndexSource, WBMementoIndexSource

from pywb.warcserver.index.aggregator import SimpleAggregator

from warcio.timeutils import timestamp_now

from pywb.warcserver.test.testutils import key_ts_res, TEST_CDX_PATH, FakeRedisTests, BaseTestClass
from pywb.utils.canonicalize import canonicalize
from pywb.utils.geventserver import GeventServer

from six.moves.urllib.parse import parse_qs

import pytest
import os


local_sources = ['file', 'redis']
remote_sources = ['remote_cdx', 'memento']
all_sources = local_sources + remote_sources


# responses of the excellences-and-perfections collection on webarchives.rhizome.org (a pywb instance)
RHIZOME_CDXJ = b'''\
com,instagram)/amaliaulman 20141014150552 {"url": "http://instagram.com/amaliaulman", "mime": "text/html", "status": "200", "digest": "TOSGWY34O455PVOCOPUQ2JMSNAYMHLIU", "length": "13665", "offset": "355", "filename": "excellences-and-perfections_desktop-p1.warc.gz"}
com,instagram)/amaliaulman 20141014155217 {"url": "http://instagram.com/amaliaulman", "mime": "text/html", "status": "200", "digest": "7ELWPVPC6GNKWJ446L52QOXME55TSILE", "length": "13784", "offset": "357", "filename": "excellences-and-perfections_desktop-p2.warc.gz"}
com,instagram)/amaliaulman 20141014162333 {"url": "http://instagram.com/amaliaulman", "mime": "text/html", "status": "200", "digest": "33AZFENGA6QJ66KCRIDRMH65DWW2DQEL", "length": "13658", "offset": "355", "filename": "excellences-and-perfections_desktop-p3.warc.gz"}
com,instagram)/amaliaulman 20141014171636 {"url": "http://instagram.com/amaliaulman", "mime": "text/html", "status": "200", "digest": "H523Y3PFUUJ4CJJYXRFH7NOTVZL6XMHH", "length": "13451", "offset": "359", "filename": "excellences-and-perfections_desktop-fin.warc.gz"}
'''

# extra prefix matches returned for a url that has no exact match
RHIZOME_CDXJ_FUZZY = RHIZOME_CDXJ + b'''\
com,instagram)/amaliaulman/media?max_id=704906059232664579_202871366 20141014150654 {"url": "http://instagram.com/amaliaulman/media?max_id=704906059232664579_202871366", "mime": "application/json", "status": "200", "digest": "6NJ6VN4PF6VRUMLYOD46RH4W2NOAHF3N", "length": "8111", "offset": "7478560", "filename": "excellences-and-perfections_desktop-p1.warc.gz", "is_fuzzy": "1"}
com,instagram)/amaliaulman/media?max_id=799785922954878482_202871366 20141014171705 {"url": "http://instagram.com/amaliaulman/media?max_id=799785922954878482_202871366", "mime": "application/json", "status": "200", "digest": "5E47UOQZQDEGYIPCAY7CVEZKUFNU3VZ5", "length": "11972", "offset": "1897836", "filename": "excellences-and-perfections_desktop-fin.warc.gz", "is_fuzzy": "1"}
'''

RHIZOME_MEMENTO = '<{prefix}{timestamp}mp_/http://instagram.com/amaliaulman>; rel="memento"; datetime="{datetime}"'

RHIZOME_DATETIMES = [('20141014150552', 'Tue, 14 Oct 2014 15:05:52 GMT'),
                     ('20141014155217', 'Tue, 14 Oct 2014 15:52:17 GMT'),
                     ('20141014162333', 'Tue, 14 Oct 2014 16:23:33 GMT'),
                     ('20141014171636', 'Tue, 14 Oct 2014 17:16:36 GMT')]


def rhizome_app(environ, start_response):
    # local stand-in for webarchives.rhizome.org: cdx api, timemap, timegate and id_ replay
    # for http://instagram.com/amaliaulman, closest capture 20141014162333
    prefix = 'http://' + environ['HTTP_HOST'] + '/excellences-and-perfections/'
    path = environ['PATH_INFO']
    url = 'http://instagram.com/amaliaulman'

    if path == '/excellences-and-perfections/cdx':
        key = canonicalize(parse_qs(environ['QUERY_STRING'])['url'][0])
        if key == 'com,instagram)/amaliaulman':
            body = RHIZOME_CDXJ
        elif key.startswith('com,instagram)/amaliaulman'):
            body = RHIZOME_CDXJ_FUZZY
        else:
            body = b''

        start_response('200 OK', [('Content-Type', 'text/x-cdxj')])
        return [body]

    links = ['<{0}>; rel="original"'.format(url),
             '<{0}{1}>; rel="timegate"'.format(prefix, url),
             '<{0}timemap/link/{1}>; rel="timemap"; type="application/link-format"'.format(prefix, url)]

    if path == '/excellences-and-perfections/timemap/link/' + url:
        links += [RHIZOME_MEMENTO.format(prefix=prefix, timestamp=ts, datetime=dt)
                  for ts, dt in RHIZOME_DATETIMES]
        start_response('200 OK', [('Content-Type', 'application/link-format')])
        return [',\n'.join(links).encode('utf-8')]

    links.append(RHIZOME_MEMENTO.format(prefix=prefix, timestamp='20141014162333',
                                        datetime='Tue, 14 Oct 2014 16:23:33 GMT'))
    headers = [('Content-Type', 'text/html'), ('Link', ', '.join(links))]

    # timegate
    if path == '/excellences-and-perfections/' + url:
        start_response('200 OK', headers)
        return [b'']

    # replay, as wayback redirects to the closest capture
    if path.startswith('/excellences-and-perfections/2014') and path.endswith('id_/' + url):
        headers += [('Memento-Datetime', 'Tue, 14 Oct 2014 16:23:33 GMT'),
                    ('Content-Location', prefix + '20141014162333id_/' + url)]
        start_response('200 OK', headers)
        return [b'']

    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'Not Found']


# ============================================================================
class TestIndexSources(FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestIndexSources, cls).setup_class()
        cls.add_cdx_to_redis(TEST_CDX_PATH + 'iana.cdxj', 'test:rediscdx')

        cls.rhizome_server = GeventServer(rhizome_app)
        cls.rhizome_url = 'http://localhost:{0}/'.format(cls.rhizome_server.port)
        rhizome_coll = cls.rhizome_url + 'excellences-and-perfections/'

        cls.all_sources = {
            'file': FileIndexSource(TEST_CDX_PATH + 'iana.cdxj'),
            'redis': RedisIndexSource('redis://localhost:6379/2/test:rediscdx'),
            'remote_cdx': RemoteIndexSource(rhizome_coll + 'cdx?url={url}',
                              rhizome_coll + '{timestamp}id_/{url}'),

            'memento': MementoIndexSource(rhizome_coll + '{url}',
                               rhizome_coll + 'timemap/link/{url}',
                               rhizome_coll + '{timestamp}id_/{url}')
        }

    @classmethod
    def teardown_class(cls):
        cls.rhizome_server.stop()
        super(TestIndexSources, cls).teardown_class()

    @pytest.fixture(params=local_sources)
    def local_source(self, request):
        return self.all_sources[request.param]

    @pytest.fixture(params=remote_sources)
    def remote_source(self, request):
        return self.all_sources[request.param]

    @pytest.fixture(params=all_sources)
    def all_source(self, request):
        return self.all_sources[request.param]

    @staticmethod
    def query_single_source(source, params):
        string = str(source)
        return SimpleAggregator({'source': source})(params)

    # Url Match -- Local Loaders
    def test_local_cdxj_loader(self, local_source):
        url = 'http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf'
        res, errs = self.query_single_source(local_source, dict(url=url, limit=3))

        expected = """\
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200826 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200912 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200930 iana.warc.gz"""

        assert(key_ts_res(res) == expected)
        assert(errs == {})


    # Closest -- Local Loaders
    def test_local_closest_loader(self, local_source):
        url = 'http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf'
        res, errs = self.query_single_source(local_source, dict(url=url,
                      closest='20140126200930',
                      limit=3))

        expected = """\
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200930 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200912 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200826 iana.warc.gz"""

        assert(key_ts_res(res) == expected)
        assert(errs == {})


    # Prefix -- Local Loaders
    def test_file_prefix_loader(self, local_source):
        res, errs = self.query_single_source(local_source, dict(url='http://iana.org/domains/root/*'))

        expected = """\
org,iana)/domains/root/db 20140126200927 iana.warc.gz
org,iana)/domains/root/db 20140126200928 iana.warc.gz
org,iana)/domains/root/servers 20140126201227 iana.warc.gz"""

        assert(key_ts_res(res) == expected)
        assert(errs == {})

    # Url Match -- Remote Loaders
    def test_remote_loader(self, remote_source):
        url = 'http://instagram.com/amaliaulman'
        res, errs = self.query_single_source(remote_source, dict(url=url))

        expected = """\
com,instagram)/amaliaulman 20141014150552 {0}excellences-and-perfections/20141014150552id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014155217 {0}excellences-and-perfections/20141014155217id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014162333 {0}excellences-and-perfections/20141014162333id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014171636 {0}excellences-and-perfections/20141014171636id_/http://instagram.com/amaliaulman""".format(self.rhizome_url)
        assert(key_ts_res(res, 'load_url') == expected)
        assert(errs == {})

    # Url Match -- Remote Loaders
    def test_remote_loader_with_prefix(self):
        url = 'http://instagram.com/amaliaulman?__=1234234234'
        remote_source = self.all_sources['remote_cdx']
        res, errs = self.query_single_source(remote_source, dict(url=url, closest='20141014162332', limit=1, allowFuzzy='0'))

        expected = """\
com,instagram)/amaliaulman 20141014162333 {0}excellences-and-perfections/20141014162333id_/http://instagram.com/amaliaulman""".format(self.rhizome_url)

        assert(key_ts_res(res, 'load_url') == expected)
        assert(errs == {})

    # Url Match -- Remote Loaders Closest
    def test_remote_closest_loader(self, remote_source):
        url = 'http://instagram.com/amaliaulman'
        res, errs = self.query_single_source(remote_source, dict(url=url, closest='20141014162332', limit=1))

        expected = """\
com,instagram)/amaliaulman 20141014162333 {0}excellences-and-perfections/20141014162333id_/http://instagram.com/amaliaulman""".format(self.rhizome_url)

        assert(key_ts_res(res, 'load_url') == expected)
        assert(errs == {})

    # Url Match -- Wb Memento
    def test_remote_closest_wb_memento_loader(self):
        replay = self.rhizome_url + 'excellences-and-perfections/{timestamp}id_/{url}'
        source = WBMementoIndexSource(replay, '', replay)

        url = 'http://instagram.com/amaliaulman'
        res, errs = self.query_single_source(source, dict(url=url, closest='20141014162332', limit=1))

        expected = """\
com,instagram)/amaliaulman 20141014162333 {0}excellences-and-perfections/20141014162333id_/http://instagram.com/amaliaulman""".format(self.rhizome_url)

        assert(key_ts_res(res, 'load_url') == expected)
        assert(errs == {})

    # Live Index -- No Load!
    def test_live(self):
        url = 'http://example.com/'
        source = LiveIndexSource()
        res, errs = self.query_single_source(source, dict(url=url))

        expected = 'com,example)/ {0} http://example.com/'.format(timestamp_now())

        assert(key_ts_res(res, 'load_url') == expected)
        assert(errs == {})

    # Errors -- Not Found All
    def test_all_not_found(self, all_source):
        url = 'http://x-not-found-x.notfound/'
        res, errs = self.query_single_source(all_source, dict(url=url, limit=3))

        expected = ''
        assert(key_ts_res(res) == expected)
        if all_source == self.all_sources['memento']:
            assert('x-not-found-x.notfound/' in errs['source'])
        else:
            assert(errs == {})

    def test_another_remote_not_found(self):
        source = MementoIndexSource.from_timegate_url(self.rhizome_url + 'all/')
        url = 'http://x-not-found-x.notfound/'
        res, errs = self.query_single_source(source, dict(url=url, limit=3))


        expected = ''
        assert(key_ts_res(res) == expected)
        assert(errs['source'] == "NotFoundException('{0}all/timemap/link/http://x-not-found-x.notfound/',)".format(self.rhizome_url))

    def test_file_not_found(self):
        source = FileIndexSource('testdata/not-found-x')
        url = 'http://x-not-found-x.notfound/'
        res, errs = self.query_single_source(source, dict(url=url, limit=3))

        expected = ''
        assert(key_ts_res(res) == expected)
        assert(errs['source'] == "NotFoundException('testdata/not-found-x',)"), errs

    @pytest.mark.live
    def test_ait_filters(self):
        pytest.skip("ait issue, may not work anymore")

        ait_source = RemoteIndexSource('http://wayback.archive-it.org/cdx/search/cdx?url={url}&filter=filename:ARCHIVEIT-({colls})-.*',
                                       'http://wayback.archive-it.org/all/{timestamp}id_/{url}')

        cdxlist, errs = self.query_single_source(ait_source, {'url': 'http://iana.org/', 'param.source.colls': '5610|933'})
        filenames = [cdx['filename'] for cdx in cdxlist]

        prefix = ('ARCHIVEIT-5610-', 'ARCHIVEIT-933-')

        assert(all([x.startswith(prefix) for x in filenames]))


        cdxlist, errs = self.query_single_source(ait_source, {'url': 'http://iana.org/', 'param.source.colls': '1883|366|905'})
        filenames = [cdx['filename'] for cdx in cdxlist]

        prefix = ('ARCHIVEIT-1883-', 'ARCHIVEIT-366-', 'ARCHIVEIT-905-')

        assert(all([x.startswith(prefix) for x in filenames]))

