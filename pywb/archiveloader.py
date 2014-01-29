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
    def __init__(self, hmac = None, hmac_duration = 30):
        self.hmac = hmac
        self.hmac_duration = hmac_duration

    def load(self, url, offset, length):
        if length > 0:
            range_header = 'bytes={0}-{1}'.format(offset, offset + length - 1)
        else:
            range_header = 'bytes={0}-'.format(offset)

        headers = {}
        headers['Range'] = range_header

        if self.hmac:
            headers['Cookie'] = self.hmac(self.hmac_duration)

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
    >>> load_test_archive('example.warc.gz', '333', '1043')
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
      

    >>> load_test_archive('example.warc.gz', '1864', '553')
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
    def create_default_loaders():
        http = HttpReader()
        file = FileReader()
        return {
                'http': http,
                'https': http,
                'file': file,
                '': file
               }


    def __init__(self, loaders = {}, chunk_size = 8192):
        self.loaders = loaders if loaders else ArchiveLoader.create_default_loaders()
        self.chunk_size = chunk_size

        self.arc_parser = ARCHeadersParser(ArchiveLoader.ARC_HEADERS)
        self.warc_parser = StatusAndHeadersParser(['WARC/1.0', 'WARC/0.17', 'WARC/0.18'])
        self.http_parser = StatusAndHeadersParser(['HTTP/1.0', 'HTTP/1.1'])

    def load(self, url, offset, length):
        url_parts = urlparse.urlsplit(url)

        try:
            loader = self.loaders.get(url_parts.scheme)
        except Exception:
            raise wbexceptions.UnknownLoaderProtocolException(url)

        the_format = None

        for ext, iformat in ArchiveLoader.FORMAT_MAP.iteritems():
            if url.endswith(ext):
                the_format = iformat
                break

        if the_format is None:
            raise wbexceptions.UnknownArchiveFormatException(url)

        (a_format, is_gzip) = the_format

        decomp = utils.create_decompressor() if is_gzip else None

        try:
            length = int(length)
        except:
            length = -1


        raw = loader.load(url, long(offset), length)

        stream = LineReader(raw, length, self.chunk_size, decomp)

        if a_format == 'arc':
            rec_headers = self.arc_parser.parse(stream)
            rec_type = 'response'
            empty = (rec_headers.get_header('length') == 0)

        elif a_format == 'warc':
            rec_headers = self.warc_parser.parse(stream)
            rec_type = rec_headers.get_header('WARC-Type')
            empty = (rec_headers.get_header('Content-Length') == '0')

        # special case: empty w/arc record (hopefully a revisit)
        if empty:
            status_headers = StatusAndHeaders('204 No Content', [])

        # special case: warc records that are not expected to have http headers
        # attempt to add 200 status and content-type
        elif rec_type == 'metadata' or rec_type == 'resource':
            status_headers = StatusAndHeaders('200 OK', [('Content-Type', rec_headers.get_header('Content-Type'))])

        # special case: http 0.9 response, no status or headers
        #elif rec_type == 'response':
        #    content_type = rec_headers.get_header('Content-Type')
        #    if content_type and (';version=0.9' in content_type):
        #        status_headers = StatusAndHeaders('200 OK', [])

        # response record: parse HTTP status and headers!
        else:
            #(statusline, http_headers) = self.parse_http_headers(stream)
            status_headers = self.http_parser.parse(stream)

        return WBArchiveRecord((a_format, rec_type), rec_headers, stream, status_headers)


#=================================================================
class StatusAndHeadersParser:
    def __init__(self, statuslist):
        self.statuslist = statuslist

    def parse(self, stream):
        statusline = stream.readline().rstrip()

        protocol_status = utils.split_prefix(statusline, self.statuslist)

        if not protocol_status:
            raise wbexceptions.InvalidArchiveRecordException('Expected Status Line, Found: ' + statusline)

        headers = []

        line = stream.readline().rstrip()
        while line and line != '\r\n':
            name, value = line.split(':', 1)
            header = (name, value.strip())
            headers.append(header)
            line = stream.readline().rstrip()

        return StatusAndHeaders(statusline = protocol_status[1].strip(), headers = headers, protocol = protocol_status[0])

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
    def __init__(self, stream, max_len = 0, chunk_size = 1024, decomp = None):
        self.stream = stream
        self.chunk_size = chunk_size
        self.decomp = decomp
        self.buff = None
        self.num_read = 0
        self.max_len = max_len

    def _fillbuff(self, chunk_size = None):
        if not chunk_size:
            chunk_size = self.chunk_size

        if not self.buff or self.buff.pos >= self.buff.len:
            to_read =  min(self.max_len - self.num_read, self.chunk_size) if (self.max_len > 0) else self.chunk_size
            data = self.stream.read(to_read)
            self._process_read(data)

    def _process_read(self, data):
        self.num_read += len(data)

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

    all_chunks_read = False
    not_chunked = False
    raise_chunked_data_exceptions = False # if False, we'll use best-guess fallback for parse errors

    def _fillbuff(self, chunk_size = None):
        if self.not_chunked:
            return LineReader._fillbuff(self, chunk_size)

        if self.all_chunks_read:
            return

        if not self.buff or self.buff.pos >= self.buff.len:
            length_header = self.stream.readline(64)
            data = ''

            try:
                # decode length header
                try:
                    chunk_size = int(length_header.strip().split(';')[0], 16)
                except ValueError:
                    raise ChunkedDataException("Couldn't decode length header '%s'" % length_header)

                if chunk_size:
                    # read chunk
                    while len(data) < chunk_size:
                        new_data = self.stream.read(chunk_size - len(data))

                        # if we unexpectedly run out of data, either raise an exception or just stop reading, assuming file was cut off
                        if not new_data:
                            if self.raise_chunked_data_exceptions:
                                raise ChunkedDataException("Ran out of data before end of chunk")
                            else:
                                chunk_size = len(data)
                                self.all_chunks_read = True

                        data += new_data

                    # if we successfully read a block without running out, it should end in \r\n
                    if not self.all_chunks_read:
                        clrf = self.stream.read(2)
                        if clrf != '\r\n':
                            raise ChunkedDataException("Chunk terminator not found.")

                    if self.decomp:
                        data = self.decomp.decompress(data)
                else:
                    # chunk_size 0 indicates end of file
                    self.all_chunks_read = True
                    data = ''

                self._process_read(data)
            except ChunkedDataException:
                if self.raise_chunked_data_exceptions:
                    raise
                # Can't parse the data as chunked.
                # It's possible that non-chunked data is set with a Transfer-Encoding: chunked
                # Treat this as non-chunk encoded from here on
                self._process_read(length_header + data)
                self.not_chunked = True


#=================================================================
import utils
if __name__ == "__main__" or utils.enable_doctests():
    import os
    import pprint

    testloader = ArchiveLoader()

    def load_test_archive(test_file, offset, length):
        path = os.path.dirname(os.path.realpath(__file__)) + '/../test/' + test_file

        archive = testloader.load(path, offset, length)
        pprint.pprint((archive.type, archive.rec_headers, archive.status_headers))

    import doctest
    doctest.testmod()

