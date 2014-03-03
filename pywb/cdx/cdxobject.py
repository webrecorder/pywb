from collections import OrderedDict
import itertools

from urllib import urlencode
from urlparse import parse_qs

from pywb.utils.wbexception import WbException


#=================================================================
class CDXException(WbException):
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
