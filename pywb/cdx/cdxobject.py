from collections import OrderedDict
import itertools

from urllib import urlencode
from urlparse import parse_qs


#=================================================================
class CDXException(Exception):
    def status(self):
        return '400 Bad Request'


#=================================================================
class CaptureNotFoundException(CDXException):
    def status(self):
        return '404 Not Found'


#=================================================================
class AccessException(CDXException):
    def status(self):
        return '403 Access Denied'


#=================================================================
class CDXQuery(object):
    def __init__(self, **kwargs):
        self.params = kwargs

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
        return v.split(',') if v else None

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
    def secondary_index_only(self):
        return self._get_bool('showPagedIndex')

    @property
    def process(self):
        return self._get_bool('processOps', True)

    def set_process(self, process):
        self.params['processOps'] = process

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

    @staticmethod
    def from_wsgi_env(env):
        """ utility function to extract params and create a CDXQuery
        from a WSGI environment dictionary
        """
        params = parse_qs(env['QUERY_STRING'])

        if not 'output' in params:
            params['output'] = 'text'

        # parse_qs produces arrays for single values
        # cdx processing expects singleton params for all params,
        # except filters, so convert here
        # use first value of the list
        for name, val in params.iteritems():
            if name != 'filter':
                params[name] = val[0]

        return CDXQuery(**params)


#=================================================================
class CDXObject(OrderedDict):
    CDX_FORMATS = [
        # Public CDX Format
        ["urlkey", "timestamp", "original", "mimetype", "statuscode",
         "digest", "length"],

        # CDX 11 Format
        ["urlkey", "timestamp", "original", "mimetype", "statuscode",
         "digest", "redirect", "robotflags", "length", "offset", "filename"],

        # CDX 9 Format
        ["urlkey", "timestamp", "original", "mimetype", "statuscode",
         "digest", "redirect", "offset", "filename"],

        # CDX 11 Format + 3 revisit resolve fields
        ["urlkey", "timestamp", "original", "mimetype", "statuscode",
         "digest", "redirect", "robotflags", "length", "offset", "filename",
         "orig.length", "orig.offset", "orig.filename"],

        # CDX 9 Format + 3 revisit resolve fields
        ["urlkey", "timestamp", "original", "mimetype", "statuscode",
         "digest", "redirect", "offset", "filename",
         "orig.length", "orig.offset", "orig.filename"]
        ]

    def __init__(self, cdxline):
        OrderedDict.__init__(self)

        cdxline = cdxline.rstrip()
        fields = cdxline.split(' ')

        cdxformat = None
        for i in self.CDX_FORMATS:
            if len(i) == len(fields):
                cdxformat = i

        if not cdxformat:
            raise Exception('unknown {0}-field cdx format'.format(len(fields)))

        for header, field in itertools.izip(cdxformat, fields):
            self[header] = field

        self.cdxline = cdxline

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)

        # force regen on next __str__ call
        self.cdxline = None

    def is_revisit(self):
        return (self['mimetype'] == 'warc/revisit' or
                self['filename'] == '-')

    def to_text(self, fields=None):
        """
        return plaintext CDX record (includes newline).
        :param fields: list of field names to output.
        """
        if fields is None:
            return str(self) + '\n'
        else:
            return ' '.join(self[x] for x in fields) + '\n'

    def __str__(self):
        if self.cdxline:
            return self.cdxline

        return ' '.join(val for n, val in self.iteritems())


#=================================================================
class IDXObject(OrderedDict):

    FORMAT = ['urlkey', 'part', 'offset', 'length', 'lineno']
    NUM_REQ_FIELDS = len(FORMAT) - 1  # lineno is an optional field

    def __init__(self, idxline):
        OrderedDict.__init__(self)

        idxline = idxline.rstrip()
        fields = idxline.split('\t')

        if len(fields) < self.NUM_REQ_FIELDS:
            msg = 'invalid idx format: {0} fields found, {1} required'
            raise Exception(msg.format(len(fields), self.NUM_REQ_FIELDS))

        for header, field in itertools.izip(self.FORMAT, fields):
            self[header] = field

        self['offset'] = int(self['offset'])
        self['length'] = int(self['length'])
        lineno = self.get('lineno')
        if lineno:
            self['lineno'] = int(lineno)

        self.idxline = idxline

    def to_text(self, fields=None):
        """
        return plaintext IDX record (including newline).
        :param fields: list of field names to output (currently ignored)
        """
        return str(self) + '\n'

    def __str__(self):
        return self.idxline
