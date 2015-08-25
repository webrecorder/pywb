try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict

import itertools

from urllib import urlencode, quote
from urlparse import parse_qs

from pywb.utils.wbexception import WbException

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

    def __init__(self, cdxline=''):
        OrderedDict.__init__(self)

        cdxline = cdxline.rstrip()
        self._from_json = False

        # Allows for filling the fields later or in a custom way
        if not cdxline:
            self.cdxline = cdxline
            return

        fields = cdxline.split(' ' , 2)
        # Check for CDX JSON
        if fields[-1].startswith('{'):
            self[URLKEY] = fields[0]
            self[TIMESTAMP] = fields[1]
            json_fields = json_decode(fields[-1])
            for n, v in json_fields.iteritems():
                n = self.CDX_ALT_FIELDS.get(n, n)

                try:
                    self[n] = str(v)
                except UnicodeEncodeError:
                    v = v.encode('utf-8')
                    parts = v.split('//', 1)
                    v = parts[0] + '//' + quote(parts[1])
                    self[n] = v

            self.cdxline = cdxline
            self._from_json = True
            return

        more_fields = fields.pop().split(' ')
        fields.extend(more_fields)

        cdxformat = None
        for i in self.CDX_FORMATS:
            if len(i) == len(fields):
                cdxformat = i

        if not cdxformat:
            msg = 'unknown {0}-field cdx format'.format(len(fields))
            raise CDXException(msg)

        for header, field in itertools.izip(cdxformat, fields):
            self[header] = field

        self.cdxline = cdxline

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)

        # force regen on next __str__ call
        self.cdxline = None

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
            result = ' '.join(self[x] for x in fields) + '\n'
        except KeyError as ke:
            msg = 'Invalid field "{0}" found in fields= argument'
            msg = msg.format(ke.message)
            raise CDXException(msg)

        return result

    def to_json(self, fields=None):
        """
        return cdx as json dictionary string
        if ``fields`` is ``None``, output will include all fields
        in order stored, otherwise only specified fields will be
        included

        :param fields: list of field names to output
        """
        if fields is None:
            return json_encode(self) + '\n'

        try:
            result = json_encode(OrderedDict((x, self[x]) for x in fields)) + '\n'
        except KeyError as ke:
            msg = 'Invalid field "{0}" found in fields= argument'
            msg = msg.format(ke.message)
            raise CDXException(msg)

        return result

    def __str__(self):
        if self.cdxline:
            return self.cdxline

        if not self._from_json:
            return ' '.join(val for n, val in self.iteritems())
        else:
            return json_encode(self)

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
            raise CDXException(msg.format(len(fields), self.NUM_REQ_FIELDS))

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

    def to_json(self, fields=None):
        return json_encode(self) + '\n'

    def __str__(self):
        return self.idxline
