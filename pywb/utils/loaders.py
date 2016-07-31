"""
This module provides loaders for local file system and over http
local and remote access
"""

import os
import hmac
import requests

import six
from six.moves.urllib.request import pathname2url, url2pathname
from six.moves.urllib.parse import urljoin, unquote_plus, urlsplit, urlencode

import time
import pkg_resources
import base64
import cgi

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
    url = urljoin('file:', pathname2url(url))
    return url


#=================================================================
def load_yaml_config(config_file):
    import yaml
    config = None
    configdata = None
    try:
        configdata = BlockLoader().load(config_file)
        config = yaml.load(configdata)
    finally:
        configdata.close()
        if configdata:
            configdata.close()

    return config


#=================================================================
def to_native_str(value, encoding='iso-8859-1', func=lambda x: x):
    if isinstance(value, str):
        return value

    if six.PY3 and isinstance(value, six.binary_type):  #pragma: no cover
        return func(value.decode(encoding))
    elif six.PY2 and isinstance(value, six.text_type):  #pragma: no cover
        return func(value.encode(encoding))


#=================================================================
def extract_post_query(method, mime, length, stream,
                       buffered_stream=None,
                       environ=None):
    """
    Extract a url-encoded form POST from stream
    content length, return None
    Attempt to decode application/x-www-form-urlencoded or multipart/*,
    otherwise read whole block and b64encode
    """
    if method.upper() != 'POST':
        return None

    try:
        length = int(length)
    except (ValueError, TypeError):
        return None

    if length <= 0:
        return None

    post_query = b''

    while length > 0:
        buff = stream.read(length)
        length -= len(buff)

        if not buff:
            break

        post_query += buff

    if buffered_stream:
        buffered_stream.write(post_query)
        buffered_stream.seek(0)

    if not mime:
        mime = ''

    if mime.startswith('application/x-www-form-urlencoded'):
        post_query = to_native_str(post_query)
        post_query = unquote_plus(post_query)

    elif mime.startswith('multipart/'):
        env = {'REQUEST_METHOD': 'POST',
               'CONTENT_TYPE': mime,
               'CONTENT_LENGTH': len(post_query)}

        args = dict(fp=BytesIO(post_query),
                    environ=env,
                    keep_blank_values=True)

        if six.PY3:
            args['encoding'] = 'utf-8'

        data = cgi.FieldStorage(**args)

        values = []
        for item in data.list:
            values.append((item.name, item.value))

        post_query = urlencode(values, True)

    elif mime.startswith('application/x-amf'):
        post_query = amf_parse(post_query, environ)

    else:
        post_query = base64.b64encode(post_query)
        post_query = to_native_str(post_query)
        post_query = '&__wb_post_data=' + post_query

    return post_query


#=================================================================
def amf_parse(string, environ):
    try:
        from pyamf import remoting

        res = remoting.decode(BytesIO(string))

        #print(res)
        body = res.bodies[0][1].body[0]

        values = {}

        if hasattr(body, 'body'):
            values['body'] = body.body

        if hasattr(body, 'source'):
            values['source'] = body.source

        if hasattr(body, 'operation'):
            values['op'] = body.operation

        if environ is not None:
            environ['pywb.inputdata'] = res

        query = urlencode(values)
        #print(query)
        return query

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
        return None


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
class BaseLoader(object):
    def __init__(self, **kwargs):
        pass

    def load(self, url, offset=0, length=-1):
        raise NotImplemented()


#=================================================================
class BlockLoader(BaseLoader):
    """
    a loader which can stream blocks of content
    given a uri, offset and optional length.
    Currently supports: http/https and file/local file system
    """

    loaders = {}
    profile_loader = None

    def __init__(self, **kwargs):
        self.cached = {}
        self.kwargs = kwargs

    def load(self, url, offset=0, length=-1):
        loader, url = self._get_loader_for_url(url)
        return loader.load(url, offset, length)

    def _get_loader_for_url(self, url):
        """
        Determine loading method based on uri
        """
        parts = url.split('://', 1)
        if len(parts) < 2:
            type_ = 'file'
        else:
            type_ = parts[0]

        if '+' in type_:
            profile_name, scheme = type_.split('+', 1)
            if len(parts) == 2:
                url = scheme + '://' + parts[1]
        else:
            profile_name = ''
            scheme = type_

        loader = self.cached.get(type_)
        if loader:
            return loader, url

        loader_cls = self._get_loader_class_for_type(scheme)

        if not loader_cls:
            raise IOError('No Loader for type: ' + scheme)

        profile = self.kwargs

        if self.profile_loader:
            profile = self.profile_loader(profile_name, scheme)

        loader = loader_cls(**profile)

        self.cached[type_] = loader
        return loader, url

    def _get_loader_class_for_type(self, type_):
        loader_cls = self.loaders.get(type_)
        return loader_cls

    @staticmethod
    def init_default_loaders():
        BlockLoader.loaders['http'] = HttpLoader
        BlockLoader.loaders['https'] = HttpLoader
        BlockLoader.loaders['s3'] = S3Loader
        BlockLoader.loaders['file'] = LocalFileLoader

    @staticmethod
    def set_profile_loader(src):
        BlockLoader.profile_loader = src

    @staticmethod
    def _make_range_header(offset, length):
        if length > 0:
            range_header = 'bytes={0}-{1}'.format(offset, offset + length - 1)
        else:
            range_header = 'bytes={0}-'.format(offset)

        return range_header


#=================================================================
class LocalFileLoader(BaseLoader):
    def load(self, url, offset=0, length=-1):
        """
        Load a file-like reader from the local file system
        """

        # if starting with . or /, can only be a file path..
        file_only = url.startswith(('/', '.'))

        # convert to filename
        if url.startswith('file://'):
            file_only = True
            url = url2pathname(url[len('file://'):])

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
class HttpLoader(BaseLoader):
    def __init__(self, **kwargs):
        self.cookie_maker = kwargs.get('cookie_maker')
        if not self.cookie_maker:
            self.cookie_maker = kwargs.get('cookie')
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
            if isinstance(self.cookie_maker, six.string_types):
                headers['Cookie'] = self.cookie_maker
            else:
                headers['Cookie'] = self.cookie_maker.make()

        if not self.session:
            self.session = requests.Session()

        r = self.session.get(url, headers=headers, stream=True)
        r.raise_for_status()
        return r.raw


#=================================================================
class S3Loader(BaseLoader):
    def __init__(self, **kwargs):
        self.s3conn = None
        self.aws_access_key_id = kwargs.get('aws_access_key_id')
        self.aws_secret_access_key = kwargs.get('aws_secret_access_key')

    def load(self, url, offset, length):
        if not s3_avail:  #pragma: no cover
           raise IOError('To load from s3 paths, ' +
                          'you must install boto: pip install boto')

        aws_access_key_id = self.aws_access_key_id
        aws_secret_access_key = self.aws_secret_access_key

        parts = urlsplit(url)

        if parts.username and parts.password:
            aws_access_key_id = unquote_plus(parts.username)
            aws_secret_access_key = unquote_plus(parts.password)
            bucket_name = parts.netloc.split('@', 1)[-1]
        else:
            bucket_name = parts.netloc

        if not self.s3conn:
            try:
                self.s3conn = connect_s3(aws_access_key_id, aws_secret_access_key)
            except Exception:  #pragma: no cover
                self.s3conn = connect_s3(anon=True)

        bucket = self.s3conn.get_bucket(bucket_name)

        key = bucket.get_key(parts.path)

        if offset == 0 and length == -1:
            headers = {}
        else:
            headers = {'Range': BlockLoader._make_range_header(offset, length)}

        # Read range
        key.open_read(headers=headers)
        return key


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
        expire = str(int(time.time() + self.duration))

        if extra_id:
            msg = extra_id + '-' + expire
        else:
            msg = expire

        hmacdigest = hmac.new(self.key.encode('utf-8'), msg.encode('utf-8'))
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
            return b''

        buff = self.stream.read(length)
        self.limit -= len(buff)
        return buff

    def readline(self, length=None):
        if length is not None:
            length = min(length, self.limit)
        else:
            length = self.limit

        if length == 0:
            return b''

        buff = self.stream.readline(length)
        self.limit -= len(buff)
        return buff

    def close(self):
        self.stream.close()

    @staticmethod
    def wrap_stream(stream, content_length):
        """
        If given content_length is an int > 0, wrap the stream
        in a LimitReader. Otherwise, return the stream unaltered
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

# ============================================================================
BlockLoader.init_default_loaders()

