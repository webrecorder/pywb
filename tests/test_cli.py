import os
from mock import patch

import pytest

from pywb.apps.cli import wayback
from .base_config_test import CollsDirMixin, BaseTestClass


# ============================================================================
def _run_patch(self):
    return self


@patch('pywb.apps.cli.ReplayCli.run', _run_patch)
class TestProxyCLIConfig(CollsDirMixin, BaseTestClass):
    def test_proxy_cli(self):
        res = wayback(['--proxy', 'test'])
        exp = {'ca_file_cache': os.path.join('proxy-certs', 'pywb-ca.pem'),
               'ca_name': 'pywb HTTPS Proxy CA',
               'coll': 'test',
               'recording': False,
               'use_wombat': False,
               'use_auto_fetch_worker': False}
        assert res.extra_config['proxy'] == exp

    def test_proxy_cli_rec(self):
        res = wayback(['--proxy', 'test', '--proxy-record'])
        assert res.extra_config['proxy']['recording'] == True
        assert res.extra_config['collections']['live'] == {'index': '$live'}

    def test_proxy_cli_err_coll(self):
        with pytest.raises(Exception):
            res = wayback(['--proxy', 'test/foo'])

    def test_all_cli(self):
        res = wayback(['--all-coll', 'all'])
        assert res.extra_config['collections']['all'] == '$all'

    def test_live_all_cli(self):
        res = wayback(['--all-coll', 'all', '--live'])
        assert res.extra_config['collections'] == {'live': {'index': '$live'},
                                                   'all': '$all'}

