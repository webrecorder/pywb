from pywb.apps.cdx_server import application
from pywb.cdx.cdxserver import CDXServer, RemoteCDXServer

from pywb.utils.wbexception import AccessException, NotFoundException
from pywb.utils.wbexception import BadRequestException, WbException

from urllib2 import HTTPError

from mock import patch
from pytest import raises
import webtest

from pywb import get_test_dir

TEST_CDX_DIR = get_test_dir() + 'cdx/'

CDX_SERVER_URL = 'http://localhost/cdx'

CDX_RESULT = [
 ('urlkey', 'com,example)/'),
 ('timestamp', '20140127171200'),
 ('original', 'http://example.com'),
 ('mimetype', 'text/html'),
 ('statuscode', '200'),
 ('digest', 'B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A'),
 ('redirect', '-'),
 ('robotflags', '-'),
 ('length', '1046'),
 ('offset', '334'),
 ('filename', 'dupes.warc.gz')
]

testapp = None

def setup_module(self):
    global testapp
    testapp = webtest.TestApp(application)


def mock_urlopen(req):
    resp = testapp.get(req.get_full_url())
    return resp.body.split('\n')

def mock_urlopen_err(err):
    def make_err(req):
        raise HTTPError(req.get_full_url(), err, None, None, None)
    return make_err

# First time expect a 404 when called with 'exact',
# Second time expect a 200 for fuzzy match
def mock_urlopen_fuzzy(req):
    status = 200
    if 'exact' in req.get_full_url():
        status = 404

    resp = testapp.get(req.get_full_url(), status=status)

    if status == 200:
        return resp.body.split('\n')
    else:
        raise mock_urlopen_err(404)(req)

@patch('pywb.cdx.cdxsource.urllib2.urlopen', mock_urlopen)
def assert_cdx_match(server):
    x = server.load_cdx(url='example.com',
                        limit=2,
                        output='cdxobject')
    x.next()
    assert x.next().items() == CDX_RESULT


def assert_cdx_fuzzy_match(server, mock=mock_urlopen):
    with patch('pywb.cdx.cdxsource.urllib2.urlopen', mock):
        x = server.load_cdx(url='http://example.com?_=123',
                            limit=2,
                            output='cdxobject',
                            allowFuzzy=True)
    x.next()
    assert x.next().items() == CDX_RESULT


@patch('pywb.cdx.cdxsource.urllib2.urlopen', mock_urlopen_err(404))
def assert_404(server):
    server.load_cdx(url='http://notfound.example.com')


@patch('pywb.cdx.cdxsource.urllib2.urlopen', mock_urlopen_err(403))
def assert_403(server):
    server.load_cdx(url='http://notfound.example.com')


@patch('pywb.cdx.cdxsource.urllib2.urlopen', mock_urlopen_err(400))
def assert_400(server):
    server.load_cdx(url='http://notfound.example.com')


@patch('pywb.cdx.cdxsource.urllib2.urlopen', mock_urlopen_err(502))
def assert_502(server):
    server.load_cdx(url='http://notfound.example.com')


def test_match():
    # Local CDX Server
    assert_cdx_match(CDXServer([TEST_CDX_DIR]))

    # Remote CDX Source, Local Filtering
    assert_cdx_match(CDXServer(CDX_SERVER_URL))

    # Remote CDX Query (Remote Filtering)
    assert_cdx_match(RemoteCDXServer(CDX_SERVER_URL))


# TODO: make these automatic
DEFAULT_RULES = 'pywb/rules.yaml'

def test_fuzzy_match():
    # Local CDX Server
    assert_cdx_fuzzy_match(CDXServer([TEST_CDX_DIR],
                           ds_rules_file=DEFAULT_RULES))

    # Remote CDX Source, Local Filtering
    # two calls to remote, first exact with 404,
    # then fuzzy with 200
    assert_cdx_fuzzy_match(CDXServer(CDX_SERVER_URL,
                           ds_rules_file=DEFAULT_RULES),
                           mock_urlopen_fuzzy)

    # Remote CDX Query (Remote Filtering)
    # fuzzy match handled on remote, single response
    assert_cdx_fuzzy_match(RemoteCDXServer(CDX_SERVER_URL,
                           ds_rules_file=DEFAULT_RULES))

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
