from .base_config_test import BaseConfigTest, fmod, CollsDirMixin
from pywb.manager.manager import main as manager
from pywb.manager.autoindex import AutoIndexer
from pywb.warcserver.test.testutils import to_path

import os
import time
import json


# ============================================================================
class TestRecordReplay(CollsDirMixin, BaseConfigTest):
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

    def test_replay_1(self, fmod):
        self.ensure_empty()

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test/{0}http://httpbin.org/get?A=B', fmod_slash)
        assert '"A": "B"' in res.text

    def test_record_2(self):
        res = self.testapp.get('/test2/record/mp_/http://httpbin.org/get?C=D')
        assert '"C": "D"' in res.text

    def test_replay_2(self, fmod):
        self.ensure_empty()

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test2/{0}http://httpbin.org/get?C=D', fmod_slash)
        assert '"C": "D"' in res.text

    def test_record_again_1(self):
        res = self.testapp.get('/test/record/mp_/http://httpbin.org/get?C=D')
        assert '"C": "D"' in res.text

    def test_replay_again_1(self, fmod):
        self.ensure_empty()

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test/{0}http://httpbin.org/get?C=D', fmod_slash)
        assert '"C": "D"' in res.text

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

        assert len(cdxj_lines) == 3

        assert cdxj_lines[0]['url'] == 'http://httpbin.org/get?A=B'
        assert cdxj_lines[1]['url'] == 'http://httpbin.org/get?C=D'
        assert cdxj_lines[2]['url'] == 'http://httpbin.org/get?C=D'

        assert cdxj_lines[0]['source'] == to_path('_test_colls:test/indexes/autoindex.cdxj')
        assert cdxj_lines[1]['source'] == to_path('_test_colls:test2/indexes/autoindex.cdxj')
        assert cdxj_lines[2]['source'] == to_path('_test_colls:test/indexes/autoindex.cdxj')

        assert cdxj_lines[0]['filename'] == cdxj_lines[2]['filename']

