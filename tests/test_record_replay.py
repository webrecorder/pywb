from .base_config_test import BaseConfigTest, fmod, CollsDirMixin
from pywb.manager.manager import main as manager
from pywb.manager.autoindex import AutoIndexer
from pywb.warcserver.test.testutils import to_path, HttpBinLiveTests, TEST_WARC_PATH, TEST_CDX_PATH

from warcio import ArchiveIterator

import os
import time
import json
import sys

from mock import patch
import pytest


# ============================================================================
class TestRecordReplay(HttpBinLiveTests, CollsDirMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestRecordReplay, cls).setup_class('config_test_record.yaml')
        cls.indexer = AutoIndexer(interval=0.1)
        cls.indexer.start()

    @classmethod
    def teardown_class(cls):
        cls.indexer.stop()
        super(TestRecordReplay, cls).teardown_class()

    def test_init_coll(self):
        manager(['init', 'test'])
        assert os.path.isdir(os.path.join(self.root_dir, '_test_colls', 'test', 'archive'))

        manager(['init', 'test2'])
        assert os.path.isdir(os.path.join(self.root_dir, '_test_colls', 'test2', 'archive'))

    def test_record_1(self):
        res = self.testapp.get('/test/record/mp_/http://httpbin.org/get?A=B')
        assert '"A": "B"' in res.text

    def test_record_head(self):
        res = self.testapp.head('/test/record/mp_/http://httpbin.org/get?A=B')
        assert res.status_code == 200
        assert res.text == ''

    def test_replay_1(self, fmod):
        self.ensure_empty()

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test/{0}http://httpbin.org/get?A=B', fmod_slash)
        assert '"A": "B"' in res.text

    def test_replay_head(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''

        res = self.testapp.head('/test/{0}http://httpbin.org/get?A=B'.format(fmod_slash))
        assert res.status_code == 200
        assert res.text == ''

    def test_record_2(self):
        res = self.testapp.get('/test2/record/mp_/http://httpbin.org/get?C=D')
        assert '"C": "D"' in res.text

    def test_replay_2(self, fmod):
        self.ensure_empty()

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test2/{0}http://httpbin.org/get?C=D', fmod_slash)
        assert '"C": "D"' in res.text

    def test_record_again_1(self):
        res = self.testapp.get('/test/record/mp_/http://httpbin.org/get?C=D2')
        assert '"C": "D2"' in res.text

    def test_replay_again_1(self, fmod):
        self.ensure_empty()

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test/{0}http://httpbin.org/get?C=D2', fmod_slash)
        assert '"C": "D2"' in res.text

        assert len(os.listdir(os.path.join(self.root_dir, '_test_colls', 'test', 'archive'))) == 1

        assert len(os.listdir(os.path.join(self.root_dir, '_test_colls', 'test', 'indexes'))) == 1

    def ensure_empty(self):
        while not self.app.recorder.write_queue.empty():
            time.sleep(0.1)

        time.sleep(0.4)

    def test_replay_all_coll(self, fmod):
        self.ensure_empty()

        fmod_slash = fmod + '/' if fmod else ''

        res = self.get('/all/{0}http://httpbin.org/get?C=D', fmod_slash)
        assert '"C": "D"' in res.text

        res = self.get('/all/mp_/http://httpbin.org/get?A=B', fmod_slash)
        assert '"A": "B"' in res.text

    def test_cdx_all_coll(self):
        res = self.testapp.get('/all/cdx?url=http://httpbin.org/get*&output=json')

        cdxj_lines = [json.loads(line) for line in res.text.rstrip().split('\n')]

        assert len(cdxj_lines) == 4

        assert cdxj_lines[0]['url'] == 'http://httpbin.org/get?A=B'
        assert cdxj_lines[1]['url'] == 'http://httpbin.org/get?A=B'
        assert cdxj_lines[2]['url'] == 'http://httpbin.org/get?C=D'
        assert cdxj_lines[3]['url'] == 'http://httpbin.org/get?C=D2'

        assert cdxj_lines[0]['urlkey'] == 'org,httpbin)/get?__wb_method=head&a=b'
        assert cdxj_lines[1]['urlkey'] == 'org,httpbin)/get?a=b'
        assert cdxj_lines[2]['urlkey'] == 'org,httpbin)/get?c=d'
        assert cdxj_lines[3]['urlkey'] == 'org,httpbin)/get?c=d2'

        assert cdxj_lines[0]['source'] == to_path('test/indexes/autoindex.cdxj')
        assert cdxj_lines[1]['source'] == to_path('test/indexes/autoindex.cdxj')
        assert cdxj_lines[2]['source'] == to_path('test2/indexes/autoindex.cdxj')
        assert cdxj_lines[3]['source'] == to_path('test/indexes/autoindex.cdxj')

        assert cdxj_lines[0]['source-coll'] == 'test'
        assert cdxj_lines[1]['source-coll'] == 'test'
        assert cdxj_lines[2]['source-coll'] == 'test2'
        assert cdxj_lines[3]['source-coll'] == 'test'

        assert cdxj_lines[1]['filename'] == cdxj_lines[3]['filename']

    def test_timemap_all_coll(self):
        res = self.testapp.get('/all/timemap/link/http://httpbin.org/get?C=D')
        link_lines = res.text.rstrip().split('\n')
        assert len(link_lines) == 4

        assert to_path('collection="test2"') in link_lines[3]
        #assert to_path('collection="test"') in link_lines[4]

    def test_put_custom_record(self):
        payload = b'<html><body>This is custom data added directly. <a href="/test">Link</a></body></html>'
        res = self.testapp.put('/test2/record?url=https://example.com/custom/record', params=payload, content_type="text/html")

    def test_replay_custom_record(self, fmod):
        self.ensure_empty()

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test2/{0}https://example.com/custom/record', fmod_slash)
        assert res.content_type == 'text/html'
        assert 'This is custom data added directly. <a href="/test2/' in res.text


# ============================================================================
class TestRecordCustomConfig(HttpBinLiveTests, CollsDirMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        rec_custom = {'recorder': {'source_coll': 'live',
                                   'filename_template': 'pywb-rec-test-{timestamp}.warcgz'}}
        super(TestRecordCustomConfig, cls).setup_class('config_test_record.yaml', custom_config=rec_custom)

    def test_init_and_rec(self):
        manager(['init', 'test-new'])
        dir_name = os.path.join(self.root_dir, '_test_colls', 'test-new', 'archive')
        assert os.path.isdir(dir_name)

        res = self.testapp.get('/test-new/record/mp_/http://httpbin.org/get?A=B')
        assert '"A": "B"' in res.text

        names = os.listdir(dir_name)
        assert len(names) == 1
        assert names[0].startswith('pywb-rec-test-')
        assert names[0].endswith('.warcgz')

        TestRecordCustomConfig.warc_name = os.path.join(dir_name, names[0])

    @patch('pywb.rewrite.rewriteinputreq.has_brotli', False)
    def test_no_brotli(self):
        res = self.testapp.get('/test-new/record/mp_/http://httpbin.org/get?C=D',
                               headers={'Accept-Encoding': 'gzip, deflate, br'})
        assert '"C": "D"' in res.text

        with open(self.warc_name, 'rb') as fh:
            for record in ArchiveIterator(fh):
                last_record = record

        assert record.http_headers['Accept-Encoding'] == 'gzip, deflate'


# ============================================================================
@pytest.mark.skipif(sys.version_info >= (3,9) and sys.version_info < (3,10), reason='Skipping for 3.9')
class TestRecordFilter(HttpBinLiveTests, CollsDirMixin, BaseConfigTest):

    @classmethod
    def setup_class(cls):
        rec_custom = {'collections': {'fallback': {'sequence': [
                        {
                            'index_paths': os.path.join(TEST_CDX_PATH, 'example.cdxj'),
                            'archive_paths': TEST_WARC_PATH,
                            'name': 'example'
                        },{
                            'index':'$live',
                            'name': 'live'
                        }]}},
                        'recorder': {'source_coll': 'fallback',
                                     'source_filter': 'live',
                                     }
                     }
        super(TestRecordFilter, cls).setup_class('config_test_record.yaml', custom_config=rec_custom)
        manager(['init', 'test-new'])

    def test_skip_existing(self):
        dir_name = os.path.join(self.root_dir, '_test_colls', 'test-new', 'archive')
        assert os.path.isdir(dir_name)
        res = self.testapp.get('/fallback/cdx?url=http://example.com/?example=1')
        assert res.text != ''

        res = self.testapp.get('/test-new/record/mp_/http://example.com/?example=1')
        assert 'Example Domain' in res.text
        assert os.listdir(dir_name) == []

    def test_record_new(self):
        dir_name = os.path.join(self.root_dir, '_test_colls', 'test-new', 'archive')
        assert os.path.isdir(dir_name)
        res = self.testapp.get('/fallback/cdx?url=http://httpbin.org/get?A=B')
        assert res.text == ''

        res = self.testapp.get('/test-new/record/mp_/http://httpbin.org/get?A=B')
        assert res.json['args']['A'] == 'B'
        names = os.listdir(dir_name)
        assert len(names) == 1
        assert names[0].endswith('.warc.gz')



