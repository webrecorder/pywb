from pywb.warcserver.index.indexsource import FileIndexSource, RemoteIndexSource, MementoIndexSource, RedisIndexSource
from pywb.warcserver.index.indexsource import LiveIndexSource, WBMementoIndexSource, S3IndexSource

from pywb.warcserver.index.aggregator import SimpleAggregator

from warcio.timeutils import timestamp_now

from pywb.warcserver.test.testutils import key_ts_res, TEST_CDX_PATH, FakeRedisTests, BaseTestClass

from pywb.recorder.s3uploader import s3_upload_file

import pytest
import os
import pathlib

import boto3


local_sources = ['file', 'redis']
remote_sources = ['remote_cdx', 'memento']
all_sources = local_sources + remote_sources


# ============================================================================
class TestIndexSources(FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestIndexSources, cls).setup_class()
        cls.add_cdx_to_redis(TEST_CDX_PATH + 'iana.cdxj', 'test:rediscdx')

        cls.all_sources = {
            'file': FileIndexSource(TEST_CDX_PATH + 'iana.cdxj'),
            'redis': RedisIndexSource('redis://localhost:6379/2/test:rediscdx'),
            'remote_cdx': RemoteIndexSource('https://webenact.rhizome.org/all/cdx?url={url}',
                              'https://webenact.rhizome.org/all/{timestamp}id_/{url}'),

            'memento': MementoIndexSource('https://webenact.rhizome.org/all/{url}',
                               'https://webenact.rhizome.org/all/timemap/link/{url}',
                               'https://webenact.rhizome.org/all/{timestamp}id_/{url}'),
        }

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
com,instagram)/amaliaulman 20141014150552 https://webenact.rhizome.org/all/20141014150552id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014152101 https://webenact.rhizome.org/all/20141014152101id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014155217 https://webenact.rhizome.org/all/20141014155217id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014160238 https://webenact.rhizome.org/all/20141014160238id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014162333 https://webenact.rhizome.org/all/20141014162333id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014163116 https://webenact.rhizome.org/all/20141014163116id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014171636 https://webenact.rhizome.org/all/20141014171636id_/http://instagram.com/amaliaulman
com,instagram)/amaliaulman 20141014171954 https://webenact.rhizome.org/all/20141014171954id_/http://instagram.com/amaliaulman"""
        assert(key_ts_res(res, 'load_url') == expected)
        assert(errs == {})

    # Url Match -- Remote Loaders
    def test_remote_loader_with_prefix(self):
        url = 'http://instagram.com/amaliaulman?__=1234234234'
        remote_source = self.all_sources['remote_cdx']
        res, errs = self.query_single_source(remote_source, dict(url=url, closest='20141014162332', limit=1, allowFuzzy='0'))

        expected = """\
com,instagram)/amaliaulman 20141014162333 https://webenact.rhizome.org/all/20141014162333id_/http://instagram.com/amaliaulman"""

        assert(key_ts_res(res, 'load_url') == expected)
        assert(errs == {})

    # Url Match -- Remote Loaders Closest
    def test_remote_closest_loader(self, remote_source):
        url = 'http://instagram.com/amaliaulman'
        res, errs = self.query_single_source(remote_source, dict(url=url, closest='20141014162332', limit=1))

        expected = """\
com,instagram)/amaliaulman 20141014162333 https://webenact.rhizome.org/all/20141014162333id_/http://instagram.com/amaliaulman"""

        assert(key_ts_res(res, 'load_url') == expected)
        assert(errs == {})

    # Url Match -- Wb Memento
    def test_remote_closest_wb_memento_loader(self):
        replay = 'https://webenact.rhizome.org/all/{timestamp}id_/{url}'
        source = WBMementoIndexSource(replay, '', replay)

        url = 'http://instagram.com/amaliaulman'
        res, errs = self.query_single_source(source, dict(url=url, closest='20141014162332', limit=1))

        expected = """\
com,instagram)/amaliaulman 20141014162333 https://webenact.rhizome.org/all/20141014162333id_/http://instagram.com/amaliaulman"""

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
        source = MementoIndexSource.from_timegate_url('https://webenact.rhizome.org/all/')
        url = 'http://x-not-found-x.notfound/'
        res, errs = self.query_single_source(source, dict(url=url, limit=3))


        expected = ''
        assert(key_ts_res(res) == expected)
        assert(errs['source'] == "NotFoundException('https://webenact.rhizome.org/all/timemap/link/http://x-not-found-x.notfound/',)")

    def test_file_not_found(self):
        source = FileIndexSource('testdata/not-found-x')
        url = 'http://x-not-found-x.notfound/'
        res, errs = self.query_single_source(source, dict(url=url, limit=3))

        expected = ''
        assert(key_ts_res(res) == expected)
        assert(errs['source'] == "NotFoundException('testdata/not-found-x',)"), errs

    def test_ait_filters(self):
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


    def test_s3_index(self):
        test_bucket = os.environ.get('AWS_S3_BUCKET')
        path = str(pathlib.Path(__file__).parent.absolute())
        idx_path = path + '/data/index.cdxj'
        obj_name = 'index.cdxj'

        s3_upload_file(idx_path, test_bucket, obj_name)
        idx = S3IndexSource(f's3://{test_bucket}/{obj_name}')

        url = 'https://www.thedatashed.co.uk'
        res, errs = self.query_single_source(idx, dict(url=url, limit=3))

        expected = """\
uk,co,thedatashed)/ 20201111163836 rec-20201111163836162255-e568593d94c8.warc.gz"""
        assert(key_ts_res(res) == expected)
        assert(errs == {})
        
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(test_bucket)
        s3.Object(test_bucket, obj_name).delete()