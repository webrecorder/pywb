import itertools
import urlparse
import collections

from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.statusandheaders import StatusAndHeadersParser
from pywb.utils.statusandheaders import StatusAndHeadersParserException

from pywb.utils.loaders import BlockLoader, LimitReader
from pywb.utils.bufferedreaders import DecompressingBufferedReader

from pywb.utils.wbexception import WbException


#=================================================================
ArcWarcRecord = collections.namedtuple('ArcWarcRecord',
                                       'format, rec_type, rec_headers, ' +
                                       'stream, status_headers')


#=================================================================
class ArchiveLoadFailed(WbException):
    def __init__(self, reason, filename=''):
        if filename:
            msg = filename + ':' + str(reason)
        else:
            msg = str(reason)

        super(ArchiveLoadFailed, self).__init__(msg)

    def status(self):
        return '503 Service Unavailable'


#=================================================================
class ArcWarcRecordLoader:
    # Standard ARC v1.0 headers
    # TODO: support ARV v2.0 also?
    ARC_HEADERS = ["uri", "ip-address", "archive-date",
                   "content-type", "length"]

    def __init__(self, loader=None, cookie_maker=None, block_size=8192):
        if not loader:
            loader = BlockLoader(cookie_maker)

        self.loader = loader
        self.block_size = block_size

        self.arc_parser = ARCHeadersParser(self.ARC_HEADERS)

        warc_types = ['WARC/1.0', 'WARC/0.17', 'WARC/0.18']
        self.warc_parser = StatusAndHeadersParser(warc_types)
        self.http_parser = StatusAndHeadersParser(['HTTP/1.0', 'HTTP/1.1'])

    def load(self, url, offset, length):
        """ Load a single record from given url at offset with length
        and parse as either warc or arc record
        """
        try:
            length = int(length)
        except:
            length = -1

        stream = self.loader.load(url, long(offset), length)
        decomp_type = 'gzip'

        # Create decompressing stream
        stream = DecompressingBufferedReader(stream=stream,
                                             decomp_type=decomp_type,
                                             block_size=self.block_size)

        return self.parse_record_stream(stream)

    def parse_record_stream(self, stream,
                            statusline=None, known_format=None):
        """ Parse file-like stream and return an ArcWarcRecord
        encapsulating the record headers, http headers (if any),
        and a stream limited to the remainder of the record.

        Pass statusline and known_format to detect_type_loader_headers()
        to faciliate parsing.
        """
        (the_format, rec_headers) = (self.
                                     _detect_type_load_headers(stream,
                                                               statusline,
                                                               known_format))

        if the_format == 'arc':
            if rec_headers.get_header('uri').startswith('filedesc://'):
                rec_type = 'arc_header'
                length = 0
            else:
                rec_type = 'response'
                length = rec_headers.get_header('length')

        elif the_format == 'warc':
            rec_type = rec_headers.get_header('WARC-Type')
            length = rec_headers.get_header('Content-Length')

        is_err = False

        try:
            length = int(length)
            if length < 0:
                is_err = True
        except ValueError:
            is_err = True

        # ================================================================
        # handle different types of records

        # err condition
        if is_err:
            status_headers = StatusAndHeaders('-', [])
            length = 0
        # special case: empty w/arc record (hopefully a revisit)
        elif length == 0:
            status_headers = StatusAndHeaders('204 No Content', [])

        # special case: warc records that are not expected to have http headers
        # attempt to add 200 status and content-type
        elif rec_type == 'metadata' or rec_type == 'resource':
            content_type = [('Content-Type',
                            rec_headers.get_header('Content-Type'))]

            status_headers = StatusAndHeaders('200 OK', content_type)

        elif (rec_type == 'warcinfo' or
              rec_type == 'arc_header' or
              rec_type == 'request'):
            # not parsing these for now
            status_headers = StatusAndHeaders('204 No Content', [])

        # special case: http 0.9 response, no status or headers
        #elif rec_type == 'response':
        #    content_type = rec_headers.get_header('Content-Type')
        #    if content_type and (';version=0.9' in content_type):
        #        status_headers = StatusAndHeaders('200 OK', [])

        # response record: parse HTTP status and headers!
        else:
            #(statusline, http_headers) = self.parse_http_headers(stream)
            status_headers = self.http_parser.parse(stream)

        # limit the stream to the remainder, if >0
        # should always be valid, but just in case, still stream if
        # content-length was not set
        remains = length - status_headers.total_len
        if remains >= 0:
            stream = LimitReader.wrap_stream(stream, remains)

        return ArcWarcRecord(the_format, rec_type,
                             rec_headers, stream, status_headers)

    def _detect_type_load_headers(self, stream,
                                  statusline=None, known_format=None):
        """ If known_format is specified ('warc' or 'arc'),
        parse only as that format.

        Otherwise, try parsing record as WARC, then try parsing as ARC.
        if neither one succeeds, we're out of luck.
        """

        if known_format != 'arc':
            # try as warc first
            try:
                rec_headers = self.warc_parser.parse(stream, statusline)
                return 'warc', rec_headers
            except StatusAndHeadersParserException as se:
                if known_format == 'warc':
                    msg = 'Invalid WARC record, first line: '
                    raise ArchiveLoadFailed(msg + str(se.statusline))

                statusline = se.statusline
                pass

        # now try as arc
        try:
            rec_headers = self.arc_parser.parse(stream, statusline)
            return 'arc', rec_headers
        except StatusAndHeadersParserException as se:
            if known_format == 'arc':
                msg = 'Invalid WARC record, first line: '
            else:
                msg = 'Unknown archive format, first line: '
            raise ArchiveLoadFailed(msg + str(se.statusline))


#=================================================================
class ARCHeadersParser:
    def __init__(self, headernames):
        self.headernames = headernames

    def parse(self, stream, headerline=None):

        total_read = 0

        # if headerline passed in, use that
        if headerline is None:
            headerline = stream.readline()

        total_read = len(headerline)

        if total_read == 0:
            raise EOFError()

        headerline = headerline.rstrip()

        headernames = self.headernames

        # if arc header, consume next two lines
        if headerline.startswith('filedesc://'):
            stream.readline()  # skip version
            stream.readline()  # skip header spec, use preset one

        parts = headerline.split(' ')

        if len(parts) != len(headernames):
            msg = 'Wrong # of headers, expected arc headers {0}, Found {1}'
            msg = msg.format(headernames, parts)
            raise StatusAndHeadersParserException(msg, parts)

        headers = []

        for name, value in itertools.izip(headernames, parts):
            headers.append((name, value))

        return StatusAndHeaders(statusline='',
                                headers=headers,
                                protocol='ARC/1.0',
                                total_len=total_read)
