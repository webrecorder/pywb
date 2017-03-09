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

# HMAC Cookie Maker
>>> print_str(BlockLoader(cookie_maker=HMACCookieMaker('test', 'test', 5)).load('http://example.com', 41, 14).read())
'Example Domain'

# fixed cookie, range request
>>> print_str(BlockLoader(cookie='some=value').load('http://example.com', 41, 14).read())
'Example Domain'

# range request
>>> print_str(BlockLoader().load('http://example.com', 1262).read())
'</html>\n'

# custom profile
>>> print_str(BlockLoader().load('local+http://example.com', 1262).read())
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

# append_post_query
>>> append_post_query('http://example.com/?abc=def', 'foo=bar')
'http://example.com/?abc=def&foo=bar'

>>> append_post_query('http://example.com/', '')
'http://example.com/'

>>> append_post_query('http://example.com/', 'foo=bar')
'http://example.com/?foo=bar'

# extract_post_query tests

# correct POST data
>>> post_data = b'foo=bar&dir=%2Fbaz'
>>> extract_post_query('POST', 'application/x-www-form-urlencoded', len(post_data), BytesIO(post_data))
'foo=bar&dir=/baz'

# unsupported method
>>> extract_post_query('PUT', 'application/x-www-form-urlencoded', len(post_data), BytesIO(post_data))

# base64 encode
>>> extract_post_query('POST', 'text/plain', len(post_data), BytesIO(post_data))
'&__wb_post_data=Zm9vPWJhciZkaXI9JTJGYmF6'

# invalid length
>>> extract_post_query('POST', 'application/x-www-form-urlencoded', 'abc', BytesIO(post_data))
>>> extract_post_query('POST', 'application/x-www-form-urlencoded', 0, BytesIO(post_data))

# length too short
>>> extract_post_query('POST', 'application/x-www-form-urlencoded', len(post_data) - 4, BytesIO(post_data))
'foo=bar&dir=%2'

# length too long
>>> extract_post_query('POST', 'application/x-www-form-urlencoded', len(post_data) + 4, BytesIO(post_data))
'foo=bar&dir=/baz'


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

from pywb.utils.loaders import BlockLoader, HMACCookieMaker, to_file_url
from pywb.utils.loaders import extract_client_cookie, extract_post_query
from pywb.utils.loaders import append_post_query, read_last_line

from warcio.bufferedreaders import DecompressingBufferedReader

from pywb import get_test_dir

test_cdx_dir = get_test_dir() + 'cdx/'


def test_s3_read_1():
    pytest.importorskip('boto')

    res = BlockLoader().load('s3://commoncrawl/crawl-data/CC-MAIN-2015-11/segments/1424936462700.28/warc/CC-MAIN-20150226074102-00159-ip-10-28-5-156.ec2.internal.warc.gz',
                             offset=53235662,
                             length=2526)

    buff = res.read()
    assert len(buff) == 2526

    reader = DecompressingBufferedReader(BytesIO(buff))
    assert reader.readline() == b'WARC/1.0\r\n'
    assert reader.readline() == b'WARC-Type: response\r\n'

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


def print_str(string):
    return string.decode('utf-8') if six.PY3 else string


if __name__ == "__main__":
    import doctest
    doctest.testmod()


