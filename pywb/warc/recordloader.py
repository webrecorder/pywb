import itertools
import urlparse
import collections

from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.statusandheaders import StatusAndHeadersParser
from pywb.utils.statusandheaders import StatusAndHeadersParserException

from pywb.utils.loaders import FileLoader, HttpLoader
from pywb.utils.bufferedreaders import BufferedReader

#=================================================================
ArcWarcRecord = collections.namedtuple('ArchiveRecord',
                                       'type, rec_headers, ' +
                                       'stream, status_headers')


#=================================================================
class ArchiveLoadFailed(Exception):
    def __init__(self, reason, filename=''):
        super(ArchiveLoadFailed, self).__init__(filename + ':' + str(reason))
        #self.filename = filename
        #self.reason = reason

    def status(self):
        return '503 Service Unavailable'


#=================================================================
class ArcWarcRecordLoader:
    # Standard ARC headers
    ARC_HEADERS = ["uri", "ip-address", "creation-date",
                   "content-type", "length"]

    @staticmethod
    def create_default_loaders(cookie_maker=None):
        http = HttpLoader(cookie_maker)
        file = FileLoader()
        return {
            'http': http,
            'https': http,
            'file': file,
            '': file
            }

    def __init__(self, loaders={}, cookie_maker=None, chunk_size=8192):
        self.loaders = loaders

        if not self.loaders:
            self.loaders = self.create_default_loaders(cookie_maker)

        self.chunk_size = chunk_size

        self.arc_parser = ARCHeadersParser(self.ARC_HEADERS)

        warc_types = ['WARC/1.0', 'WARC/0.17', 'WARC/0.18']
        self.warc_parser = StatusAndHeadersParser(warc_types)
        self.http_parser = StatusAndHeadersParser(['HTTP/1.0', 'HTTP/1.1'])

    def load(self, url, offset, length):
        url_parts = urlparse.urlsplit(url)

        loader = self.loaders.get(url_parts.scheme)
        if not loader:
            raise ArchiveLoadFailed('Unknown Protocol', url)

        try:
            length = int(length)
        except:
            length = -1

        raw = loader.load(url, long(offset), length)

        decomp_type = 'gzip'

        stream = BufferedReader(raw, length, self.chunk_size, decomp_type)

        (the_format, rec_headers) = self._load_headers(stream)

        if the_format == 'arc':
            rec_type = 'response'
            empty = (rec_headers.get_header('length') == 0)

        elif the_format == 'warc':
            rec_type = rec_headers.get_header('WARC-Type')
            empty = (rec_headers.get_header('Content-Length') == '0')

        # special case: empty w/arc record (hopefully a revisit)
        if empty:
            status_headers = StatusAndHeaders('204 No Content', [])

        # special case: warc records that are not expected to have http headers
        # attempt to add 200 status and content-type
        elif rec_type == 'metadata' or rec_type == 'resource':
            content_type = [('Content-Type',
                            rec_headers.get_header('Content-Type'))]

            status_headers = StatusAndHeaders('200 OK', content_type)

        # special case: http 0.9 response, no status or headers
        #elif rec_type == 'response':
        #    content_type = rec_headers.get_header('Content-Type')
        #    if content_type and (';version=0.9' in content_type):
        #        status_headers = StatusAndHeaders('200 OK', [])

        # response record: parse HTTP status and headers!
        else:
            #(statusline, http_headers) = self.parse_http_headers(stream)
            status_headers = self.http_parser.parse(stream)

        return ArcWarcRecord((the_format, rec_type),
                             rec_headers, stream, status_headers)

    def _load_headers(self, stream):
        """
        Try parsing record as WARC, then try parsing as ARC.
        if neither one succeeds, we're out of luck.
        """

        statusline = None

        # try as warc first
        try:
            rec_headers = self.warc_parser.parse(stream)
            return 'warc', rec_headers
        except StatusAndHeadersParserException as se:
            statusline = se.statusline
            pass

        # now try as arc
        try:
            rec_headers = self.arc_parser.parse(stream, statusline)
            return 'arc', rec_headers
        except StatusAndHeadersParserException as se:
            msg = 'Unknown archive format, first line: ' + se.statusline
            raise ArchiveLoadFailed(msg)


#=================================================================
class ARCHeadersParser:
    def __init__(self, headernames):
        self.headernames = headernames

    def parse(self, stream, headerline=None):

        # if headerline passed in, use that
        if not headerline:
            headerline = stream.readline().rstrip()

        parts = headerline.split()

        headernames = self.headernames

        if len(parts) != len(headernames):
            msg = 'Wrong # of headers, expected arc headers {0}, Found {1}'
            msg = msg.format(headernames, parts)
            raise StatusAndHeadersParserException(msg, headernames)

        headers = []

        for name, value in itertools.izip(headernames, parts):
            headers.append((name, value))

        return StatusAndHeaders(statusline='',
                                headers=headers,
                                protocol='ARC/1.0')
