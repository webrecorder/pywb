import redis

from pywb.utils.binsearch import iter_range
from pywb.utils.timeutils import timestamp_to_http_date, http_date_to_timestamp
from pywb.utils.timeutils import timestamp_to_sec, timestamp_now
from pywb.utils.canonicalize import canonicalize, calc_search_range
from pywb.utils.wbexception import NotFoundException

from pywb.cdx.cdxobject import CDXObject
from pywb.cdx.query import CDXQuery

from webagg.liverec import patched_requests as requests

from webagg.utils import ParamFormatter, res_template
from webagg.utils import MementoUtils


WAYBACK_ORIG_SUFFIX = '{timestamp}id_/{url}'


#=============================================================================
class BaseIndexSource(object):
    def load_index(self, params):  #pragma: no cover
        raise NotImplemented()


#=============================================================================
class FileIndexSource(BaseIndexSource):
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

    def __str__(self):
        return 'file'


#=============================================================================
class RemoteIndexSource(BaseIndexSource):
    def __init__(self, api_url, replay_url, url_field='load_url'):
        self.api_url_template = api_url
        self.replay_url = replay_url
        self.url_field = url_field

    def load_index(self, params):
        api_url = res_template(self.api_url_template, params)
        r = requests.get(api_url, timeout=params.get('_timeout'))
        if r.status_code >= 400:
            raise NotFoundException(api_url)

        lines = r.content.strip().split(b'\n')
        def do_load(lines):
            for line in lines:
                cdx = CDXObject(line)
                self._set_load_url(cdx)
                yield cdx

        return do_load(lines)

    def _set_load_url(self, cdx):
        cdx[self.url_field] = self.replay_url.format(
                                 timestamp=cdx['timestamp'],
                                 url=cdx['url'])

    def __str__(self):
        return 'remote'


#=============================================================================
class UpstreamAggIndexSource(RemoteIndexSource):
    def __init__(self, base_url):
        api_url = base_url + '/index?url={url}'
        proxy_url = base_url + '/resource?url={url}&closest={timestamp}'
        super(UpstreamAggIndexSource, self).__init__(api_url, proxy_url, 'filename')

    def _set_load_url(self, cdx):
        super(UpstreamAggIndexSource, self)._set_load_url(cdx)
        cdx['offset'] = '0'
        cdx.pop('load_url', '')


#=============================================================================
class LiveIndexSource(BaseIndexSource):
    def load_index(self, params):
        cdx = CDXObject()
        cdx['urlkey'] = params.get('key').decode('utf-8')
        cdx['timestamp'] = timestamp_now()
        cdx['url'] = params['url']
        cdx['load_url'] = params['url']
        cdx['is_live'] = 'true'
        def live():
            yield cdx

        return live()

    def __str__(self):
        return 'live'


#=============================================================================
class RedisIndexSource(BaseIndexSource):
    def __init__(self, redis_url):
        parts = redis_url.split('/')
        key_prefix = ''
        if len(parts) > 4:
            key_prefix = parts[4]
            redis_url = 'redis://' + parts[2] + '/' + parts[3]

        self.redis_url = redis_url
        self.redis_key_template = key_prefix
        self.redis = redis.StrictRedis.from_url(redis_url)

    def load_index(self, params):
        z_key = res_template(self.redis_key_template, params)
        index_list = self.redis.zrangebylex(z_key,
                                            b'[' + params['key'],
                                            b'(' + params['end_key'])

        def do_load(index_list):
            for line in index_list:
                yield CDXObject(line)

        return do_load(index_list)

    def __str__(self):
        return 'redis'


#=============================================================================
class MementoIndexSource(BaseIndexSource):
    def __init__(self, timegate_url, timemap_url, replay_url):
        self.timegate_url = timegate_url
        self.timemap_url = timemap_url
        self.replay_url = replay_url

    def links_to_cdxobject(self, link_header, def_name):
        results = MementoUtils.parse_links(link_header, def_name)

        #meta = MementoUtils.meta_field('timegate', results)
        #if meta:
        #    yield meta

        #meta = MementoUtils.meta_field('timemap', results)
        #if meta:
        #    yield meta

        #meta = MementoUtils.meta_field('original', results)
        #if meta:
        #    yield meta

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

        return res.headers.get('Link')

    def get_timemap_links(self, params):
        url = res_template(self.timemap_url, params)
        res = requests.get(url, timeout=params.get('_timeout'))
        if res.status_code >= 400:
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

    @staticmethod
    def from_timegate_url(timegate_url, path='link'):
        return MementoIndexSource(timegate_url + '{url}',
                                  timegate_url + 'timemap/' + path + '/{url}',
                                  timegate_url + WAYBACK_ORIG_SUFFIX)

    def __str__(self):
        return 'memento'


