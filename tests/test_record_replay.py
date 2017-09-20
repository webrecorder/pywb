from .base_config_test import BaseConfigTest, fmod, CollsDirMixin
from pywb.manager.manager import main as manager
from pywb.manager.autoindex import AutoIndexer
import os
import time


# ============================================================================
class TestRecordReplay(CollsDirMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestRecordReplay, cls).setup_class('config_test_record.yaml')
        cls.indexer = AutoIndexer(interval=0.25)
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

    def test_record_1(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test/record/mp_/http://httpbin.org/get?A=B', fmod_slash)
        assert '"A": "B"' in res.text

    def test_replay_1(self, fmod):
        time.sleep(0.5)

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test/mp_/http://httpbin.org/get?A=B', fmod_slash)
        assert '"A": "B"' in res.text

    def test_record_2(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test2/record/{0}http://httpbin.org/get?C=D', fmod_slash)
        assert '"C": "D"' in res.text

    def test_replay_2(self, fmod):
        time.sleep(0.5)

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test2/{0}http://httpbin.org/get?C=D', fmod_slash)
        assert '"C": "D"' in res.text

    def test_record_again_1(self, fmod):
        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test/record/{0}http://httpbin.org/get?C=D', fmod_slash)
        assert '"C": "D"' in res.text

    def test_replay_again_1(self, fmod):
        time.sleep(0.5)

        fmod_slash = fmod + '/' if fmod else ''
        res = self.get('/test/{0}http://httpbin.org/get?C=D', fmod_slash)
        assert '"C": "D"' in res.text

        # two warcs, for framed and non-framed capture
        assert len(os.listdir(os.path.join(self.root_dir, '_test_colls', 'test', 'archive'))) == 2

        assert len(os.listdir(os.path.join(self.root_dir, '_test_colls', 'test', 'indexes'))) == 1


