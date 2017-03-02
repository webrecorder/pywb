from pywb.utils.binsearch import iter_range
from warcio.timeutils import timestamp_to_http_date, http_date_to_timestamp
from warcio.timeutils import timestamp_now
from pywb.utils.canonicalize import canonicalize
from pywb.utils.wbexception import NotFoundException

from pywb.cdx.cdxobject import CDXObject

from pywb.webagg.utils import ParamFormatter, res_template
from pywb.webagg.utils import MementoUtils

import redis
import requests
import re


WAYBACK_ORIG_SUFFIX = '{timestamp}id_/{url}'


#=============================================================================
class BaseIndexSource(object):
    def load_index(self, params):  #pragma: no cover
        raise NotImplemented()


#=============================================================================
class FileIndexSource(BaseIndexSource):
    CDX_EXT = ('.cdx', '.cdxj')

    def __init__(self, filename):
        self.filename_template = filename

    def load_index(self, params):
        filename = res_template(self.filename_template, params)

        try:
            fh = open(filename, 'rb')
        except IOError:
            raise NotFoundException(filename)

        def do_load(fh):
            with fh:
                gen = iter_range(fh, params['key'], params['end_key'])
                for line in gen:
                    yield CDXObject(line)

        return do_load(fh)

    def __repr__(self):
        return '{0}(file://{1})'.format(self.__class__.__name__,
                                        self.filename_template)

    def __str__(self):
        return 'file'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.filename_template == other.filename_template

    @classmethod
    def init_from_string(cls, value):
        if value.startswith('file://'):
            return cls(value[7:])

        if not value.endswith(cls.CDX_EXT):
            return None

        if value.startswith('/') or '://' not in value:
            return cls(value)

    @classmethod
    def init_from_config(cls, config):
        if config['type'] != 'file':
            return

        return cls.init_from_string(config['path'])


#=============================================================================
class RemoteIndexSource(BaseIndexSource):
    CDX_MATCH_RX = re.compile('^cdxj?\+(?P<url>https?\:.*)')

    def __init__(self, api_url, replay_url, url_field='load_url', closest_limit=10):
        self.api_url = api_url
        self.replay_url = replay_url
        self.url_field = url_field
        self.closest_limit = closest_limit

    def _get_api_url(self, params):
        api_url = res_template(self.api_url, params)
        if 'timestamp' in params and self.closest_limit:
            api_url += '&limit=' + str(self.closest_limit)

        return api_url

    def load_index(self, params):
        api_url = self._get_api_url(params)
        r = requests.get(api_url, timeout=params.get('_timeout'))
        if r.status_code >= 400:
            raise NotFoundException(api_url)

        lines = r.content.strip().split(b'\n')
        def do_load(lines):
            for line in lines:
                if not line:
                    continue

                cdx = CDXObject(line)
                self._set_load_url(cdx)
                yield cdx

        return do_load(lines)

    def _set_load_url(self, cdx):
        cdx[self.url_field] = self.replay_url.format(
                                 timestamp=cdx['timestamp'],
                                 url=cdx['url'])

    def __repr__(self):
        return '{0}({1}, {2})'.format(self.__class__.__name__,
                                      self.api_url,
                                      self.replay_url)

    def __str__(self):
        return 'cdx'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.api_url == other.api_url and
                self.replay_url == other.replay_url)

    @classmethod
    def init_from_string(cls, value):
        m = cls.CDX_MATCH_RX.match(value)
        if not m:
            return

        url = m.group('url')
        coll = ''

        parts = url.split(' ', 1)
        if len(parts) == 2:
            url = parts[0]
            coll = parts[1]

        # pywb style cdx, just remove -cdx to get coll path
        if not coll and url.endswith('-cdx'):
            replay = url[:-4] + '/' + WAYBACK_ORIG_SUFFIX
        else:
        # add specified coll, if any
            replay = url.rsplit('/', 1)[0] + coll + '/' + WAYBACK_ORIG_SUFFIX

        url += '?url={url}&closest={timestamp}&sort=closest'

        return cls(url, replay)

    @classmethod
    def init_from_config(cls, config):
        if config['type'] != 'cdx':
            return

        return cls(config['api_url'], config['replay_url'])


#=============================================================================
class LiveIndexSource(BaseIndexSource):
    def __init__(self, proxy_url='{url}'):
        self.proxy_url = proxy_url

    def load_index(self, params):
        cdx = CDXObject()
        cdx['urlkey'] = params.get('key').decode('utf-8')
        cdx['timestamp'] = timestamp_now()
        cdx['url'] = params['url']
        cdx['load_url'] = res_template(self.proxy_url, params)
        cdx['is_live'] = 'true'
        cdx['mime'] = params.get('content_type', '')
        def live():
            yield cdx

        return live()

    def __repr__(self):
        return '{0}()'.format(self.__class__.__name__)

    def __str__(self):
        return 'live'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return True

    @classmethod
    def init_from_string(cls, value):
        if value in ('$live', 'live'):
            return cls()

        if value.startswith('live+'):
            return cls(value[5:])

    @classmethod
    def init_from_config(cls, config):
        if config['type'] != 'live':
            return

        return cls()


#=============================================================================
class RedisIndexSource(BaseIndexSource):
    def __init__(self, redis_url=None, redis=None, key_template=None, **kwargs):
        if redis_url:
            redis, key_template = self.parse_redis_url(redis_url, redis)

        self.redis_url = redis_url
        self.redis = redis
        self.redis_key_template = key_template
        self.member_key_template = kwargs.get('member_key_templ')

    @staticmethod
    def parse_redis_url(redis_url, redis_=None):
        parts = redis_url.split('/')
        key_prefix = ''
        if len(parts) > 4:
            key_prefix = parts[4]
            redis_url = 'redis://' + parts[2] + '/' + parts[3]

        redis_key_template = key_prefix
        if not redis_:
            redis_ = redis.StrictRedis.from_url(redis_url)
        return redis_, key_prefix

    def scan_keys(self, match_templ, params, member_key=None):
        if not member_key:
            member_key = self.member_key_template

        if not member_key:
            return self.redis.scan_iter(match=match_templ)

        key = res_template(member_key, params)

        keys = self.redis.smembers(key)

        match_templ = match_templ.encode('utf-8')

        return [match_templ.replace(b'*', key) for key in keys]

    def load_index(self, params):
        return self.load_key_index(self.redis_key_template, params)

    def load_key_index(self, key_template, params):
        z_key = res_template(key_template, params)
        index_list = self.redis.zrangebylex(z_key,
                                            b'[' + params['key'],
                                            b'(' + params['end_key'])

        def do_load(index_list):
            for line in index_list:
                yield CDXObject(line)

        return do_load(index_list)

    def __repr__(self):
        return '{0}({1}, {2}, {3})'.format(self.__class__.__name__,
                                           self.redis_url,
                                           self.redis,
                                           self.redis_key_template)

    def __str__(self):
        return 'redis'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.redis_key_template == other.redis_key_template and
                self.redis == other.redis)

    @classmethod
    def init_from_string(cls, value):
        if value.startswith('redis://'):
            return cls(value)

    @classmethod
    def init_from_config(cls, config):
        if config['type'] != 'redis':
            return

        return cls.init_from_string(config['redis_url'])


#=============================================================================
class MementoIndexSource(BaseIndexSource):
    def __init__(self, timegate_url, timemap_url, replay_url):
        self.timegate_url = timegate_url
        self.timemap_url = timemap_url
        self.replay_url = replay_url

    def links_to_cdxobject(self, link_header, def_name):
        results = MementoUtils.parse_links(link_header, def_name)

        original = results['original']['url']
        key = canonicalize(original)

        mementos = results['mementos']

        for val in mementos:
            dt = val['datetime']
            ts = http_date_to_timestamp(dt)
            cdx = CDXObject()
            cdx['urlkey'] = key
            cdx['timestamp'] = ts
            cdx['url'] = original
            cdx['mem_rel'] = val.get('rel', '')
            cdx['memento_url'] = val['url']

            load_url = self.replay_url.format(timestamp=cdx['timestamp'],
                                              url=original)

            cdx['load_url'] = load_url
            yield cdx

    def get_timegate_links(self, params, closest):
        url = res_template(self.timegate_url, params)
        accept_dt = timestamp_to_http_date(closest)
        res = requests.head(url, headers={'Accept-Datetime': accept_dt})
        if res.status_code >= 400:
            raise NotFoundException(url)

        links = res.headers.get('Link')

        if not links:
            raise NotFoundException(url)

        return links

    def get_timemap_links(self, params):
        url = res_template(self.timemap_url, params)
        res = requests.get(url, timeout=params.get('_timeout'))
        if res.status_code >= 400 or not res.text:
            raise NotFoundException(url)

        return res.text

    def load_index(self, params):
        closest = params.get('closest')

        if not closest:
            links = self.get_timemap_links(params)
            def_name = 'timemap'
        else:
            links = self.get_timegate_links(params, closest)
            def_name = 'timegate'

        return self.links_to_cdxobject(links, def_name)

    @classmethod
    def from_timegate_url(cls, timegate_url, path='link'):
        return cls(timegate_url + '{url}',
                   timegate_url + 'timemap/' + path + '/{url}',
                   timegate_url + WAYBACK_ORIG_SUFFIX)

    def __repr__(self):
        return '{0}({1}, {2}, {3})'.format(self.__class__.__name__,
                                           self.timegate_url,
                                           self.timemap_url,
                                           self.replay_url)

    def __str__(self):
        return 'memento'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.timegate_url == other.timegate_url and
                self.timemap_url == other.timemap_url and
                self.replay_url == other.replay_url)

    @classmethod
    def init_from_string(cls, value):
        if value.startswith('memento+'):
            return cls.from_timegate_url(value[8:], 'link')

        # default to memento for any http url
        if value.startswith(('http://', 'https://')):
            return cls.from_timegate_url(value, 'link')


    @classmethod
    def init_from_config(cls, config):
        if config['type'] != 'memento':
            return

        return cls(config['timegate_url'],
                   config['timemap_url'],
                   config['replay_url'])

