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
                                       'stream, status_headers, ' +
                                       'content_type, length')


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
    # TODO: support ARC v2.0 also?
    ARC_HEADERS = ["uri", "ip-address", "archive-date",
                   "content-type", "length"]

    WARC_TYPES = ['WARC/1.0', 'WARC/0.17', 'WARC/0.18']

    HTTP_TYPES = ['HTTP/1.0', 'HTTP/1.1']

    HTTP_VERBS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE',
                  'OPTIONS', 'CONNECT', 'PATCH']

    NON_HTTP_RECORDS = ('warcinfo', 'arc_header', 'metadata', 'resource')

    def __init__(self, loader=None, cookie_maker=None, block_size=8192,
                 verify_http=True):
        if not loader:
            loader = BlockLoader(cookie_maker)

        self.loader = loader
        self.block_size = block_size

        self.arc_parser = ARCHeadersParser(self.ARC_HEADERS)

        self.warc_parser = StatusAndHeadersParser(self.WARC_TYPES)
        self.http_parser = StatusAndHeadersParser(self.HTTP_TYPES, verify_http)

        self.http_req_parser = StatusAndHeadersParser(self.HTTP_VERBS, verify_http)

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
                            statusline=None,
                            known_format=None,
                            no_record_parse=False):
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
            uri = rec_headers.get_header('uri')
            length = rec_headers.get_header('length')
            content_type = rec_headers.get_header('content-type')
            sub_len = rec_headers.total_len
            if uri and uri.startswith('filedesc://'):
                rec_type = 'arc_header'
            else:
                rec_type = 'response'

        elif the_format == 'warc':
            rec_type = rec_headers.get_header('WARC-Type')
            uri = rec_headers.get_header('WARC-Target-URI')
            length = rec_headers.get_header('Content-Length')
            content_type = rec_headers.get_header('Content-Type')
            sub_len = 0

        is_err = False

        try:
            length = int(length) - sub_len
            if length < 0:
                is_err = True
        except ValueError:
            is_err = True

        # err condition
        if is_err:
            length = 0
        # limit stream to the length for all valid records
        stream = LimitReader.wrap_stream(stream, length)

        # don't parse the http record at all
        if no_record_parse:
            status_headers = None#StatusAndHeaders('', [])

        # if empty record (error or otherwise) set status to 204
        elif length == 0:
            if is_err:
                msg = '204 Possible Error'
            else:
                msg = '204 No Content'

            status_headers = StatusAndHeaders(msg, [])

        # response record or non-empty revisit: parse HTTP status and headers!
        elif (rec_type in ('response', 'revisit') and
              not uri.startswith(('dns:', 'whois:'))):
            status_headers = self.http_parser.parse(stream)

        # request record: parse request
        elif ((rec_type == 'request') and
              not uri.startswith(('dns:', 'whois:'))):
            status_headers = self.http_req_parser.parse(stream)

        # everything else: create a no-status entry, set content-type
        else:
            content_type_header = [('Content-Type', content_type),
                                   ('Content-Length', str(length))]

            status_headers = StatusAndHeaders('200 OK', content_type_header)

        return ArcWarcRecord(the_format, rec_type,
                             rec_headers, stream, status_headers,
                             content_type, length)

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
                msg = 'Invalid ARC record, first line: '
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

        header_len = len(headerline)

        if header_len == 0:
            raise EOFError()

        headerline = headerline.rstrip()

        headernames = self.headernames

        # if arc header, consume next two lines
        if headerline.startswith('filedesc://'):
            version = stream.readline()  # skip version
            spec = stream.readline()  # skip header spec, use preset one
            total_read += len(version)
            total_read += len(spec)

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
