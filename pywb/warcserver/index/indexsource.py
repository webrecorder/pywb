from pywb.utils.binsearch import iter_range
from pywb.utils.canonicalize import canonicalize
from pywb.utils.wbexception import NotFoundException

from warcio.timeutils import timestamp_to_http_date, http_date_to_timestamp
from warcio.timeutils import timestamp_now, pad_timestamp, PAD_14_DOWN

from pywb.warcserver.http import DefaultAdapters
from pywb.warcserver.index.cdxobject import CDXObject

from pywb.utils.format import ParamFormatter, res_template
from pywb.utils.memento import MementoUtils

import redis

import requests

import re
import logging


#=============================================================================
class BaseIndexSource(object):
    WAYBACK_ORIG_SUFFIX = '{timestamp}id_/{url}'

    logger = logging.getLogger('warcserver')

    def load_index(self, params):  #pragma: no cover
        raise NotImplemented()

    def _get_referrer(self, params):
        input_req = params.get('_input_req')
        if input_req:
            return input_req.get_referrer()
        else:
            return None

    def _init_sesh(self, adapter=None):
        if not adapter:
            adapter = DefaultAdapters.remote_adapter
        self.sesh = requests.Session()
        self.sesh.mount('http://', adapter)
        self.sesh.mount('https://', adapter)


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
        self._init_sesh()

    def _get_api_url(self, params):
        api_url = res_template(self.api_url, params)
        if 'closest' in params and self.closest_limit:
            api_url += '&limit=' + str(self.closest_limit)

        return api_url

    def load_index(self, params):
        api_url = self._get_api_url(params)
        try:
            r = self.sesh.get(api_url, timeout=params.get('_timeout'))
            r.raise_for_status()
        except Exception as e:
            self.logger.debug('FAILED: ' + str(e))
            raise NotFoundException(api_url)

        lines = r.content.strip().split(b'\n')
        def do_load(lines):
            for line in lines:
                if not line:
                    continue

                cdx = CDXObject(line)
                self._set_load_url(cdx, params)
                yield cdx

        return do_load(lines)

    def _set_load_url(self, cdx, params):
        source_coll = ''
        name = params.get('_name')
        if name:
            source_coll = params.get('param.' + name + '.src_coll', '')

        cdx[self.url_field] = self.replay_url.format(url=cdx['url'],
                                                     timestamp=cdx['timestamp'],
                                                     src_coll=source_coll)
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
            replay = url[:-4] + '/' + cls.WAYBACK_ORIG_SUFFIX
        else:
        # add specified coll, if any
            replay = url.rsplit('/', 1)[0] + coll + '/' + cls.WAYBACK_ORIG_SUFFIX

        url += '?url={url}&closest={closest}&sort=closest'

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
        self._init_sesh(DefaultAdapters.live_adapter)

    def load_index(self, params):
        # no fuzzy match for live resources
        if params.get('is_fuzzy'):
            raise NotFoundException(params['url'] + '*')

        cdx = CDXObject()
        cdx['urlkey'] = params.get('key').decode('utf-8')
        cdx['timestamp'] = timestamp_now()
        cdx['url'] = params['url']
        cdx['load_url'] = res_template(self.proxy_url, params)
        cdx['is_live'] = 'true'

        mime = params.get('content_type', '')

        if params.get('filter') and not mime:
            try:
                res = self.sesh.head(cdx['url'])
                if res.status_code != 405:
                    cdx['status'] = str(res.status_code)

                content_type = res.headers.get('Content-Type')
                if content_type:
                    mime = content_type.split(';')[0]

            except Exception as e:
                pass

        cdx['mime'] = mime

        return iter([cdx])

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

        self.member_key_type = None

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

        scan_key = 'scan:' + key
        # check if already have keys to avoid extra redis call
        keys = params.get(scan_key)
        if not keys:
            keys = self._load_key_set(key)
            params[scan_key] = keys

        match_templ = match_templ.encode('utf-8')

        return [match_templ.replace(b'*', key) for key in keys]

    def _load_key_set(self, key):
        if not self.member_key_type:
            self.member_key_type = self.redis.type(key)

        if self.member_key_type == b'set':
            return self.redis.smembers(key)

        elif self.member_key_type == b'hash':
            return self.redis.hvals(key)

        # don't cache if any other type
        else:
            self.member_key_type = None

        return []

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
        self._init_sesh()

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

            load_url = self._get_replay_url(cdx['timestamp'], original)

            cdx['load_url'] = load_url
            yield cdx

    def _get_replay_url(self, ts, url):
        return self.replay_url.format(url=url, timestamp=ts)

    def handle_timegate(self, params, timestamp):
        links = self.get_timegate_links(params, timestamp)
        return self.links_to_cdxobject(links, 'timegate')

    def get_timegate_links(self, params, timestamp):
        url = res_template(self.timegate_url, params)
        accept_dt = timestamp_to_http_date(timestamp)
        try:
            headers = self._get_headers(params)
            headers['Accept-Datetime'] = accept_dt
            res = self.sesh.head(url, headers=headers)
            res.raise_for_status()
        except Exception as e:
            self.logger.debug('FAILED: ' + str(e))
            raise NotFoundException(url)

        links = res.headers.get('Link')

        if not links:
            raise NotFoundException(url)

        return links

    def _get_headers(self, params):
        return {}

    def handle_timemap(self, params):
        url = res_template(self.timemap_url, params)
        headers = self._get_headers(params)
        try:
            res = self.sesh.get(url,
                                headers=headers,
                                timeout=params.get('_timeout'))

            res.raise_for_status()
            assert(res.text)

        except Exception as e:
            self.logger.debug('FAILED: ' + str(e))
            raise NotFoundException(url)

        links = res.text
        return self.links_to_cdxobject(links, 'timemap')

    def load_index(self, params):
        timestamp = params.get('closest')

        # can't do fuzzy matching via memento
        if params.get('is_fuzzy'):
            raise NotFoundException(params['url'] + '*')

        if not timestamp:
            return self.handle_timemap(params)
        else:
            return self.handle_timegate(params, timestamp)

    @classmethod
    def from_timegate_url(cls, timegate_url, path='link'):
        return cls(timegate_url + '{url}',
                   timegate_url + 'timemap/' + path + '/{url}',
                   timegate_url + cls.WAYBACK_ORIG_SUFFIX)

    def __repr__(self):
        return '{0}({1}, {2}, {3})'.format(self.__class__.__name__,
                                           self.timegate_url,
                                           self.timemap_url,
                                           self.replay_url)

    @classmethod
    def _init_id(cls):
        return 'memento'

    def __str__(self):
        return self._init_id()

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.timegate_url == other.timegate_url and
                self.timemap_url == other.timemap_url and
                self.replay_url == other.replay_url)

    @classmethod
    def init_from_string(cls, value):
        key = cls._init_id() + '+'
        if value.startswith(key):
            return cls.from_timegate_url(value[len(key):], 'link')

        # default to memento for any http url
        if value.startswith(('http://', 'https://')):
            return cls.from_timegate_url(value, 'link')


    @classmethod
    def init_from_config(cls, config):
        if config['type'] != cls._init_id():
            return

        return cls(config['timegate_url'],
                   config['timemap_url'],
                   config['replay_url'])


#=============================================================================
class WBMementoIndexSource(MementoIndexSource):
    WBURL_MATCH = re.compile('([0-9]{0,14})?(?:\w+_)?/{0,3}(.*)')
    WAYBACK_ORIG_SUFFIX = '{timestamp}im_/{url}'

    def __init__(self, timegate_url, timemap_url, replay_url):
        super(WBMementoIndexSource, self).__init__(timegate_url, timemap_url, replay_url)
        self.prefix = replay_url.split('{', 1)[0]

    def _get_referrer(self, params):
        ref_url = super(WBMementoIndexSource, self)._get_referrer(params)
        if ref_url:
            timestamp = params.get('closest', '20')
            timestamp = pad_timestamp(timestamp, PAD_14_DOWN)
            ref_url = self._get_replay_url(timestamp, ref_url)
            ref_url = ref_url.replace('im_/', '/')

        return ref_url

    def _get_headers(self, params):
        headers = super(WBMementoIndexSource, self)._get_headers(params)
        ref_url = self._get_referrer(params)
        if ref_url:
            headers['Referer'] = ref_url
        return headers

    def _extract_location(self, url, location):
        if not location or not location.startswith(self.prefix):
            raise NotFoundException(url)

        m = self.WBURL_MATCH.search(location[len(self.prefix):])
        if not m:
            raise NotFoundException(url)

        url = m.group(2)
        timestamp = m.group(1)
        location = self._get_replay_url(timestamp, url)
        return url, timestamp, location

    def handle_timegate(self, params, timestamp):
        url = params['url']
        load_url = self.timegate_url.format(url=url, timestamp=timestamp)

        try:
            headers = self._get_headers(params)
            res = self.sesh.head(load_url, headers=headers)
        except Exception as e:
            raise NotFoundException(url)

        if res and res.headers.get('Memento-Datetime'):
            if res.status_code >= 400:
                raise NotFoundException(url)

            if res.status_code >= 300:
                info = self._extract_location(url, res.headers.get('Location'))
            else:
                info = self._extract_location(url, res.headers.get('Content-Location'))

            url, timestamp, load_url = info

        cdx = CDXObject()
        cdx['urlkey'] = canonicalize(url)
        cdx['timestamp'] = timestamp
        cdx['url'] = url
        cdx['load_url'] = load_url

        if 'Referer' in headers:
            cdx['set_referrer'] = headers['Referer']

        return iter([cdx])

    @classmethod
    def _init_id(cls):
        return 'wb-memento'
