"""
This module provides loaders for local file system and over http
local and remote access
"""

import os
import hmac
import urllib2
import time


def is_http(filename):
    return any(filename.startswith(x) for x in ['http://', 'https://'])


#=================================================================
class BlockLoader(object):
    """
    a loader which can stream blocks of content
    given a uri, offset and optional length.
    Currently supports: http/https and file/local file system
    """
    def __init__(self, cookie_maker=None):
        self.cookie_maker = cookie_maker

    def load(self, url, offset, length):
        """
        Determine loading method based on uri
        """
        if is_http(url):
            return self.load_http(url, offset, length)
        else:
            return self.load_file(url, offset, length)

    def load_file(self, url, offset, length):
        """
        Load a file-like reader from the local file system
        """

        if url.startswith('file://'):
            url = url[len('file://'):]

        afile = open(url, 'rb')
        afile.seek(offset)

        if length > 0:
            return LimitReader(afile, length)
        else:
            return afile

    def load_http(self, url, offset, length):
        """
        Load a file-like reader over http using range requests
        and an optional cookie created via a cookie_maker
        """
        if length > 0:
            range_header = 'bytes={0}-{1}'.format(offset, offset + length - 1)
        else:
            range_header = 'bytes={0}-'.format(offset)

        headers = {}
        headers['Range'] = range_header

        if self.cookie_maker:
            headers['Cookie'] = self.cookie_maker.make()

        request = urllib2.Request(url, headers=headers)
        return urllib2.urlopen(request)


#=================================================================
# Signed Cookie-Maker
#=================================================================

class HMACCookieMaker(object):
    """
    Utility class to produce signed HMAC digest cookies
    to be used with each http request
    """
    def __init__(self, key, name, duration=10):
        self.key = key
        self.name = name
        # duration in seconds
        self.duration = duration

    def make(self, extra_id=''):
        expire = str(long(time.time() + self.duration))

        if extra_id:
            msg = extra_id + '-' + expire
        else:
            msg = expire

        hmacdigest = hmac.new(self.key, msg)
        hexdigest = hmacdigest.hexdigest()

        if extra_id:
            cookie = '{0}-{1}={2}-{3}'.format(self.name, extra_id,
                                              expire, hexdigest)
        else:
            cookie = '{0}={1}-{2}'.format(self.name, expire, hexdigest)

        return cookie


#=================================================================
# Limit Reader
#=================================================================
class LimitReader(object):
    """
    A reader which will not read more than specified limit
    """

    def __init__(self, stream, limit):
        self.stream = stream
        self.limit = limit

        if not self.limit:
            self.limit = 1

    def read(self, length=None):
        length = min(length, self.limit) if length else self.limit
        buff = self.stream.read(length)
        self.limit -= len(buff)
        return buff

    def readline(self, length=None):
        length = min(length, self.limit) if length else self.limit
        buff = self.stream.readline(length)
        self.limit -= len(buff)
        return buff

    def close(self):
        self.stream.close()


#=================================================================
# Local text file with known size -- used for binsearch
#=================================================================
class SeekableTextFileReader(object):
    """
    A very simple file-like object wrapper that knows it's total size,
    via getsize()
    Supports seek() operation.
    Assumed to be a text file. Used for binsearch.
    """
    def __init__(self, filename):
        self.fh = open(filename, 'rb')
        self.filename = filename
        self.size = os.path.getsize(filename)

    def getsize(self):
        return self.size

    def read(self):
        return self.fh.read()

    def readline(self):
        return self.fh.readline()

    def seek(self, offset):
        return self.fh.seek(offset)

    def close(self):
        return self.fh.close()
