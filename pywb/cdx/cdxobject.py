try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict

import six
from six.moves import zip

from six.moves.urllib.parse import urlencode, quote
from six.moves.urllib.parse import parse_qs

from pywb.utils.wbexception import WbException
from pywb.utils.loaders import to_native_str

from json import loads as json_decode
from json import dumps as json_encode


#=================================================================
URLKEY = 'urlkey'
TIMESTAMP = 'timestamp'
ORIGINAL = 'url'
MIMETYPE = 'mime'
STATUSCODE = 'status'
DIGEST = 'digest'
REDIRECT = 'redirect'
ROBOTFLAGS = 'robotflags'
LENGTH = 'length'
OFFSET = 'offset'
FILENAME = 'filename'

ORIG_LENGTH = 'orig.length'
ORIG_OFFSET = 'orig.offset'
ORIG_FILENAME = 'orig.filename'


#=================================================================
class CDXException(WbException):
    def status(self):
        return '400 Bad Request'


#=================================================================
class CDXObject(OrderedDict):
    """
    dictionary object representing parsed CDX line.
    """
    CDX_FORMATS = [
        # Public CDX Format
        [URLKEY, TIMESTAMP, ORIGINAL, MIMETYPE, STATUSCODE,
         DIGEST, LENGTH],

        # CDX 11 Format
        [URLKEY, TIMESTAMP, ORIGINAL, MIMETYPE, STATUSCODE,
         DIGEST, REDIRECT, ROBOTFLAGS, LENGTH, OFFSET, FILENAME],

        # CDX 10 Format
        [URLKEY, TIMESTAMP, ORIGINAL, MIMETYPE, STATUSCODE,
         DIGEST, REDIRECT, ROBOTFLAGS, OFFSET, FILENAME],

        # CDX 9 Format
        [URLKEY, TIMESTAMP, ORIGINAL, MIMETYPE, STATUSCODE,
         DIGEST, REDIRECT, OFFSET, FILENAME],

        # CDX 11 Format + 3 revisit resolve fields
        [URLKEY, TIMESTAMP, ORIGINAL, MIMETYPE, STATUSCODE,
         DIGEST, REDIRECT, ROBOTFLAGS, LENGTH, OFFSET, FILENAME,
         ORIG_LENGTH, ORIG_OFFSET, ORIG_FILENAME],

        # CDX 10 Format + 3 revisit resolve fields
        [URLKEY, TIMESTAMP, ORIGINAL, MIMETYPE, STATUSCODE,
         DIGEST, REDIRECT, ROBOTFLAGS, OFFSET, FILENAME,
         ORIG_LENGTH, ORIG_OFFSET, ORIG_FILENAME],

        # CDX 9 Format + 3 revisit resolve fields
        [URLKEY, TIMESTAMP, ORIGINAL, MIMETYPE, STATUSCODE,
         DIGEST, REDIRECT, OFFSET, FILENAME,
         ORIG_LENGTH, ORIG_OFFSET, ORIG_FILENAME],
    ]


    CDX_ALT_FIELDS = {
                  'u': ORIGINAL,
                  'original': ORIGINAL,

                  'statuscode': STATUSCODE,
                  's': STATUSCODE,

                  'mimetype': MIMETYPE,
                  'm': MIMETYPE,

                  'l': LENGTH,
                  's': LENGTH,

                  'o': OFFSET,

                  'd': DIGEST,

                  't': TIMESTAMP,

                  'k': URLKEY,

                  'f': FILENAME
    }

    def __init__(self, cdxline=b''):
        OrderedDict.__init__(self)

        cdxline = cdxline.rstrip()
        self._from_json = False
        self._cached_json = None

        # Allows for filling the fields later or in a custom way
        if not cdxline:
            self.cdxline = cdxline
            return

        fields = cdxline.split(b' ' , 2)
        # Check for CDX JSON
        if fields[-1].startswith(b'{'):
            self[URLKEY] = to_native_str(fields[0], 'utf-8')
            self[TIMESTAMP] = to_native_str(fields[1], 'utf-8')
            json_fields = json_decode(to_native_str(fields[-1], 'utf-8'))
            for n, v in six.iteritems(json_fields):
                n = to_native_str(n, 'utf-8')
                n = self.CDX_ALT_FIELDS.get(n, n)

                if n == 'url':
                    try:
                        v.encode('ascii')
                    except UnicodeEncodeError:
                        v = quote(v.encode('utf-8'), safe=':/')

                if n != 'filename':
                    v = to_native_str(v, 'utf-8')

                self[n] = v

            self.cdxline = cdxline
            self._from_json = True
            return

        more_fields = fields.pop().split(b' ')
        fields.extend(more_fields)

        cdxformat = None
        for i in self.CDX_FORMATS:
            if len(i) == len(fields):
                cdxformat = i

        if not cdxformat:
            msg = 'unknown {0}-field cdx format'.format(len(fields))
            raise CDXException(msg)

        for header, field in zip(cdxformat, fields):
            self[header] = to_native_str(field, 'utf-8')

        self.cdxline = cdxline

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)

        # force regen on next __str__ call
        self.cdxline = None

        # force regen on next to_json() call
        self._cached_json = None

    def is_revisit(self):
        """return ``True`` if this record is a revisit record."""
        return (self.get(MIMETYPE) == 'warc/revisit' or
                self.get(FILENAME) == '-')

    def to_text(self, fields=None):
        """
        return plaintext CDX record (includes newline).
        if ``fields`` is ``None``, output will have all fields
        in the order they are stored.

        :param fields: list of field names to output.
        """
        if fields is None:
            return str(self) + '\n'

        try:
            result = ' '.join(str(self[x]) for x in fields) + '\n'
        except KeyError as ke:
            msg = 'Invalid field "{0}" found in fields= argument'
            msg = msg.format(str(ke))
            raise CDXException(msg)

        return result

    def to_json(self, fields=None):
        return self.conv_to_json(self, fields)

    @staticmethod
    def conv_to_json(obj, fields=None):
        """
        return cdx as json dictionary string
        if ``fields`` is ``None``, output will include all fields
        in order stored, otherwise only specified fields will be
        included

        :param fields: list of field names to output
        """
        if fields is None:
            return json_encode(OrderedDict(((x, obj[x]) for x in obj if not x.startswith('_')))) + '\n'

        result = json_encode(OrderedDict([(x, obj[x]) for x in fields if x in obj])) + '\n'

        return result

    def __str__(self):
        if self.cdxline:
            return to_native_str(self.cdxline, 'utf-8')

        if not self._from_json:
            return ' '.join(str(val) for val in six.itervalues(self))
        else:
            return json_encode(self)

    def to_cdxj(self, fields=None):
        prefix = self['urlkey'] + ' ' + self['timestamp'] + ' '
        dupe = OrderedDict(list(self.items())[2:])
        return prefix + self.conv_to_json(dupe, fields)

    def __lt__(self, other):
        if not self._cached_json:
            self._cached_json = self.to_json()

        if not other._cached_json:
            other._cached_json = other.to_json()

        res = self._cached_json < other._cached_json
        return res

    def __le__(self, other):
        if not self._cached_json:
            self._cached_json = self.to_json()

        if not other._cached_json:
            other._cached_json = other.to_json()

        res = (self._cached_json <= other._cached_json)
        return res


#=================================================================
class IDXObject(OrderedDict):

    FORMAT = ['urlkey', 'part', 'offset', 'length', 'lineno']
    NUM_REQ_FIELDS = len(FORMAT) - 1  # lineno is an optional field

    def __init__(self, idxline):
        OrderedDict.__init__(self)

        idxline = idxline.rstrip()
        fields = idxline.split(b'\t')

        if len(fields) < self.NUM_REQ_FIELDS:
            msg = 'invalid idx format: {0} fields found, {1} required'
            raise CDXException(msg.format(len(fields), self.NUM_REQ_FIELDS))

        for header, field in zip(self.FORMAT, fields):
            self[header] = to_native_str(field, 'utf-8')

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

    def to_json(self, fields=None):
        return json_encode(self) + '\n'

    def __str__(self):
        return to_native_str(self.idxline, 'utf-8')
