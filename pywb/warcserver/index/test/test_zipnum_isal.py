import os
import subprocess
import sys
import zlib as stdlib_zlib

import pytest

import pywb
from pywb import get_test_dir
from pywb.warcserver.index import zipnum
from pywb.warcserver.index.zipnum import ZipNumIndexSource


TEST_ZIPNUM = get_test_dir() + 'zipcdx/zipnum-sample.idx'

QUERIES = [
    {'url': 'http://iana.org/'},
    {'url': 'http://example.com/'},
    {'url': 'http://iana.org/domains/', 'matchType': 'prefix'},
    {'url': 'iana.org', 'matchType': 'domain'},
    {'url': 'iana.org', 'matchType': 'domain', 'pageSize': '4', 'page': '2'},
    {'url': 'http://iana.org/not-archived'},
]


def lookup_all(monkeypatch, zlib_module):
    monkeypatch.setattr(zipnum, 'zlib', zlib_module)
    source = ZipNumIndexSource(TEST_ZIPNUM)
    return [[str(cdx) for cdx in source.load_index(dict(params))] for params in QUERIES]


def test_isal_is_used_if_installed():
    isal_zlib = pytest.importorskip('isal.isal_zlib')
    assert zipnum.zlib is isal_zlib


def test_zlib_is_used_without_isal():
    root = os.path.dirname(os.path.dirname(os.path.abspath(pywb.__file__)))
    code = ("import sys; sys.modules['isal'] = None; "
            "from pywb.warcserver.index import zipnum; print(zipnum.zlib.__name__)")

    env = dict(os.environ, PYTHONPATH=root)
    out = subprocess.check_output([sys.executable, '-c', code], cwd=root, env=env)
    assert out.strip() == b'zlib'


def test_same_results_with_isal_and_zlib(monkeypatch):
    isal_zlib = pytest.importorskip('isal.isal_zlib')

    expected = lookup_all(monkeypatch, stdlib_zlib)
    assert [len(lines) for lines in expected] == [3, 2, 9, 46, 20, 0]

    assert lookup_all(monkeypatch, isal_zlib) == expected
