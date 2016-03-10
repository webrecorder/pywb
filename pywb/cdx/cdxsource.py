from pywb.utils.binsearch import iter_range

from pywb.utils.wbexception import AccessException, NotFoundException
from pywb.utils.wbexception import BadRequestException, WbException

from pywb.cdx.query import CDXQuery

from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.error import HTTPError
from six.moves import map


#=================================================================
class CDXSource(object):
    """
    Represents any cdx index source
    """
    def load_cdx(self, query):  # pragma: no cover
        raise NotImplementedError('Implement in subclass')


#=================================================================
class CDXFile(CDXSource):
    """
    Represents a local plain-text .cdx file
    """
    def __init__(self, filename):
        self.filename = filename

    def load_cdx(self, query):
        return self._do_load_file(self.filename, query)

    @staticmethod
    def _do_load_file(filename, query):
        with open(filename, 'rb') as source:
            gen = iter_range(source, query.key,
                                     query.end_key)
            for line in gen:
                yield line

    def __str__(self):
        return 'CDX File - ' + self.filename


#=================================================================
class RemoteCDXSource(CDXSource):
    """
    Represents a remote cdx server, to which requests will be proxied.

    Only ``url`` and ``match_type`` params are proxied at this time,
    the stream is passed through all other filters locally.
    """
    def __init__(self, filename, cookie=None, remote_processing=False):
        self.remote_url = filename
        self.cookie = cookie
        self.remote_processing = remote_processing

    def load_cdx(self, query):
        if self.remote_processing:
            remote_query = query
        else:
            # Only send url and matchType to remote
            remote_query = CDXQuery(dict(url=query.url,
                                         matchType=query.match_type))

        urlparams = remote_query.urlencode()

        try:
            request = Request(self.remote_url + '?' + urlparams)

            if self.cookie:
                request.add_header('Cookie', self.cookie)

            response = urlopen(request)

        except HTTPError as e:
            if e.code == 403:
                raise AccessException('Access Denied')
            elif e.code == 404:
                # return empty list for consistency with other cdx sources
                # will be converted to 404 if no other retry
                return []
            elif e.code == 400:
                raise BadRequestException()
            else:
                raise WbException('Invalid response from remote cdx server')

        return iter(response)

    def __str__(self):
        if self.remote_processing:
            return 'Remote CDX Server: ' + self.remote_url
        else:
            return 'Remote CDX Source: ' + self.remote_url


#=================================================================
class RedisCDXSource(CDXSource):
    DEFAULT_KEY_PREFIX = b'c:'

    def __init__(self, redis_url, config=None):
        import redis

        parts = redis_url.split('/')
        if len(parts) > 4:
            self.cdx_key = parts[4].encode('utf-8')
            redis_url = 'redis://' + parts[2] + '/' + parts[3]
        else:
            self.cdx_key = None

        self.redis_url = redis_url
        self.redis = redis.StrictRedis.from_url(redis_url)

        self.key_prefix = self.DEFAULT_KEY_PREFIX

    def load_cdx(self, query):
        """
        Load cdx from redis cache, from an ordered list

        If cdx_key is set, treat it as cdx file and load use
        zrangebylex! (Supports all match types!)

        Otherwise, assume a key per-url and load all entries for that key.
        (Only exact match supported)
        """

        if self.cdx_key:
            return self.load_sorted_range(query, self.cdx_key)
        else:
            return self.load_single_key(query.key)

    def load_sorted_range(self, query, cdx_key):
        cdx_list = self.redis.zrangebylex(cdx_key,
                                          b'[' + query.key,
                                          b'(' + query.end_key)

        return iter(cdx_list)

    def load_single_key(self, key):
        # ensure only url/surt is part of key
        key = key.split(b' ')[0]
        cdx_list = self.redis.zrange(self.key_prefix + key, 0, -1)

        # key is not part of list, so prepend to each line
        key += b' '
        cdx_list = list(map(lambda x: key + x, cdx_list))
        return cdx_list

    def __str__(self):
        return 'Redis - ' + self.redis_url
