import redis

from pywb.utils.binsearch import iter_range
from pywb.utils.timeutils import timestamp_to_http_date, http_date_to_timestamp
from pywb.utils.timeutils import timestamp_to_sec, timestamp_now
from pywb.utils.canonicalize import calc_search_range

from pywb.cdx.cdxobject import CDXObject
from pywb.cdx.cdxops import cdx_sort_closest, cdx_limit

import requests

from utils import MementoUtils


#=============================================================================
class BaseIndexSource(object):
    def __init__(self, index_template=''):
        self.index_template = index_template

    def get_index(self, params):
        return self.index_template.format(params.get('coll'))


#=============================================================================
class FileIndexSource(BaseIndexSource):
    def load_index(self, params):
        filename = self.get_index(params)

        with open(filename, 'rb') as fh:
            gen = iter_range(fh, params['start_key'], params['end_key'])
            for line in gen:
                yield CDXObject(line)


#=============================================================================
class RemoteIndexSource(BaseIndexSource):
    def __init__(self, cdx_url, replay_url):
        self.index_template = cdx_url
        self.replay_url = replay_url

    def load_index(self, params):
        url = self.get_index(params)
        url += '?url=' + params['url']
        r = requests.get(url)
        lines = r.content.strip().split(b'\n')
        for line in lines:
            cdx = CDXObject(line)
            cdx['load_url'] = self.replay_url.format(timestamp=cdx['timestamp'], url=cdx['url'])
            yield cdx


#=============================================================================
class LiveIndexSource(BaseIndexSource):
    def load_index(self, params):
        cdx = CDXObject()
        cdx['urlkey'] = params.get('start_key').decode('utf-8')
        cdx['timestamp'] = timestamp_now()
        cdx['url'] = params['url']
        cdx['load_url'] = params['url']
        def live():
            yield cdx

        return live()


#=============================================================================
class RedisIndexSource(BaseIndexSource):
    def __init__(self, redis_url):
        parts = redis_url.split('/')
        key_prefix = ''
        if len(parts) > 4:
            key_prefix = parts[4]
            redis_url = 'redis://' + parts[2] + '/' + parts[3]

        self.redis_url = redis_url
        self.index_template = key_prefix
        self.redis = redis.StrictRedis.from_url(redis_url)

    def load_index(self, params):
        z_key = self.get_index(params)
        index_list = self.redis.zrangebylex(z_key,
                                            b'[' + params['start_key'],
                                            b'(' + params['end_key'])

        for line in index_list:
            yield CDXObject(line)


#=============================================================================
class MementoIndexSource(BaseIndexSource):
    def __init__(self, timegate_url, timemap_url, replay_url):
        self.timegate_url = timegate_url
        self.timemap_url = timemap_url
        self.replay_url = replay_url

    def make_iter(self, links, def_name):
        original, link_iter = MementoUtils.links_to_json(links, def_name)

        for cdx in link_iter():
            cdx['load_url'] = self.replay_url.format(timestamp=cdx['timestamp'], url=original)
            yield cdx

    def load_timegate(self, params, closest):
        url = self.timegate_url.format(coll=params.get('coll')) + params['url']
        accept_dt = timestamp_to_http_date(closest)
        res = requests.head(url, headers={'Accept-Datetime': accept_dt})
        return self.make_iter(res.headers.get('Link'), 'timegate')

    def load_timemap(self, params):
        url = self.timemap_url + params['url']
        r = requests.get(url)
        return self.make_iter(r.text, 'timemap')

    def load_index(self, params):
        closest = params.get('closest')
        if not closest:
            return self.load_timemap(params)
        else:
            return self.load_timegate(params, closest)

    @staticmethod
    def from_timegate_url(timegate_url, type_='link'):
        return MementoIndexSource(timegate_url,
                                  timegate_url + 'timemap/' + type_ + '/',
                                  timegate_url + '{timestamp}id_/{url}')



def query_index(source, params):
    url = params.get('url', '')

    if not params.get('matchType'):
        if url.startswith('*.'):
            params['url'] = url[2:]
            params['matchType'] = 'domain'
        elif url.endswith('*'):
            params['url'] = url[:-1]
            params['matchType'] = 'prefix'
        else:
            params['matchType'] = 'exact'

    start, end = calc_search_range(url=params['url'],
                                   match_type=params['matchType'])

    params['start_key'] = start.encode('utf-8')
    params['end_key'] = end.encode('utf-8')

    res = source.load_index(params)

    limit = int(params.get('limit', 10))
    closest = params.get('closest')
    if closest:
        res = cdx_sort_closest(closest, res, limit)
    elif limit:
        res = cdx_limit(res, limit)


    return res
