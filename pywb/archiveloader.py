import hanzo.warctools

import re
import utils
import zlib
import urllib2
import StringIO
import urlparse
import collections
import wbexceptions

#=================================================================
class HttpStreamLoader:
    def __init__(self, hmac = None, hmacDuration = 30):
        self.hmac = hmac
        self.hmacDuration = hmacDuration

    def load(self, url, offset, length):
        if length > 0:
            rangeHeader = 'bytes={0}-{1}'.format(offset, offset + length - 1)
        else:
            rangeHeader = 'bytes={0}-'.format(offset)

        headers = {}
        headers['Range'] = rangeHeader

        if self.hmac:
            headers['Cookie'] = self.hmac(self.hmacDuration)

        request = urllib2.Request(url, headers = headers)
        return urllib2.urlopen(request)


#=================================================================
# Untested, but for completeness
class FileStreamLoader:
    def load(self, url, offset, length):
        if url.startswith('file://'):
            url = url[len('file://'):]

        afile = open(url, 'rb')
        afile.seek(offset)
        return afile



#=================================================================
WBArchiveRecord = collections.namedtuple('WBArchiveRecord', 'type, record, stream, statusline, httpHeaders')

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

    HTTP_STATUS_REGEX = re.compile('^HTTP/[\d.]+ (\d+.*)$')

    @staticmethod
    def createDefaultLoaders():
        http = HttpStreamLoader()
        file = FileStreamLoader()
        return {
                'http': http,
                'https': http,
                'file': file,
                '': file
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

        try:
            length = int(length)
        except:
            length = -1


        raw = loader.load(url, long(offset), length)

        reader = LineReader(raw, length, self.chunkSize, decomp)

        parser = loaderCls.make_parser()

        if aFormat == 'arc':
            parser.headers = ArchiveLoader.ARC_HEADERS

        (parsed, errors, _) = parser.parse(reader, 0)

        if errors:
            reader.close()
            raise wbexceptions.InvalidArchiveRecordException('Error Parsing Record', errors)


        if aFormat == 'arc':
            recType = 'response'
            empty = (utils.get_header(parsed.headers, 'length') == 0)
        else:
            recType = utils.get_header(parsed.headers, 'WARC-Type')
            empty = (utils.get_header(parsed.headers, 'Content-Length') == '0')

        # special case: empty w/arc record (hopefully a revisit)
        if empty:
            statusline = '204 No Content'
            headers = []

        # special case: warc records that are not expected to have http headers
        # attempt to add 200 status and content-type
        elif recType == 'metadata' or recType == 'resource':
            statusline = '200 OK'
            headers = [('Content-Type', utils.get_header(parsed.headers, 'Content-Type'))]

        # special case: http 0.9 response, no status or headers
        #elif recType == 'response' and (';version=0.9' in utils.get_header(parsed.headers, 'Content-Type')):
        #    statusline = '200 OK'
        #    headers = []

        # response record: parse HTTP status and headers!
        else:
            (statusline, headers) = self.parseHttpHeaders(reader)

        return WBArchiveRecord((aFormat, recType), parsed, reader, statusline, headers)


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
    def __init__(self, stream, maxLen = 0, chunkSize = 1024, decomp = None):
        self.stream = stream
        self.chunkSize = chunkSize
        self.decomp = decomp
        self.buff = None
        self.numRead = 0
        self.maxLen = maxLen

    def _fillbuff(self, chunkSize = None):
        if not chunkSize:
            chunkSize = self.chunkSize

        if not self.buff or self.buff.pos >= self.buff.len:
            toRead =  min(self.maxLen - self.numRead, self.chunkSize) if (self.maxLen > 0) else self.chunkSize
            data = self.stream.read(toRead)
            self.numRead += len(data)

            if self.decomp:
                data = self.decomp.decompress(data)

            self.buff = StringIO.StringIO(data)

    def read(self, length = None):
        self._fillbuff()
        return self.buff.read(length)

    def readline(self, length = None):
        self._fillbuff()
        return self.buff.readline(length)

    def close(self):
        if self.stream:
            self.stream.close()
            self.stream = None



