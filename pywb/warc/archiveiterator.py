from pywb.utils.timeutils import iso_date_to_timestamp
from pywb.utils.bufferedreaders import DecompressingBufferedReader
from pywb.utils.canonicalize import canonicalize
from pywb.utils.loaders import extract_post_query, append_post_query

from recordloader import ArcWarcRecordLoader

import hashlib
import base64

import re


#=================================================================
class ArchiveIterator(object):
    """ Iterate over records in WARC and ARC files, both gzip chunk
    compressed and uncompressed

    The indexer will automatically detect format, and decompress
    if necessary.

    """

    GZIP_ERR_MSG = """
    ERROR: Non-chunked gzip file detected, gzip block continues
    beyond single record.

    This file is probably not a multi-chunk gzip but a single gzip file.

    To allow seek, a gzipped {1} must have each record compressed into
    a single gzip chunk and concatenated together.

    This file is likely still valid and you can use it by decompressing it:

    gunzip myfile.{0}.gz

    You can then also use the 'warc2warc' tool from the 'warc-tools'
    package which will create a properly chunked gzip file:

    warc2warc -Z myfile.{0} > myfile.{0}.gz
    """

    def __init__(self, fileobj):
        self.fh = fileobj

        self.loader = ArcWarcRecordLoader()
        self.reader = None

        self.offset = 0
        self.known_format = None

        self.member_info = None

    def iter_records(self, block_size=16384):
        """ iterate over each record
        """

        decomp_type = 'gzip'

        self.reader = DecompressingBufferedReader(self.fh,
                                                  block_size=block_size)
        self.offset = self.fh.tell()

        self.next_line = None

        is_valid = True

        while True:
            try:
                record = self._next_record(self.next_line)
                if not is_valid:
                    self._raise_err()

                yield record
            except EOFError:
                break

            self.read_to_end(record)

            if self.reader.decompressor:
                is_valid = self.reader.read_next_member()

    def _raise_err(self):
        frmt = 'warc/arc'
        if self.known_format:
            frmt = self.known_format

        frmt_up = frmt.upper()

        msg = self.GZIP_ERR_MSG.format(frmt, frmt_up)
        raise Exception(msg)

    def _consume_blanklines(self):
        """ Consume blank lines that are between records
        - For warcs, there are usually 2
        - For arcs, may be 1 or 0
        - For block gzipped files, these are at end of each gzip envelope
          and are included in record length which is the full gzip envelope
        - For uncompressed, they are between records and so are NOT part of
          the record length

          count empty_size so that it can be substracted from
          the record length for uncompressed
        """
        empty_size = 0
        while True:
            line = self.reader.readline()
            if len(line) == 0:
                return None, empty_size

            if line.rstrip() == '':
                empty_size += len(line)
                continue

            return line, empty_size

    def read_to_end(self, record, compute_digest=False):
        """ Read remainder of the stream
        If a digester is included, update it
        with the data read
        """

        # already at end of this record, don't read until it is consumed
        if self.member_info:
            return None

        if compute_digest:
            digester = hashlib.sha1()
        else:
            digester = None

        num = 0
        curr_offset = self.offset

        while True:
            b = record.stream.read(8192)
            if not b:
                break
            num += len(b)
            if digester:
                digester.update(b)

        """
        - For compressed files, blank lines are consumed
          since they are part of record length
        - For uncompressed files, blank lines are read later,
          and not included in the record length
        """
        #if self.reader.decompressor:
        self.next_line, empty_size = self._consume_blanklines()

        self.offset = self.fh.tell() - self.reader.rem_length()
        #if self.offset < 0:
        #    raise Exception('Not Gzipped Properly')

        if self.next_line:
            self.offset -= len(self.next_line)

        length = self.offset - curr_offset

        if not self.reader.decompressor:
            length -= empty_size

        if compute_digest:
            digest = base64.b32encode(digester.digest())
        else:
            digest = None

        self.member_info = (curr_offset, length, digest)
        #return self.member_info
        #return next_line

    def _next_record(self, next_line):
        """ Use loader to parse the record from the reader stream
        Supporting warc and arc records
        """
        record = self.loader.parse_record_stream(self.reader,
                                                 next_line,
                                                 self.known_format)

        self.member_info = None

        # Track known format for faster parsing of other records
        self.known_format = record.format

        return record


#=================================================================
class ArchiveIndexEntry(object):
    MIME_RE = re.compile('[; ]')

    def __init__(self):
        self.url = None
        self.key = None
        self.digest = '-'

    def extract_mime(self, mime, def_mime='unk'):
        """ Utility function to extract mimetype only
        from a full content type, removing charset settings
        """
        self.mime = def_mime
        if mime:
            self.mime = self.MIME_RE.split(mime, 1)[0]

    def extract_status(self, status_headers):
        """ Extract status code only from status line
        """
        self.status = status_headers.get_statuscode()
        if not self.status:
            self.status = '-'
        if self.status == '204' and 'Error' in status_headers.statusline:
            self.status = '-'

    def set_rec_info(self, offset, length, digest):
        self.offset = str(offset)
        self.length = str(length)
        if digest:
            self.digest = digest

    def merge_request_data(self, other, options):
        surt_ordered = options.get('surt_ordered', True)

        if other.record.rec_type != 'request':
            return False

        # two requests, not correct
        if self.record.rec_type == 'request':
            return False

        # merge POST/PUT body query
        if hasattr(other, 'post_query'):
            url = append_post_query(self.url, other.post_query)
            self.key = canonicalize(url, surt_ordered)
            other.key = self.key

        referer = other.record.status_headers.get_header('referer')
        if referer:
            self.referer = referer

        return True


#=================================================================
def create_record_iter(arcv_iter, options):
    append_post = options.get('append_post')
    include_all = options.get('include_all')
    block_size = options.get('block_size', 16384)

    for record in arcv_iter.iter_records(block_size):
        entry = None

        if not include_all and (record.status_headers.get_statuscode() == '-'):
            continue

        if record.format == 'warc':
            if (record.rec_type in ('request', 'warcinfo') and
                 not include_all and
                 not append_post):
                continue

            elif (not include_all and
                  record.content_type == 'application/warc-fields'):
                continue

            entry = parse_warc_record(record)
        elif record.format == 'arc':
            entry = parse_arc_record(record)

        if not entry:
            continue

        if entry.url and not entry.key:
            entry.key = canonicalize(entry.url,
                                     options.get('surt_ordered', True))

        compute_digest = False

        if (entry.digest == '-' and
             record.rec_type not in ('revisit', 'request', 'warcinfo')):

            compute_digest = True

        elif record.rec_type == 'request' and options.get('append_post'):
            method = record.status_headers.protocol
            len_ = record.status_headers.get_header('Content-Length')

            post_query = extract_post_query(method,
                                            entry.mime,
                                            len_,
                                            record.stream)

            entry.post_query = post_query

        #entry.set_rec_info(*arcv_iter.read_to_end(record, compute_digest))
        arcv_iter.read_to_end(record, compute_digest)
        entry.set_rec_info(*arcv_iter.member_info)
        entry.record = record

        yield entry


#=================================================================
def join_request_records(entry_iter, options):
    prev_entry = None

    for entry in entry_iter:
        if not prev_entry:
            prev_entry = entry
            continue

        # check for url match
        if (entry.url != prev_entry.url):
            pass

        # check for concurrency also
        elif (entry.record.rec_headers.get_header('WARC-Concurrent-To') !=
              prev_entry.record.rec_headers.get_header('WARC-Record-ID')):
            pass

        elif (entry.merge_request_data(prev_entry, options) or
              prev_entry.merge_request_data(entry, options)):
            yield prev_entry
            yield entry
            prev_entry = None
            continue

        yield prev_entry
        prev_entry = entry

    if prev_entry:
        yield prev_entry


#=================================================================
def parse_warc_record(record):
    """ Parse warc record
    """

    entry = ArchiveIndexEntry()

    if record.rec_type == 'warcinfo':
        entry.url = record.rec_headers.get_header('WARC-Filename')
        entry.key = entry.url
        entry.warcinfo = record.stream.read(record.length)
        return entry

    entry.url = record.rec_headers.get_header('WARC-Target-Uri')

    # timestamp
    entry.timestamp = iso_date_to_timestamp(record.rec_headers.
                                            get_header('WARC-Date'))

    # mime
    if record.rec_type == 'revisit':
        entry.mime = 'warc/revisit'
    else:
        def_mime = '-' if record.rec_type == 'request' else 'unk'
        entry.extract_mime(record.status_headers.
                           get_header('Content-Type'),
                           def_mime)

    # status -- only for response records (by convention):
    if record.rec_type == 'response':
        entry.extract_status(record.status_headers)
    else:
        entry.status = '-'

    # digest
    entry.digest = record.rec_headers.get_header('WARC-Payload-Digest')
    if entry.digest and entry.digest.startswith('sha1:'):
        entry.digest = entry.digest[len('sha1:'):]

    if not entry.digest:
        entry.digest = '-'

    return entry


#=================================================================
def parse_arc_record(record):
    """ Parse arc record
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

    entry = ArchiveIndexEntry()
    entry.url = url

    # timestamp
    entry.timestamp = record.rec_headers.get_header('archive-date')
    if len(entry.timestamp) > 14:
        entry.timestamp = entry.timestamp[:14]

    # status
    entry.extract_status(record.status_headers)

    # mime
    entry.extract_mime(record.rec_headers.get_header('content-type'))

    # digest
    entry.digest = '-'

    return entry


#=================================================================
def create_index_iter(fh, **options):
    aiter = ArchiveIterator(fh)

    entry_iter = create_record_iter(aiter, options)

    if options.get('append_post'):
        entry_iter = join_request_records(entry_iter, options)

    for entry in entry_iter:
        if (entry.record.rec_type in ('request', 'warcinfo') and
             not options.get('include_all')):
            continue

        yield entry
