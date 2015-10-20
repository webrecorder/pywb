"""
This module provides loaders for local file system and over http
local and remote access
"""

import os
import hmac
import urllib
#import urllib2
import requests
import urlparse
import time
import pkg_resources
from io import open, BytesIO

try:
    from boto import connect_s3
    s3_avail = True
except ImportError:  #pragma: no cover
    s3_avail = False


#=================================================================
def is_http(filename):
    return filename.startswith(('http://', 'https://'))


#=================================================================
def to_file_url(filename):
    """ Convert a filename to a file:// url
    """
    url = os.path.abspath(filename)
    url = urlparse.urljoin('file:', urllib.pathname2url(url))
    return url


#=================================================================
def load_yaml_config(config_file):
    import yaml
    configdata = BlockLoader().load(config_file)
    config = yaml.load(configdata)
    return config


#=================================================================
def extract_post_query(method, mime, length, stream, buffered_stream=None):
    """
    Extract a url-encoded form POST from stream
    If not a application/x-www-form-urlencoded, or no missing
    content length, return None
    """
    if method.upper() != 'POST':
        return None

    if ((not mime or
         not mime.lower().startswith('application/x-www-form-urlencoded'))):
        return None

    try:
        length = int(length)
    except (ValueError, TypeError):
        return None

    if length <= 0:
        return None

    #todo: encoding issues?
    post_query = ''

    while length > 0:
        buff = stream.read(length)
        length -= len(buff)

        if not buff:
            break

        post_query += buff

    if buffered_stream:
        buffered_stream.write(post_query)
        buffered_stream.seek(0)

    post_query = urllib.unquote_plus(post_query)
    return post_query


#=================================================================
def append_post_query(url, post_query):
    if not post_query:
        return url

    if '?' not in url:
        url += '?'
    else:
        url += '&'

    url += post_query
    return url


#=================================================================
def extract_client_cookie(env, cookie_name):
    cookie_header = env.get('HTTP_COOKIE')
    if not cookie_header:
        return None

    # attempt to extract cookie_name only
    inx = cookie_header.find(cookie_name)
    if inx < 0:
        return None

    end_inx = cookie_header.find(';', inx)
    if end_inx > 0:
        value = cookie_header[inx:end_inx]
    else:
        value = cookie_header[inx:]

    value = value.split('=')
    if len(value) < 2:
        return None

    value = value[1].strip()
    return value


#=================================================================
def read_last_line(fh, offset=256):
    """ Read last line from a seekable file. Start reading
    from buff before end of file, and double backwards seek
    until line break is found. If reached beginning of file
    (no lines), just return whole file
    """
    fh.seek(0, 2)
    size = fh.tell()

    while offset < size:
        fh.seek(-offset, 2)
        lines = fh.readlines()
        if len(lines) > 1:
            return lines[-1]
        offset *= 2

    fh.seek(0, 0)
    return fh.readlines()[-1]


#=================================================================
class BlockLoader(object):
    """
    a loader which can stream blocks of content
    given a uri, offset and optional length.
    Currently supports: http/https and file/local file system
    """

    def __init__(self, *args, **kwargs):
        self.cached = {}
        self.args = args
        self.kwargs = kwargs

    def load(self, url, offset=0, length=-1):
        loader = self._get_loader_for(url)
        return loader.load(url, offset, length)

    def _get_loader_for(self, url):
        """
        Determine loading method based on uri
        """
        parts = url.split('://', 1)
        if len(parts) < 2:
            type_ = 'file'
        else:
            type_ = parts[0]

        loader = self.cached.get(type_)
        if loader:
            return loader

        loader_cls = LOADERS.get(type_)
        if not loader_cls:
            raise IOError('No Loader for type: ' + type_)

        loader = loader_cls(*self.args, **self.kwargs)
        self.cached[type_] = loader
        return loader


    @staticmethod
    def _make_range_header(offset, length):
        if length > 0:
            range_header = 'bytes={0}-{1}'.format(offset, offset + length - 1)
        else:
            range_header = 'bytes={0}-'.format(offset)

        return range_header


#=================================================================
class LocalFileLoader(object):
    def __init__(self, *args, **kwargs):
        pass

    def load(self, url, offset=0, length=-1):
        """
        Load a file-like reader from the local file system
        """

        # if starting with . or /, can only be a file path..
        file_only = url.startswith(('/', '.'))

        # convert to filename
        if url.startswith('file://'):
            file_only = True
            url = urllib.url2pathname(url[len('file://'):])

        try:
            # first, try as file
            afile = open(url, 'rb')

        except IOError:
            if file_only:
                raise

            # then, try as package.path/file
            pkg_split = url.split('/', 1)
            if len(pkg_split) == 1:
                raise

            afile = pkg_resources.resource_stream(pkg_split[0],
                                                  pkg_split[1])

        if offset > 0:
            afile.seek(offset)

        if length >= 0:
            return LimitReader(afile, length)
        else:
            return afile


#=================================================================
class HttpLoader(object):
    def __init__(self, cookie_maker=None, *args, **kwargs):
        self.cookie_maker = cookie_maker
        self.session = None

    def load(self, url, offset, length):
        """
        Load a file-like reader over http using range requests
        and an optional cookie created via a cookie_maker
        """
        headers = {}
        if offset != 0 or length != -1:
            headers['Range'] = BlockLoader._make_range_header(offset, length)

        if self.cookie_maker:
            if isinstance(self.cookie_maker, basestring):
                headers['Cookie'] = self.cookie_maker
            else:
                headers['Cookie'] = self.cookie_maker.make()

        if not self.session:
            self.session = requests.Session()

        r = self.session.get(url, headers=headers, stream=True)
        return r.raw


#=================================================================
class S3Loader(object):
    def __init__(self, *args, **kwargs):
        self.s3conn = None

    def load(self, url, offset, length):
        if not s3_avail:  #pragma: no cover
           raise IOError('To load from s3 paths, ' +
                          'you must install boto: pip install boto')

        if not self.s3conn:
            try:
                self.s3conn = connect_s3()
            except Exception:  #pragma: no cover
                self.s3conn = connect_s3(anon=True)

        parts = urlparse.urlsplit(url)

        bucket = self.s3conn.get_bucket(parts.netloc)

        headers = {'Range': BlockLoader._make_range_header(offset, length)}

        key = bucket.get_key(parts.path)

        result = key.get_contents_as_string(headers=headers)
        key.close()

        return BytesIO(result)


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

    def read(self, length=None):
        if length is not None:
            length = min(length, self.limit)
        else:
            length = self.limit

        if length == 0:
            return ''

        buff = self.stream.read(length)
        self.limit -= len(buff)
        return buff

    def readline(self, length=None):
        if length is not None:
            length = min(length, self.limit)
        else:
            length = self.limit

        if length == 0:
            return ''

        buff = self.stream.readline(length)
        self.limit -= len(buff)
        return buff

    def close(self):
        self.stream.close()

    @staticmethod
    def wrap_stream(stream, content_length):
        """
        If given content_length is an int > 0, wrap the stream
        in a LimitReader. Ottherwise, return the stream unaltered
        """
        try:
            content_length = int(content_length)
            if content_length >= 0:
                # optimize: if already a LimitStream, set limit to
                # the smaller of the two limits
                if isinstance(stream, LimitReader):
                    stream.limit = min(stream.limit, content_length)
                else:
                    stream = LimitReader(stream, content_length)

        except (ValueError, TypeError):
            pass

        return stream


#=================================================================
LOADERS = {'http': HttpLoader,
           'https': HttpLoader,
           's3': S3Loader,
           'file': LocalFileLoader
          }


