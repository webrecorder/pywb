"""
>>> redis_cdx('http://example.com')
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz
com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz
com,example)/ 20140127171251 http://example.com warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 11875 dupes.warc.gz

"""

from fakeredis import FakeStrictRedis
from mock import patch

from pywb.utils.timeutils import timestamp_to_sec
from pywb.cdx.cdxsource import RedisCDXSource
from pywb.cdx.cdxserver import CDXServer

from pywb import get_test_dir

import sys
import os

test_cdx_dir = get_test_dir() + 'cdx/'


def load_cdx_into_redis(source, filename):
    # load a cdx into mock redis
    with open(test_cdx_dir + filename) as fh:
        for line in fh:
            zadd_cdx(source, line)

def zadd_cdx(source, cdx):
    parts = cdx.split(' ', 2)

    key = parts[0]
    timestamp = parts[1]
    rest = timestamp + ' ' + parts[2]

    score = timestamp_to_sec(timestamp)
    source.redis.zadd(source.key_prefix + key, score, rest)



@patch('redis.StrictRedis', FakeStrictRedis)
def init_redis_server():
    source = RedisCDXSource('redis://127.0.0.1:6379/0')

    for f in os.listdir(test_cdx_dir):
        if f.endswith('.cdx'):
            load_cdx_into_redis(source, f)

    return CDXServer([source])

def redis_cdx(url, **params):
    cdx_iter = cdx_server.load_cdx(url=url, **params)
    for cdx in cdx_iter:
        sys.stdout.write(cdx)

cdx_server = init_redis_server()
