from pywb.utils.canonicalize import calc_search_range
from pywb.cdx.cdxobject import CDXObject
from pywb.warc.cdxindexer import write_cdx_index
from pywb.utils.timeutils import iso_date_to_timestamp

from io import BytesIO
import os

from webagg.indexsource import RedisIndexSource
from webagg.aggregator import SimpleAggregator
from webagg.utils import res_template

from recorder.filters import WriteRevisitDupePolicy


#==============================================================================
class WritableRedisIndexer(RedisIndexSource):
    def __init__(self, redis_url, rel_path_template='',
                 file_key_template='', name='recorder',
                 dupe_policy=WriteRevisitDupePolicy()):
        super(WritableRedisIndexer, self).__init__(redis_url)
        self.cdx_lookup = SimpleAggregator({name: self})
        self.rel_path_template = rel_path_template
        self.file_key_template = file_key_template
        self.dupe_policy = dupe_policy

    def add_warc_file(self, full_filename, params):
        rel_path = res_template(self.rel_path_template, params)
        filename = os.path.relpath(full_filename, rel_path)

        file_key = res_template(self.file_key_template, params)

        self.redis.hset(file_key, filename, full_filename)

    def add_urls_to_index(self, stream, params, filename=None):
        rel_path = res_template(self.rel_path_template, params)
        filename = os.path.relpath(filename, rel_path)

        cdxout = BytesIO()
        write_cdx_index(cdxout, stream, filename,
                        cdxj=True, append_post=True)

        z_key = res_template(self.redis_key_template, params)

        cdxes = cdxout.getvalue()
        for cdx in cdxes.split(b'\n'):
            if cdx:
                self.redis.zadd(z_key, 0, cdx)

        return cdx

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
            res = self.dupe_policy(cdx)
            if res:
                return res

        return None
