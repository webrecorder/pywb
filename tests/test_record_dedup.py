from .base_config_test import BaseConfigTest, CollsDirMixin, BaseTestClass
from pywb.manager.manager import main as manager
from pywb.warcserver.test.testutils import to_path, HttpBinLiveTests, FakeRedisTests

from fakeredis import FakeStrictRedis

from warcio import ArchiveIterator

import os
import time
import json

import pytest


# ============================================================================
class TestRecordDedup(HttpBinLiveTests, CollsDirMixin, BaseConfigTest, FakeRedisTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestRecordDedup, cls).setup_class('config_test_record_dedup.yaml', custom_config={'recorder': 'live'})
        cls.redis = FakeStrictRedis.from_url("redis://localhost/0")

    def test_init_coll(self):
        manager(['init', 'test-dedup'])
        assert os.path.isdir(os.path.join(self.root_dir, '_test_colls', 'test-dedup', 'archive'))

    def test_record_1(self):
        res = self.testapp.get('/test-dedup/record/mp_/http://httpbin.org/get?A=B', headers={"Referer": "http://httpbin.org/"})
        assert '"A": "B"' in res.text

        time.sleep(1.2)

        res = self.testapp.get('/test-dedup/record/mp_/http://httpbin.org/get?A=B', headers={"Referer": "http://httpbin.org/"})
        assert '"A": "B"' in res.text

    def test_single_redis_entry(self):
        res = self.redis.zrange("pywb:test-dedup:cdxj", 0, -1)
        assert len(res) == 1

    def test_single_warc_record(self):
        dir_name = os.path.join(self.root_dir, '_test_colls', 'test-dedup', 'archive')
        files = os.listdir(dir_name)
        assert len(files) == 1

        records = []

        with open(os.path.join(dir_name, files[0]), 'rb') as fh:
            for record in ArchiveIterator(fh):
                records.append(record.rec_type)

        # ensure only one response/request pair written
        assert records == ['response', 'request']

    def test_redis_pending_count(self):
        res = self.redis.get("pywb:test-dedup:pending")
        assert res == b'0'
