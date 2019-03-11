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
               'enable_wombat': False,
               'default_timestamp': None
              }
        assert res.extra_config['proxy'] == exp

    def test_proxy_cli_ts_iso_date(self):
        res = wayback(['--proxy', 'test', '--proxy-default-timestamp', '2014-01-03 00:01:02'])
        assert res.application.proxy_default_timestamp == '20140103000102'

    def test_proxy_cli_ts(self):
        res = wayback(['--proxy', 'test', '--proxy-default-timestamp', '20140103000102'])
        assert res.application.proxy_default_timestamp == '20140103000102'

    def test_proxy_cli_ts_err_invalid_ts(self):
        with pytest.raises(Exception):
            res = wayback(['--proxy', 'test', '--proxy-default-timestamp', '2014abc'])

    def test_proxy_cli_rec(self):
        res = wayback(['--proxy', 'test', '--proxy-record'])
        assert res.extra_config['proxy']['recording'] == True
        assert res.extra_config['collections']['live'] == {'index': '$live'}

    def test_proxy_cli_err_coll(self):
        with pytest.raises(Exception):
            res = wayback(['--proxy', 'test/foo'])

    def test_auto_fetch_cli(self):
        res = wayback(['--enable-auto-fetch'])
        assert res.extra_config['enable_auto_fetch'] == True

    def test_all_cli(self):
        res = wayback(['--all-coll', 'all'])
        assert res.extra_config['collections']['all'] == '$all'

    def test_live_all_cli(self):
        res = wayback(['--all-coll', 'all', '--live'])
        assert res.extra_config['collections'] == {'live': {'index': '$live'},
                                                   'all': '$all'}

