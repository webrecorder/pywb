from warcio.timeutils import iso_date_to_timestamp

from io import BytesIO
import os
import tempfile

from pywb.utils.canonicalize import calc_search_range
from pywb.utils.format import res_template

from pywb.indexer.cdxindexer import write_cdx_index

from pywb.warcserver.index.cdxobject import CDXObject
from pywb.warcserver.index.indexsource import RedisIndexSource
from pywb.warcserver.index.aggregator import SimpleAggregator

from pywb.recorder.filters import WriteRevisitDupePolicy


#==============================================================================
class WritableRedisIndexer(RedisIndexSource):
    def __init__(self, *args, **kwargs):
        redis_url = kwargs.get('redis_url')
        redis = kwargs.get('redis')
        cdx_key_template = kwargs.get('cdx_key_template')

        super(WritableRedisIndexer, self).__init__(redis_url,
                                                   redis,
                                                   cdx_key_template)

        name = kwargs.get('name', 'recorder')
        self.cdx_lookup = SimpleAggregator({name: self})

        self.rel_path_template = kwargs.get('rel_path_template', '')
        self.file_key_template = kwargs.get('file_key_template', '')
        self.full_warc_prefix = kwargs.get('full_warc_prefix', '')
        self.dupe_policy = kwargs.get('dupe_policy', WriteRevisitDupePolicy())

    def _get_rel_or_base_name(self, filename, params):
        rel_path = res_template(self.rel_path_template, params)
        try:
            base_name = os.path.relpath(filename, rel_path)
            assert '..' not in base_name
        except Exception:
            base_name = None

        if not base_name:
            base_name = os.path.basename(filename)

        return base_name

    def add_warc_file(self, full_filename, params):
        file_key = res_template(self.file_key_template, params)
        if not file_key:
            return

        base_filename = self._get_rel_or_base_name(full_filename, params)
        full_load_path = self.full_warc_prefix + full_filename

        self.redis.hset(file_key, base_filename, full_load_path)

    def add_urls_to_index(self, stream, params, filename, length):
        base_filename = self._get_rel_or_base_name(filename, params)

        cdxout = BytesIO()
        write_cdx_index(cdxout, stream, base_filename,
                        cdxj=True, append_post=True,
                        writer_cls=params.get('writer_cls'))

        z_key = res_template(self.redis_key_template, params)

        cdx_list = cdxout.getvalue().rstrip().split(b'\n')

        for cdx in cdx_list:
            if cdx:
                self.redis.zadd(z_key, 0, cdx)

        return cdx_list

    def lookup_revisit(self, lookup_params, digest, url, iso_dt):
        params = {}
        for param in lookup_params:
            if param.startswith('param.'):
                params[param] = lookup_params[param]

        params['url'] = url
        params['closest'] = iso_date_to_timestamp(iso_dt)

        filters = []

        filters.append('!mime:warc/revisit')

        if digest and digest != '-':
            filters.append('digest:' + digest.split(':')[-1])

        params['filter'] = filters

        cdx_iter, errs = self.cdx_lookup(params)

        for cdx in cdx_iter:
            res = self.dupe_policy(cdx, params)
            if res:
                return res

        return None


# ============================================================================
class RedisPendingCounterTempBuffer(tempfile.SpooledTemporaryFile):
    def __init__(self, max_size, redis_url, params, name, timeout=30):
        redis_url = res_template(redis_url, params)
        super(RedisPendingCounterTempBuffer, self).__init__(max_size=max_size)
        self.redis, self.key = RedisIndexSource.parse_redis_url(redis_url)
        self.timeout = timeout

        self.redis.incrby(self.key, 1)
        self.redis.expire(self.key, self.timeout)

    def write(self, buf):
        super(RedisPendingCounterTempBuffer, self).write(buf)
        self.redis.expire(self.key, self.timeout)

    def close(self):
        try:
            super(RedisPendingCounterTempBuffer, self).close()
        except:
            traceback.print_exc()

        self.redis.incrby(self.key, -1)
        self.redis.expire(self.key, self.timeout)

