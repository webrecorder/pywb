from pywb.utils.canonicalize import calc_search_range
from pywb.cdx.cdxobject import CDXObject
from pywb.warc.cdxindexer import write_cdx_index

from warcio.timeutils import iso_date_to_timestamp

from io import BytesIO
import os

from pywb.webagg.indexsource import RedisIndexSource
from pywb.webagg.aggregator import SimpleAggregator
from pywb.webagg.utils import res_template

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

    def add_warc_file(self, full_filename, params):
        rel_path = res_template(self.rel_path_template, params)
        rel_filename = os.path.relpath(full_filename, rel_path)

        file_key = res_template(self.file_key_template, params)

        full_load_path = self.full_warc_prefix + full_filename

        self.redis.hset(file_key, rel_filename, full_load_path)

    def add_urls_to_index(self, stream, params, filename, length):
        rel_path = res_template(self.rel_path_template, params)
        filename = os.path.relpath(filename, rel_path)

        cdxout = BytesIO()
        write_cdx_index(cdxout, stream, filename,
                        cdxj=True, append_post=True)

        z_key = res_template(self.redis_key_template, params)

        cdx_list = cdxout.getvalue().rstrip().split(b'\n')

        for cdx in cdx_list:
            if cdx:
                self.redis.zadd(z_key, 0, cdx)

        return cdx_list

    def lookup_revisit(self, params, digest, url, iso_dt):
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
