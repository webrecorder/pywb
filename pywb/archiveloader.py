import itertools
import utils
import urllib2
import StringIO
import urlparse
import collections
import wbexceptions

from wbrequestresponse import StatusAndHeaders

#=================================================================
class HttpReader:
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
class FileReader:
    def load(self, url, offset, length):
        if url.startswith('file://'):
            url = url[len('file://'):]

        afile = open(url, 'rb')
        afile.seek(offset)
        return afile



#=================================================================
WBArchiveRecord = collections.namedtuple('WBArchiveRecord', 'type, rec_headers, stream, status_headers')

#=================================================================

class ArchiveLoader:
    """
    >>> loadTestArchive('example.warc.gz', '333', '1043')
    (('warc', 'response'),
     StatusAndHeaders(protocol = 'WARC/1.0', statusline = '', headers = [ ('WARC-Type', 'response'),
      ('WARC-Record-ID', '<urn:uuid:6d058047-ede2-4a13-be79-90c17c631dd4>'),
      ('WARC-Date', '2014-01-03T03:03:21Z'),
      ('Content-Length', '1610'),
      ('Content-Type', 'application/http; msgtype=response'),
      ('WARC-Payload-Digest', 'sha1:B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A'),
      ('WARC-Target-URI', 'http://example.com?example=1'),
      ('WARC-Warcinfo-ID', '<urn:uuid:fbd6cf0a-6160-4550-b343-12188dc05234>')]),
     StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
      ('Cache-Control', 'max-age=604800'),
      ('Content-Type', 'text/html'),
      ('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
      ('Etag', '"359670651"'),
      ('Expires', 'Fri, 10 Jan 2014 03:03:21 GMT'),
      ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
      ('Server', 'ECS (sjc/4FCE)'),
      ('X-Cache', 'HIT'),
      ('x-ec-custom-error', '1'),
      ('Content-Length', '1270'),
      ('Connection', 'close')]))
      

    >>> loadTestArchive('example.warc.gz', '1864', '553')
    (('warc', 'revisit'),
     StatusAndHeaders(protocol = 'WARC/1.0', statusline = '', headers = [ ('WARC-Type', 'revisit'),
      ('WARC-Record-ID', '<urn:uuid:3619f5b0-d967-44be-8f24-762098d427c4>'),
      ('WARC-Date', '2014-01-03T03:03:41Z'),
      ('Content-Length', '340'),
      ('Content-Type', 'application/http; msgtype=response'),
      ('WARC-Payload-Digest', 'sha1:B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A'),
      ('WARC-Target-URI', 'http://example.com?example=1'),
      ('WARC-Warcinfo-ID', '<urn:uuid:fbd6cf0a-6160-4550-b343-12188dc05234>'),
      ( 'WARC-Profile',
        'http://netpreserve.org/warc/0.18/revisit/identical-payload-digest'),
      ('WARC-Refers-To-Target-URI', 'http://example.com?example=1'),
      ('WARC-Refers-To-Date', '2014-01-03T03:03:21Z')]),
     StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
      ('Cache-Control', 'max-age=604800'),
      ('Content-Type', 'text/html'),
      ('Date', 'Fri, 03 Jan 2014 03:03:41 GMT'),
      ('Etag', '"359670651"'),
      ('Expires', 'Fri, 10 Jan 2014 03:03:41 GMT'),
      ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
      ('Server', 'ECS (sjc/4FCE)'),
      ('X-Cache', 'HIT'),
      ('x-ec-custom-error', '1'),
      ('Content-Length', '1270'),
      ('Connection', 'close')]))
    """

    # Standard ARC headers
    ARC_HEADERS = ["uri", "ip-address", "creation-date", "content-type", "length"]

    # Since loading a range request, can only determine gzip-ness based on file extension
    FORMAT_MAP = {
        '.warc.gz': ('warc', True),
        '.arc.gz':  ('arc',  True),
        '.warc':    ('warc', False),
        '.arc':     ('arc',  False),
    }

    @staticmethod
    def createDefaultLoaders():
        http = HttpReader()
        file = FileReader()
        return {
                'http': http,
                'https': http,
                'file': file,
                '': file
               }


    def __init__(self, loaders = {}, chunkSize = 8192):
        self.loaders = loaders if loaders else ArchiveLoader.createDefaultLoaders()
        self.chunkSize = chunkSize

        self.arcParser = ARCHeadersParser(ArchiveLoader.ARC_HEADERS)
        self.warcParser = StatusAndHeadersParser(['WARC/1.0', 'WARC/0.17', 'WARC/0.18'])
        self.httpParser = StatusAndHeadersParser(['HTTP/1.0', 'HTTP/1.1'])

    def load(self, url, offset, length):
        urlParts = urlparse.urlsplit(url)

        try:
            loader = self.loaders.get(urlParts.scheme)
        except Exception:
            raise wbexceptions.UnknownLoaderProtocolException(url)

        theFormat = None

        for ext, iformat in ArchiveLoader.FORMAT_MAP.iteritems():
            if url.endswith(ext):
                theFormat = iformat
                break

        if theFormat is None:
            raise wbexceptions.UnknownArchiveFormatException(url)

        (aFormat, isGzip) = theFormat

        decomp = utils.create_decompressor() if isGzip else None

        try:
            length = int(length)
        except:
            length = -1


        raw = loader.load(url, long(offset), length)

        stream = LineReader(raw, length, self.chunkSize, decomp)

        if aFormat == 'arc':
            rec_headers = self.arcParser.parse(stream)
            recType = 'response'
            empty = (rec_headers.getHeader('length') == 0)

        elif aFormat == 'warc':
            rec_headers = self.warcParser.parse(stream)
            recType = rec_headers.getHeader('WARC-Type')
            empty = (rec_headers.getHeader('Content-Length') == '0')

        # special case: empty w/arc record (hopefully a revisit)
        if empty:
            status_headers = StatusAndHeaders('204 No Content', [])

        # special case: warc records that are not expected to have http headers
        # attempt to add 200 status and content-type
        elif recType == 'metadata' or recType == 'resource':
            status_headers = StatusAndHeaders('200 OK', [('Content-Type', rec_headers.getHeader('Content-Type'))])

        # special case: http 0.9 response, no status or headers
        #elif recType == 'response':
        #    contentType = rec_headers.getHeader('Content-Type')
        #    if contentType and (';version=0.9' in contentType):
        #        status_headers = StatusAndHeaders('200 OK', [])

        # response record: parse HTTP status and headers!
        else:
            #(statusline, http_headers) = self.parseHttpHeaders(stream)
            status_headers = self.httpParser.parse(stream)

        return WBArchiveRecord((aFormat, recType), rec_headers, stream, status_headers)


#=================================================================
class StatusAndHeadersParser:
    def __init__(self, statuslist):
        self.statuslist = statuslist

    def parse(self, stream):
        statusline = stream.readline().rstrip()

        protocolStatus = utils.split_prefix(statusline, self.statuslist)

        if not protocolStatus:
            raise wbexceptions.InvalidArchiveRecordException('Expected Status Line, Found: ' + statusline)

        headers = []

        line = stream.readline().rstrip()
        while line and line != '\r\n':
            name, value = line.split(':', 1)
            header = (name, value.strip())
            headers.append(header)
            line = stream.readline().rstrip()

        return StatusAndHeaders(statusline = protocolStatus[1].strip(), headers = headers, protocol = protocolStatus[0])

#=================================================================
class ARCHeadersParser:
    def __init__(self, headernames):
        self.headernames = headernames


    def parse(self, stream):
        headerline = stream.readline().rstrip()

        parts = headerline.split()

        headernames = self.headernames

        if len(parts) != len(headernames):
            raise wbexceptions.InvalidArchiveRecordException('Wrong # of heaeders, expected arc headers {0}, Found {1}'.format(headernames, parts))

        headers = []

        for name, value in itertools.izip(headernames, parts):
            headers.append((name, value))

        return StatusAndHeaders(statusline = '', headers = headers, protocol = 'ARC/1.0')

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
            self._process_read(data)

    def _process_read(self, data):
        self.numRead += len(data)

        if self.decomp and data:
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


class ChunkedDataException(Exception):
    pass


class ChunkedLineReader(LineReader):
    r"""
    Properly formatted chunked data:
    >>> c=ChunkedLineReader(StringIO.StringIO("4\r\n1234\r\n0\r\n\r\n")); c.read()+c.read()
    '1234'

    Non-chunked data:
    >>> ChunkedLineReader(StringIO.StringIO("xyz123!@#")).read()
    'xyz123!@#'

    Starts like chunked data, but isn't:
    >>> c=ChunkedLineReader(StringIO.StringIO("1\r\nxyz123!@#")); c.read()+c.read()
    '1\r\nx123!@#'

    Chunked data cut off part way through:
    >>> c=ChunkedLineReader(StringIO.StringIO("4\r\n1234\r\n4\r\n12"));c.read()+c.read()
    '123412'
    """

    allChunksRead = False
    notChunked = False
    raiseChunkedDataExceptions = False # if False, we'll use best-guess fallback for parse errors

    def _fillbuff(self, chunkSize = None):
        if self.notChunked:
            return LineReader._fillbuff(self, chunkSize)

        if self.allChunksRead:
            return

        if not self.buff or self.buff.pos >= self.buff.len:
            lengthHeader = self.stream.readline(64)
            data = ''

            try:
                # decode length header
                try:
                    chunkSize = int(lengthHeader.strip().split(';')[0], 16)
                except ValueError:
                    raise ChunkedDataException("Couldn't decode length header '%s'" % lengthHeader)

                if chunkSize:
                    # read chunk
                    while len(data) < chunkSize:
                        newData = self.stream.read(chunkSize - len(data))

                        # if we unexpectedly run out of data, either raise an exception or just stop reading, assuming file was cut off
                        if not newData:
                            if self.raiseChunkedDataExceptions:
                                raise ChunkedDataException("Ran out of data before end of chunk")
                            else:
                                chunkSize = len(data)
                                self.allChunksRead = True

                        data += newData

                    # if we successfully read a block without running out, it should end in \r\n
                    if not self.allChunksRead:
                        clrf = self.stream.read(2)
                        if clrf != '\r\n':
                            raise ChunkedDataException("Chunk terminator not found.")

                    if self.decomp:
                        data = self.decomp.decompress(data)
                else:
                    # chunkSize 0 indicates end of file
                    self.allChunksRead = True
                    data = ''

                self._process_read(data)
            except ChunkedDataException:
                if self.raiseChunkedDataExceptions:
                    raise
                # Can't parse the data as chunked.
                # It's possible that non-chunked data is set with a Transfer-Encoding: chunked
                # Treat this as non-chunk encoded from here on
                self._process_read(lengthHeader+data)
                self.notChunked = True


#=================================================================
import utils
if __name__ == "__main__" or utils.enable_doctests():
    import os
    import pprint

    testloader = ArchiveLoader()

    def loadTestArchive(test_file, offset, length):
        path = os.path.dirname(os.path.realpath(__file__)) + '/../test/' + test_file

        archive = testloader.load(path, offset, length)
        pprint.pprint((archive.type, archive.rec_headers, archive.status_headers))

    import doctest
    doctest.testmod()

