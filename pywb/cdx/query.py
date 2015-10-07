from urllib import urlencode
from cdxobject import CDXException


#=================================================================
class CDXQuery(object):
    def __init__(self, **kwargs):
        self.params = kwargs
        if not self.params.get('matchType'):
            url = self.params.get('url', '')
            if url.startswith('*.'):
                self.params['url'] = url[2:]
                self.params['matchType'] = 'domain'
            elif url.endswith('*'):
                self.params['url'] = url[:-1]
                self.params['matchType'] = 'prefix'

    @property
    def key(self):
        return self.params['key']

    @property
    def end_key(self):
        return self.params['end_key']

    def set_key(self, key, end_key):
        self.params['key'] = key
        self.params['end_key'] = end_key

    @property
    def url(self):
        try:
            return self.params['url']
        except KeyError:
            msg = 'A url= param must be specified to query the cdx server'
            raise CDXException(msg)

    @property
    def match_type(self):
        return self.params.get('matchType', 'exact')

    @property
    def is_exact(self):
        return self.match_type == 'exact'

    @property
    def allow_fuzzy(self):
        return self._get_bool('allowFuzzy')

    @property
    def output(self):
        return self.params.get('output', 'text')

    @property
    def limit(self):
        return int(self.params.get('limit', 100000))

    @property
    def collapse_time(self):
        return self.params.get('collapseTime')

    @property
    def resolve_revisits(self):
        return self._get_bool('resolveRevisits')

    @property
    def filters(self):
        return self.params.get('filter', [])

    @property
    def fields(self):
        v = self.params.get('fields')
        # check old param name
        if not v:
            v = self.params.get('fl')
        return v.split(',') if v else None

    @property
    def from_ts(self):
        return self.params.get('from') or self.params.get('from_ts')

    @property
    def to_ts(self):
        return self.params.get('to')

    @property
    def closest(self):
        # sort=closest is not required
        return self.params.get('closest')

    @property
    def reverse(self):
        # sort=reverse overrides reverse=0
        return (self._get_bool('reverse') or
                self.params.get('sort') == 'reverse')

    @property
    def custom_ops(self):
        return self.params.get('custom_ops', [])

    @property
    def secondary_index_only(self):
        return self._get_bool('showPagedIndex')

    @property
    def page(self):
        return int(self.params.get('page', 0))

    @property
    def page_size(self):
        return self.params.get('pageSize')

    @property
    def page_count(self):
        return self._get_bool('showNumPages')

    def _get_bool(self, name, def_val=False):
        v = self.params.get(name)
        if v:
            try:
                v = int(v)
            except ValueError as ex:
                v = (v.lower() == 'true')
        else:
            v = def_val

        return bool(v)

    def urlencode(self):
        return urlencode(self.params, True)
