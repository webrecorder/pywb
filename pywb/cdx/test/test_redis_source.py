"""
>>> redis_cdx(redis_cdx_server, 'http://example.com')
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz
com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz
com,example)/ 20140127171251 http://example.com warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 11875 dupes.warc.gz

>>> redis_cdx(redis_cdx_server_key, 'http://example.com')
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz
com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz
com,example)/ 20140127171251 http://example.com warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 11875 dupes.warc.gz

"""

from fakeredis import FakeStrictRedis
from mock import patch

from warcio.timeutils import timestamp_to_sec
from pywb.cdx.cdxsource import RedisCDXSource
from pywb.cdx.cdxserver import CDXServer

from pywb import get_test_dir

import sys
import os

test_cdx_dir = os.path.join(get_test_dir(), 'cdx/')

def load_cdx_into_redis(source, filename, key=None):
    # load a cdx into mock redis
    with open(test_cdx_dir + filename, 'rb') as fh:
        for line in fh:
            zadd_cdx(source, line, key)

def zadd_cdx(source, cdx, key):
    if key:
        source.redis.zadd(key, 0, cdx)
        return

    parts = cdx.split(b' ', 2)

    key = parts[0]
    timestamp = parts[1]
    rest = timestamp + b' ' + parts[2]

    score = timestamp_to_sec(timestamp.decode('utf-8'))
    source.redis.zadd(source.key_prefix + key, score, rest)



@patch('redis.StrictRedis', FakeStrictRedis)
def init_redis_server():
    source = RedisCDXSource('redis://127.0.0.1:6379/0')

    for f in os.listdir(test_cdx_dir):
        if f.endswith('.cdx'):
            load_cdx_into_redis(source, f)

    return CDXServer([source])

@patch('redis.StrictRedis', FakeStrictRedis)
def init_redis_server_key_file():
    source = RedisCDXSource('redis://127.0.0.1:6379/0/key')

    for f in os.listdir(test_cdx_dir):
        if f.endswith('.cdx'):
            load_cdx_into_redis(source, f, source.cdx_key)

    return CDXServer([source])


def redis_cdx(cdx_server, url, **params):
    cdx_iter = cdx_server.load_cdx(url=url, **params)
    for cdx in cdx_iter:
        sys.stdout.write(cdx)

redis_cdx_server = init_redis_server()
redis_cdx_server_key = init_redis_server_key_file()

