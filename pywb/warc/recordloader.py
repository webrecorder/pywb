import collections

from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.statusandheaders import StatusAndHeadersParser
from pywb.utils.statusandheaders import StatusAndHeadersParserException

from pywb.utils.loaders import BlockLoader, LimitReader
from pywb.utils.loaders import to_native_str
from pywb.utils.bufferedreaders import DecompressingBufferedReader

from pywb.utils.wbexception import WbException
from pywb.utils.timeutils import timestamp_to_iso_date

from six.moves import zip
import six


#=================================================================
ArcWarcRecord = collections.namedtuple('ArcWarcRecord',
                                       'format, rec_type, rec_headers, ' +
                                       'stream, status_headers, ' +
                                       'content_type, length')


#=================================================================
class ArchiveLoadFailed(WbException):
    def __init__(self, reason, filename=''):
        if filename:
            msg = filename + ': ' + str(reason)
        else:
            msg = str(reason)

        super(ArchiveLoadFailed, self).__init__(msg)

    def status(self):
        return '503 Service Unavailable'


#=================================================================
class ArcWarcRecordLoader(object):
    WARC_TYPES = ['WARC/1.0', 'WARC/0.17', 'WARC/0.18']

    HTTP_TYPES = ['HTTP/1.0', 'HTTP/1.1']

    HTTP_VERBS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE',
                  'OPTIONS', 'CONNECT', 'PATCH']

    NON_HTTP_RECORDS = ('warcinfo', 'arc_header', 'metadata', 'resource')

    NON_HTTP_SCHEMES = ('dns:', 'whois:', 'ntp:')
    HTTP_SCHEMES = ('http:', 'https:')

    def __init__(self, loader=None, cookie_maker=None, block_size=8192,
                 verify_http=True, arc2warc=True):
        if not loader:
            loader = BlockLoader(cookie_maker=cookie_maker)

        self.loader = loader
        self.block_size = block_size

        if arc2warc:
            self.arc_parser = ARC2WARCHeadersParser()
        else:
            self.arc_parser = ARCHeadersParser()

        self.warc_parser = StatusAndHeadersParser(self.WARC_TYPES)
        self.http_parser = StatusAndHeadersParser(self.HTTP_TYPES, verify_http)

        self.http_req_parser = StatusAndHeadersParser(self.HTTP_VERBS, verify_http)

    def load(self, url, offset, length, no_record_parse=False):
        """ Load a single record from given url at offset with length
        and parse as either warc or arc record
        """
        try:
            length = int(length)
        except:
            length = -1

        stream = self.loader.load(url, int(offset), length)
        decomp_type = 'gzip'

        # Create decompressing stream
        stream = DecompressingBufferedReader(stream=stream,
                                             decomp_type=decomp_type,
                                             block_size=self.block_size)

        return self.parse_record_stream(stream, no_record_parse=no_record_parse)

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

        elif the_format in ('warc', 'arc2warc'):
            rec_type = rec_headers.get_header('WARC-Type')
            uri = rec_headers.get_header('WARC-Target-URI')
            length = rec_headers.get_header('Content-Length')
            content_type = rec_headers.get_header('Content-Type')
            if the_format == 'warc':
                sub_len = 0
            else:
                sub_len = rec_headers.total_len
                the_format = 'warc'

        is_err = False

        try:
            if length is not None:
                length = int(length) - sub_len
                if length < 0:
                    is_err = True

        except (ValueError, TypeError):
            is_err = True

        # err condition
        if is_err:
            length = 0

        # limit stream to the length for all valid records
        if length is not None and length >= 0:
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
        elif (rec_type in ('response', 'revisit')
              and uri.startswith(self.HTTP_SCHEMES)):
            status_headers = self.http_parser.parse(stream)

        # request record: parse request
        elif ((rec_type == 'request')
              and uri.startswith(self.HTTP_SCHEMES)):
            status_headers = self.http_req_parser.parse(stream)

        # everything else: create a no-status entry, set content-type
        else:
            content_type_header = [('Content-Type', content_type)]

            if length is not None and length >= 0:
                content_type_header.append(('Content-Length', str(length)))

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
            return self.arc_parser.get_rec_type(), rec_headers
        except StatusAndHeadersParserException as se:
            if known_format == 'arc':
                msg = 'Invalid ARC record, first line: '
            else:
                msg = 'Unknown archive format, first line: '
            raise ArchiveLoadFailed(msg + str(se.statusline))


#=================================================================
class ARCHeadersParser(object):
    # ARC 1.0 headers
    ARC_HEADERS = ["uri", "ip-address", "archive-date",
                       "content-type", "length"]

    def __init__(self):
        self.headernames = self.get_header_names()

    def get_rec_type(self):
        return 'arc'

    def parse(self, stream, headerline=None):
        total_read = 0

        def readline():
            return to_native_str(stream.readline())

        # if headerline passed in, use that
        if headerline is None:
            headerline = readline()
        else:
            headerline = to_native_str(headerline)

        header_len = len(headerline)

        if header_len == 0:
            raise EOFError()

        headerline = headerline.rstrip()

        headernames = self.headernames

        # if arc header, consume next two lines
        if headerline.startswith('filedesc://'):
            version = readline()  # skip version
            spec = readline()  # skip header spec, use preset one
            total_read += len(version)
            total_read += len(spec)

        parts = headerline.split(' ')

        if len(parts) != len(headernames):
            msg = 'Wrong # of headers, expected arc headers {0}, Found {1}'
            msg = msg.format(headernames, parts)
            raise StatusAndHeadersParserException(msg, parts)


        protocol, headers = self._get_protocol_and_headers(headerline, parts)

        return StatusAndHeaders(statusline='',
                                headers=headers,
                                protocol='WARC/1.0',
                                total_len=total_read)

    @classmethod
    def get_header_names(cls):
        return cls.ARC_HEADERS

    def _get_protocol_and_headers(self, headerline, parts):
        headers = []

        for name, value in zip(self.headernames, parts):
            headers.append((name, value))

        return ('ARC/1.0', headers)


#=================================================================
class ARC2WARCHeadersParser(ARCHeadersParser):
    # Headers for converting ARC -> WARC Header
    ARC_TO_WARC_HEADERS = ["WARC-Target-URI",
                           "WARC-IP-Address",
                           "WARC-Date",
                           "Content-Type",
                           "Content-Length"]

    def get_rec_type(self):
        return 'arc2warc'

    @classmethod
    def get_header_names(cls):
        return cls.ARC_TO_WARC_HEADERS

    def _get_protocol_and_headers(self, headerline, parts):
        headers = []

        for name, value in zip(self.headernames, parts):
            if name == 'WARC-Date':
                value = timestamp_to_iso_date(value)

            headers.append((name, value))

        if headerline.startswith('filedesc://'):
            rec_type = 'arc_header'
        else:
            rec_type = 'response'

        headers.append(('WARC-Type', rec_type))
        headers.append(('WARC-Record-ID', StatusAndHeadersParser.make_warc_id()))

        return ('WARC/1.0', headers)


