r"""
#=================================================================
# BlockLoader Tests (includes LimitReader)
# Ensure attempt to read more than 100 bytes, reads exactly 100 bytes
>>> len(BlockLoader().load(test_cdx_dir + 'iana.cdx', 0, 100).read(400))
100

# no length specified, read full amount requested
>>> len(BlockLoader().load(to_file_url(test_cdx_dir + 'example.cdx'), 0, -1).read(400))
400

# no such file
#>>> len(BlockLoader().load('_x_no_such_file_', 0, 100).read(400))  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
IOError: [Errno 2] No such file or directory: '_x_no_such_file_'

# Disable for now
# HMAC Cookie Maker
#>>> print_str(BlockLoader(cookie_maker=HMACCookieMaker('test', 'test', 5), decode_content=False).load('https://example.com', 41, 14).read())
#'Example Domain'

# fixed cookie, range request
#>>> print_str(BlockLoader(cookie='some=value', decode_content=True).load('https://example.com', 41, 14).read())
'Example Domain'

# range request
#>>> print_str(BlockLoader(decode_content=True).load('https://example.com', 1248).read())
'</html>\n'

# custom profile
#>>> print_str(BlockLoader(decode_content=True).load('local+https://example.com', 1248).read())
'</html>\n'

# unknown loader error
#>>> BlockLoader().load('foo://example.com', 10).read()  # doctest: +IGNORE_EXCEPTION_DETAIL
#Traceback (most recent call last):
#IOError: No Loader for type: foo

# test with extra id, ensure 4 parts of the A-B=C-D form are present
>>> len(re.split('[-=]', HMACCookieMaker('test', 'test', 5).make('extra')))
4

# cookie extract tests
>>> extract_client_cookie(dict(HTTP_COOKIE='a=b; c=d'), 'a')
'b'

>>> extract_client_cookie(dict(HTTP_COOKIE='a=b; c=d'), 'c')
'd'

>>> extract_client_cookie(dict(HTTP_COOKIE='a=b; c=d'), 'x')

>>> extract_client_cookie(dict(HTTP_COOKIE='x'), 'x')

>>> extract_client_cookie({}, 'y')

# test read_last_line
>>> print_str(read_last_line(BytesIO(b'A\nB\nC')))
'C'

>>> print_str(read_last_line(BytesIO(b'Some Line\nLonger Line\nLongest Last Line LL'), offset=8))
'Longest Last Line LL'

>>> print_str(read_last_line(BytesIO(b'A\nBC')))
'BC'

>>> print_str(read_last_line(BytesIO(b'A\nBC\n')))
'BC\n'

>>> print_str(read_last_line(BytesIO(b'ABC')))
'ABC'

"""


#=================================================================
import re
import os
import pytest

import six
from six import StringIO
from io import BytesIO
import requests
import yaml
from yaml import Loader

from pywb.utils.loaders import BlockLoader, HMACCookieMaker, to_file_url
from pywb.utils.loaders import extract_client_cookie
from pywb.utils.loaders import read_last_line

from pywb.utils.canonicalize import canonicalize

from mock import patch

from warcio.bufferedreaders import DecompressingBufferedReader

from pywb import get_test_dir

test_cdx_dir = get_test_dir() + 'cdx/'

def s3_authenticated_access_verification(bucket):
    import boto3, botocore
    s3_client = boto3.client('s3')
    try:
        s3_client.head_bucket(Bucket=bucket)
    except botocore.exceptions.NoCredentialsError:
        pytest.skip("Skipping S3Loader test for authenticated reads: no credentials configured")

def test_s3_read_authenticated_1():
    pytest.importorskip('boto3')
    pytest.skip("credentials issue, to fix later")

    s3_authenticated_access_verification('commoncrawl')

    res = BlockLoader().load('s3://commoncrawl/crawl-data/CC-MAIN-2015-11/segments/1424936462700.28/warc/CC-MAIN-20150226074102-00159-ip-10-28-5-156.ec2.internal.warc.gz',
                             offset=53235662,
                             length=2526)

    buff = res.read()
    assert len(buff) == 2526

    reader = DecompressingBufferedReader(BytesIO(buff))
    assert reader.readline() == b'WARC/1.0\r\n'
    assert reader.readline() == b'WARC-Type: response\r\n'

def test_s3_read_authenticated_2():
    pytest.importorskip('boto3')
    pytest.skip("credentials issue, to fix later")

    s3_authenticated_access_verification('commoncrawl')

    res = BlockLoader().load('s3://commoncrawl/crawl-data/CC-MAIN-2015-11/index.html')

    buff = res.read()
    assert len(buff) == 2330

    reader = DecompressingBufferedReader(BytesIO(buff))
    assert reader.readline() == b'<!DOCTYPE html>\n'

def mock_load(expected):
    def mock(self, url, offset, length):
        assert canonicalize(url) == canonicalize(expected)
        assert offset == 0
        assert length == -1
        return None

    return mock

def test_mock_webhdfs_load_1():
    expected = 'http://remote-host:1234/webhdfs/v1/some/file.warc.gz?op=OPEN&offset=10&length=50'
    with patch('pywb.utils.loaders.HttpLoader.load', mock_load(expected)):
        res = BlockLoader().load('webhdfs://remote-host:1234/some/file.warc.gz', 10, 50)

def test_mock_webhdfs_load_2():
    expected = 'http://remote-host/webhdfs/v1/some/file.warc.gz?op=OPEN&offset=10'
    with patch('pywb.utils.loaders.HttpLoader.load', mock_load(expected)):
        res = BlockLoader().load('webhdfs://remote-host/some/file.warc.gz', 10, -1)

def test_mock_webhdfs_load_3_username():
    os.environ['WEBHDFS_USER'] = 'someuser'
    expected = 'http://remote-host/webhdfs/v1/some/file.warc.gz?op=OPEN&offset=10&user.name=someuser'
    with patch('pywb.utils.loaders.HttpLoader.load', mock_load(expected)):
        res = BlockLoader().load('webhdfs://remote-host/some/file.warc.gz', 10, -1)

def test_mock_webhdfs_load_4_token():
    os.environ['WEBHDFS_USER'] = ''
    os.environ['WEBHDFS_TOKEN'] = 'ATOKEN'
    expected = 'http://remote-host/webhdfs/v1/some/file.warc.gz?op=OPEN&offset=10&delegation=ATOKEN'
    with patch('pywb.utils.loaders.HttpLoader.load', mock_load(expected)):
        res = BlockLoader().load('webhdfs://remote-host/some/file.warc.gz', 10, -1)


# Error
def test_err_no_such_file():
    # no such file
    with pytest.raises(IOError):
        len(BlockLoader().load('_x_no_such_file_', 0, 100).read('400'))


def test_err_unknown_loader():
    # unknown loader error
    with pytest.raises(IOError):
        BlockLoader().load('foo://example.com', 10).read()
#IOError: No Loader for type: foo



def test_yaml_resolve_env():
    os.environ['PYWB_PATH'] = './test'
    os.environ['PYWB_FOO'] = 'bar'

    config = """\
collection:
    coll:
        index: ${PYWB_PATH}/index
        archive: ${PYWB_PATH}/archive/${PYWB_FOO}
        other: ${PYWB_NOT}/archive/${PYWB_FOO}
"""

    config_data = yaml.load(config, Loader=Loader)

    assert config_data['collection']['coll']['index'] == './test/index'
    assert config_data['collection']['coll']['archive'] == './test/archive/bar'
    assert config_data['collection']['coll']['other'] == '${PYWB_NOT}/archive/bar'

    del os.environ['PYWB_PATH']
    del os.environ['PYWB_FOO']

def print_str(string):
    return string.decode('utf-8') if six.PY3 else string


if __name__ == "__main__":
    import doctest
    doctest.testmod()


