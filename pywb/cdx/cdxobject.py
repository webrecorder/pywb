from collections import OrderedDict
import itertools


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

    def __str__(self):
        if self.cdxline:
            return self.cdxline

        li = itertools.imap(lambda (n, val): val, self.items())
        return ' '.join(li)
