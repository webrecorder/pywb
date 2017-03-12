from pywb.apps.cdx_server import application
from pywb.cdx.cdxserver import CDXServer, RemoteCDXServer
import pywb.cdx.cdxobject as obj

from pywb.utils.dsrules import DEFAULT_RULES_FILE
from pywb.utils.wbexception import AccessException, NotFoundException
from pywb.utils.wbexception import BadRequestException, WbException

from six.moves.urllib.error import HTTPError

from mock import patch
from pytest import raises
import webtest
import unittest

import six

from pywb import get_test_dir

TEST_CDX_DIR = get_test_dir() + 'cdx/'

CDX_SERVER_URL = 'http://localhost/pywb-cdx'

CDX_RESULT = [
 (obj.URLKEY, 'com,example)/'),
 (obj.TIMESTAMP, '20140127171200'),
 (obj.ORIGINAL, 'http://example.com'),
 (obj.MIMETYPE, 'text/html'),
 (obj.STATUSCODE, '200'),
 (obj.DIGEST, 'B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A'),
 (obj.REDIRECT, '-'),
 (obj.ROBOTFLAGS, '-'),
 (obj.LENGTH, '1046'),
 (obj.OFFSET, '334'),
 (obj.FILENAME, 'dupes.warc.gz')
]

testapp = None

def setup_module(self):
    global testapp
    testapp = webtest.TestApp(application)


def mock_urlopen(req):
    resp = testapp.get(req.get_full_url())
    return resp.body.split(b'\n')

def mock_urlopen_err(err):
    def make_err(req):
        raise HTTPError(req.get_full_url(), err, None, None, None)
    return make_err

# First time expect a 404 when called with 'exact',
# Second time expect a 200 for fuzzy match
def mock_urlopen_fuzzy(req):
    status = 200
    print(req.get_full_url())
    if 'exact' in req.get_full_url():
        status = 404

    resp = testapp.get(req.get_full_url(), status=status)

    if status == 200:
        return resp.body.split(b'\n')
    else:
        raise mock_urlopen_err(404)(req)

@patch('pywb.cdx.cdxsource.urlopen', mock_urlopen)
def assert_cdx_match(server):
    x = server.load_cdx(url='example.com',
                        limit=2,
                        output='cdxobject')
    x = list(x)
    assert(list(x[1].items()) == CDX_RESULT)

def assert_cdx_fuzzy_match(server, mock=mock_urlopen):
    with patch('pywb.cdx.cdxsource.urlopen', mock):
        x = server.load_cdx(url='http://example.com?_=123',
                            limit=2,
                            output='cdxobject',
                            allowFuzzy=True)
    x = list(x)
    assert(list(x[1].items()) == CDX_RESULT)


@patch('pywb.cdx.cdxsource.urlopen', mock_urlopen_err(404))
def assert_404(server):
    server.load_cdx(url='http://notfound.example.com')


@patch('pywb.cdx.cdxsource.urlopen', mock_urlopen_err(403))
def assert_403(server):
    server.load_cdx(url='http://notfound.example.com')


@patch('pywb.cdx.cdxsource.urlopen', mock_urlopen_err(400))
def assert_400(server):
    server.load_cdx(url='http://notfound.example.com')


@patch('pywb.cdx.cdxsource.urlopen', mock_urlopen_err(502))
def assert_502(server):
    server.load_cdx(url='http://notfound.example.com')


def test_match():
    # Local CDX Server
    assert_cdx_match(CDXServer([TEST_CDX_DIR]))

    # Remote CDX Source, Local Filtering
    assert_cdx_match(CDXServer(CDX_SERVER_URL))

    # Remote CDX Query (Remote Filtering)
    assert_cdx_match(RemoteCDXServer(CDX_SERVER_URL))


def test_fuzzy_match():
    # Local CDX Server
    assert_cdx_fuzzy_match(CDXServer([TEST_CDX_DIR],
                           ds_rules_file=DEFAULT_RULES_FILE))

    # Remote CDX Source, Local Filtering
    # two calls to remote, first exact with 404,
    # then fuzzy with 200
    assert_cdx_fuzzy_match(CDXServer(CDX_SERVER_URL,
                           ds_rules_file=DEFAULT_RULES_FILE),
                           mock_urlopen_fuzzy)

    # Remote CDX Query (Remote Filtering)
    # fuzzy match handled on remote, single response
    assert_cdx_fuzzy_match(RemoteCDXServer(CDX_SERVER_URL,
                           ds_rules_file=DEFAULT_RULES_FILE))

def test_fuzzy_no_match_1():
    # no match, no fuzzy
    with patch('pywb.cdx.cdxsource.urlopen', mock_urlopen):
        server = CDXServer([TEST_CDX_DIR], ds_rules_file=DEFAULT_RULES_FILE)
        with raises(NotFoundException):
            server.load_cdx(url='http://notfound.example.com/',
                            output='cdxobject',
                            reverse=True,
                            allowFuzzy=True)

def test_fuzzy_no_match_2():
    # fuzzy rule, but no actual match
    with patch('pywb.cdx.cdxsource.urlopen', mock_urlopen):
        server = CDXServer([TEST_CDX_DIR], ds_rules_file=DEFAULT_RULES_FILE)
        with raises(NotFoundException):
            server.load_cdx(url='http://notfound.example.com/?_=1234',
                            closest='2014',
                            reverse=True,
                            output='cdxobject',
                            allowFuzzy=True)

def test2_fuzzy_no_match_3():
    # special fuzzy rule, matches prefix test.example.example.,
    # but doesn't match rule regex
    with patch('pywb.cdx.cdxsource.urlopen', mock_urlopen):
        server = CDXServer([TEST_CDX_DIR], ds_rules_file=DEFAULT_RULES_FILE)
        with raises(NotFoundException):
            server.load_cdx(url='http://test.example.example/',
                            allowFuzzy=True)

def assert_error(func, exception):
    with raises(exception):
        func(CDXServer(CDX_SERVER_URL))

    with raises(exception):
        func(RemoteCDXServer(CDX_SERVER_URL))

def test_err_404():
    # Test local for consistency
    with raises(NotFoundException):
        assert_404(CDXServer([TEST_CDX_DIR]))

    assert_error(assert_404, NotFoundException)

def test_err_403():
    assert_error(assert_403, AccessException)

def test_err_400():
    assert_error(assert_400, BadRequestException)

def test_err_502():
    assert_error(assert_502, WbException)
