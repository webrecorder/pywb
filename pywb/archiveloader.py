import hanzo.warctools

import re
import utils
import zlib
import urllib2
import StringIO
import urlparse
import collections

#=================================================================
class HttpStreamLoader:
    def __init__(self, hmac = None, hmacDuration = 30):
        self.hmac = hmac
        self.hmacDuration = hmacDuration

    def load(self, url, offset, length):
        if length:
            rangeHeader = 'bytes={0}-{1}'.format(offset, int(offset) + int(length) - 1)
        else:
            rangeHeader = 'bytes={0}-'.format(offset)

        headers = {}
        headers['Range'] = rangeHeader

        if self.hmac:
            headers['Cookie'] = self.hmac(self.hmacDuration)

        request = urllib2.Request(url, headers = headers)
        return urllib2.urlopen(request)


#=================================================================
WBArchiveRecord = collections.namedtuple('WBArchiveRecord', 'parsed, stream, statusline, httpHeaders')

#=================================================================
class ArchiveLoader:
    # Standard ARC headers
    ARC_HEADERS = ["uri", "ip-address", "creation-date", "content-type", "length"]

    # Since loading a range request, can only determine gzip-ness based on file extension
    FORMAT_MAP = {
        '.warc.gz': (hanzo.warctools.WarcRecord, 'warc', True),
        '.arc.gz':  (hanzo.warctools.ArcRecord,  'arc',  True),
        '.warc':    (hanzo.warctools.WarcRecord, 'warc', False),
        '.arc':     (hanzo.warctools.ArcRecord,  'arc',  False),
    }

    HTTP_STATUS_REGEX = re.compile('^HTTP/[\d.]+ ((\d+).*)$')

    @staticmethod
    def createDefaultLoaders():
        http = HttpStreamLoader()
        return {
                'http': http,
                'https': http,
               }


    def __init__(self, loaders = {}, chunkSize = 8192):
        self.loaders = loaders if loaders else ArchiveLoader.createDefaultLoaders()
        self.chunkSize = chunkSize

    def load(self, url, offset, length):
        urlParts = urlparse.urlsplit(url)

        try:
            loader = self.loaders.get(urlParts.scheme)
        except Exception:
            raise wbexceptions.UnknownLoaderProtocolException(url)

        loaderCls = None

        for ext, (loaderCls, aFormat, gzip) in ArchiveLoader.FORMAT_MAP.iteritems():
            if url.endswith(ext):
                loaderCls = loaderCls
                aFormat = aFormat
                isGzip = gzip
                break

        if loaderCls is None:
            raise wbexceptions.UnknownArchiveFormatException(url)

        if isGzip:
            decomp = zlib.decompressobj(16+zlib.MAX_WBITS)
        else:
            decomp = None


        raw = loader.load(url, offset, length)

        reader = LineReader(raw, self.chunkSize, decomp)

        parser = loaderCls.make_parser()

        if aFormat == 'arc':
            parser.headers = ArchiveLoader.ARC_HEADERS

        (parsed, errors, _) = parser.parse(reader, 0)

        if errors:
            reader.close()
            raise wbexceptions.InvalidArchiveRecordException('Error Parsing Record', errors)


        if aFormat == 'arc':
            recType = 'arc-response'
            empty = (utils.get_header(parsed.headers, 'length') == 0)
        else:
            recType = utils.get_header(parsed.headers, 'WARC-Type')
            empty = (utils.get_header(parsed.headers, 'Content-Length') == '0')

        parsed.recType = recType
        parsed.aFormat = aFormat

        if empty:
            return WBArchiveRecord(parsed, reader, '400', [])

        elif recType == 'metadata' or recType == 'resource':
            headers = [('Content-Type', utils.get_header(parsed.headers, 'Content-Type'))]

            return WBArchiveRecord(parsed, reader, '200 OK', headers)

        else:
            (statusline, headers) = self.parseHttpHeaders(reader)

            return WBArchiveRecord(parsed, reader, statusline, headers)


    def parseHttpHeaders(self, stream):
        def nextHeaderLine(stream):
            return stream.readline().rstrip()

        line = nextHeaderLine(stream)
        matched = self.HTTP_STATUS_REGEX.match(line)

        if not matched:
            raise wbexceptions.InvalidArchiveRecordException('Expected HTTP Status Line, Found: ' + line)

        #status = int(matched.group(2))
        statusline = matched.group(1)
        headers = []

        line = nextHeaderLine(stream)

        while line and line != '\r\n':
            name, value = line.split(':', 1)
            value = value.strip()
            headers.append((name, value))
            line = nextHeaderLine(stream)

        return (statusline, headers)

#=================================================================
class LineReader:
    def __init__(self, stream, chunkSize = 1024, decomp = None):
        self.stream = stream
        self.chunkSize = chunkSize
        self.decomp = decomp
        self.buff = None
        self.numread = 0

    def _fillbuff(self, chunkSize = None):
        if not chunkSize:
            chunkSize = self.chunkSize

        if not self.buff or self.buff.pos >= self.buff.len:
            data = self.stream.read(chunkSize)
            self.numread += len(data)
            if self.decomp:
                data = self.decomp.decompress(data)

            self.buff = StringIO.StringIO(data)

    def read(self):
        self._fillbuff()
        return self.buff.read()

    def readline(self):
        self._fillbuff()
        return self.buff.readline()

    def close(self):
        if self.stream:
            self.stream.close()
            self.stream = None



