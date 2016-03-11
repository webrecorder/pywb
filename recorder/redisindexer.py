from pywb.utils.canonicalize import calc_search_range
from pywb.cdx.cdxobject import CDXObject
from pywb.warc.cdxindexer import write_cdx_index
from pywb.utils.timeutils import timestamp_to_datetime
from pywb.utils.timeutils import datetime_to_iso_date, iso_date_to_timestamp

from io import BytesIO
import os

from webagg.indexsource import RedisIndexSource
from webagg.aggregator import SimpleAggregator
from webagg.utils import res_template


#==============================================================================
class WritableRedisIndexer(RedisIndexSource):
    def __init__(self, redis_url, rel_path_template='', name='recorder'):
        super(WritableRedisIndexer, self).__init__(redis_url)
        self.cdx_lookup = SimpleAggregator({name: self})
        self.rel_path_template = rel_path_template

    def add_record(self, stream, params, filename=None):
        if not filename and hasattr(stream, 'name'):
            filename = stream.name

        rel_path = res_template(self.rel_path_template, params)
        filename = os.path.relpath(filename, rel_path)

        cdxout = BytesIO()
        write_cdx_index(cdxout, stream, filename,
                        cdxj=True, append_post=True, rel_root=rel_path)

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
            dt = timestamp_to_datetime(cdx['timestamp'])
            return ('revisit', cdx['url'],
                    datetime_to_iso_date(dt))

        return None
