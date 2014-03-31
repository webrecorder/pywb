from pywb.utils.timeutils import iso_date_to_timestamp
from pywb.utils.bufferedreaders import DecompressingBufferedReader

from recordloader import ArcWarcRecordLoader

import surt
import hashlib
import base64

import re
import sys

from bisect import insort


#=================================================================
class ArchiveIndexer(object):
    """ Generate a CDX index for WARC and ARC files, both gzip chunk
    compressed and uncompressed

    The indexer will automatically detect format, and decompress
    if necessary
    """
    def __init__(self, fileobj, filename, out=sys.stdout, sort=False):
        self.fh = fileobj
        self.filename = filename
        self.loader = ArcWarcRecordLoader()
        self.offset = 0
        self.known_format = None

        if not out:
            out = sys.stdout

        if sort:
            self.writer = SortedCDXWriter(out)
        else:
            self.writer = CDXWriter(out)

    def make_index(self):
        """ Output a cdx index!
        """

        decomp_type = 'gzip'
        block_size = 16384

        reader = DecompressingBufferedReader(self.fh,
                                             block_size=block_size,
                                             decomp_type=decomp_type)
        self.offset = self.fh.tell()
        next_line = None

        self.writer.start()

        try:
            while True:
                try:
                    record = self._process_reader(reader, next_line)
                except EOFError:
                    break

                # for non-compressed, consume blank lines here
                if not reader.decompressor:
                    next_line = self._consume_blanklines(reader)
                    if next_line is None:
                        # at end of file
                        break

                # reset reader for next member
                else:
                    reader.read_next_member()
        finally:
            self.writer.end()

    def _consume_blanklines(self, reader):
        """ Consume blank lines that are between records
        - For warcs, there are usually 2
        - For arcs, may be 1 or 0
        - For block gzipped files, these are at end of each gzip envelope
          and are included in record length which is the full gzip envelope
        - For uncompressed, they are between records and so are NOT part of
          the record length
        """
        while True:
            line = reader.readline()
            if len(line) == 0:
                return None

            if line.rstrip() == '':
                self.offset = self.fh.tell() - reader.rem_length()
                continue

            return line

    def _read_to_record_end(self, reader, record):
        """ Read to end of record and update current offset,
        which is used to compute record length
        - For compressed files, blank lines are consumed
          since they are part of record length
        - For uncompressed files, blank lines are read later,
          and not included in the record length
        """

        if reader.decompressor:
            self._consume_blanklines(reader)

        self.offset = self.fh.tell() - reader.rem_length()

    def _process_reader(self, reader, next_line):
        """ Use loader to parse the record from the reader stream
        Supporting warc and arc records
        """
        record = self.loader.parse_record_stream(reader,
                                                 next_line,
                                                 self.known_format)

        # Track known format for faster parsing of other records
        self.known_format = record.format

        if record.format == 'warc':
            result = self._parse_warc_record(record)
        elif record.format == 'arc':
            result = self._parse_arc_record(record)

        if not result:
            self.read_rest(record.stream)
            self._read_to_record_end(reader, record)
            return record

        # generate digest if it doesn't exist and if not a revisit
        # if revisit, then nothing we can do here
        if result[-1] == '-' and record.rec_type != 'revisit':
            digester = hashlib.sha1()
            self.read_rest(record.stream, digester)
            result[-1] = base64.b32encode(digester.digest())
        else:
            num = self.read_rest(record.stream)

        result.append('- -')

        offset = self.offset
        self._read_to_record_end(reader, record)
        length = self.offset - offset

        result.append(str(length))
        result.append(str(offset))
        result.append(self.filename)

        self.writer.write(result)

        return record

    def _parse_warc_record(self, record):
        """ Parse warc record to be included in index, or
        return none if skipping this type of record
        """
        if record.rec_type not in ('response', 'revisit',
                                    'metadata', 'resource'):
            return None

        url = record.rec_headers.get_header('WARC-Target-Uri')

        timestamp = record.rec_headers.get_header('WARC-Date')
        timestamp = iso_date_to_timestamp(timestamp)

        digest = record.rec_headers.get_header('WARC-Payload-Digest')

        status = record.status_headers.statusline.split(' ')[0]

        if record.rec_type == 'revisit':
            mime = 'warc/revisit'
            status = '-'
        else:
            mime = record.status_headers.get_header('Content-Type')
            mime = self._extract_mime(mime)

        if digest and digest.startswith('sha1:'):
            digest = digest[len('sha1:'):]

        if not digest:
            digest = '-'

        return [surt.surt(url),
                timestamp,
                url,
                mime,
                status,
                digest]

    def _parse_arc_record(self, record):
        """ Parse arc record and return list of fields
        to include in index, or retur none if skipping this
        type of record
        """
        if record.rec_type == 'arc_header':
            return None

        url = record.rec_headers.get_header('uri')
        url = url.replace('\r', '%0D')
        url = url.replace('\n', '%0A')
        # replace formfeed
        url = url.replace('\x0c', '%0C')
        # replace nulls
        url = url.replace('\x00', '%00')

        timestamp = record.rec_headers.get_header('archive-date')
        if len(timestamp) > 14:
            timestamp = timestamp[:14]
        status = record.status_headers.statusline.split(' ')[0]
        mime = record.rec_headers.get_header('content-type')
        mime = self._extract_mime(mime)

        return [surt.surt(url),
                timestamp,
                url,
                mime,
                status,
                '-']

    MIME_RE = re.compile('[; ]')

    def _extract_mime(self, mime):
        """ Utility function to extract mimetype only
        from a full content type, removing charset settings
        """
        if mime:
            mime = self.MIME_RE.split(mime, 1)[0]
        if not mime:
            mime = 'unk'
        return mime

    def read_rest(self, reader, digester=None):
        """ Read remainder of the stream
        If a digester is included, update it
        with the data read
        """
        num = 0
        while True:
            b = reader.read(8192)
            if not b:
                break
            num += len(b)
            if digester:
                digester.update(b)
        return num


#=================================================================
class CDXWriter(object):
    def __init__(self, out):
        self.out = out

    def start(self):
        self.out.write(' CDX N b a m s k r M S V g\n')

    def write(self, line):
        self.out.write(' '.join(line) + '\n')

    def end(self):
        pass


#=================================================================
class SortedCDXWriter(object):
    def __init__(self, out):
        self.out = out
        self.sortlist = []

    def start(self):
        self.out.write(' CDX N b a m s k r M S V g\n')
        pass

    def write(self, line):
        line = ' '.join(line) + '\n'
        insort(self.sortlist, line)

    def end(self):
        self.out.write(''.join(self.sortlist))


#=================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print 'USAGE {0} <warc or file>'.format(sys.argv[0])
        exit(0)

    filename = sys.argv[1]

    if len(sys.argv) >= 3:
        sort = sys.argv[2] == '--sort'
    else:
        sort = False

    with open(filename, 'r') as fh:
         index = ArchiveIndexer(fh, filename, sort=sort)
         index.make_index()
