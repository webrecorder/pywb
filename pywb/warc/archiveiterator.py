from pywb.utils.timeutils import iso_date_to_timestamp
from pywb.utils.bufferedreaders import DecompressingBufferedReader
from pywb.utils.canonicalize import canonicalize
from pywb.utils.loaders import extract_post_query, append_post_query

from recordloader import ArcWarcRecordLoader

import hashlib
import base64

import re
import sys

try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict


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

    INC_RECORD = """\
    WARNING: Record not followed by newline, perhaps Content-Length is invalid
    Offset: {0}
    Remainder: {1}
"""


    def __init__(self, fileobj, no_record_parse=False,
                 verify_http=False):
        self.fh = fileobj

        self.loader = ArcWarcRecordLoader(verify_http=verify_http)
        self.reader = None

        self.offset = 0
        self.known_format = None

        self.member_info = None
        self.no_record_parse = no_record_parse

    def iter_records(self, block_size=16384):
        """ iterate over each record
        """

        decomp_type = 'gzip'

        self.reader = DecompressingBufferedReader(self.fh,
                                                  block_size=block_size)
        self.offset = self.fh.tell()

        self.next_line = None

        raise_invalid_gzip = False
        empty_record = False

        while True:
            try:
                curr_offset = self.fh.tell()
                record = self._next_record(self.next_line)
                if raise_invalid_gzip:
                    self._raise_invalid_gzip_err()

                yield record

            except EOFError:
                empty_record = True

            self.read_to_end(record)

            if self.reader.decompressor:
                # if another gzip member, continue
                if self.reader.read_next_member():
                    continue

                # if empty record, then we're done
                elif empty_record:
                    break

                # otherwise, probably a gzip
                # containing multiple non-chunked records
                # raise this as an error
                else:
                    raise_invalid_gzip = True

            # non-gzip, so we're done
            elif empty_record:
                break

    def _raise_invalid_gzip_err(self):
        """ A gzip file with multiple ARC/WARC records, non-chunked
        has been detected. This is not valid for replay, so notify user
        """
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

          if first line read is not blank, likely error in WARC/ARC,
          display a warning
        """
        empty_size = 0
        first_line = True

        while True:
            line = self.reader.readline()
            if len(line) == 0:
                return None, empty_size

            stripped = line.rstrip()

            if stripped == '' or first_line:
                empty_size += len(line)

                if stripped != '':
                    # if first line is not blank,
                    # likely content-length was invalid, display warning
                    err_offset = self.fh.tell() - self.reader.rem_length() - empty_size
                    sys.stderr.write(self.INC_RECORD.format(err_offset, line))

                first_line = False
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
                                                 self.known_format,
                                                 self.no_record_parse)

        self.member_info = None

        # Track known format for faster parsing of other records
        self.known_format = record.format

        return record


#=================================================================
class ArchiveIndexEntryMixin(object):
    MIME_RE = re.compile('[; ]')

    def reset_entry(self):
        self['urlkey'] = ''
        self['metadata'] = ''

    def extract_mime(self, mime, def_mime='unk'):
        """ Utility function to extract mimetype only
        from a full content type, removing charset settings
        """
        self['mime'] = def_mime
        if mime:
            self['mime'] = self.MIME_RE.split(mime, 1)[0]

    def extract_status(self, status_headers):
        """ Extract status code only from status line
        """
        self['status'] = status_headers.get_statuscode()
        if not self['status']:
            self['status'] = '-'
        elif self['status'] == '204' and 'Error' in status_headers.statusline:
            self['status'] = '-'

    def set_rec_info(self, offset, length, digest):
        if digest:
            self['digest'] = digest

        self['length'] = str(length)
        self['offset'] = str(offset)

    def merge_request_data(self, other, options):
        surt_ordered = options.get('surt_ordered', True)

        if other.record.rec_type != 'request':
            return False

        # two requests, not correct
        if self.record.rec_type == 'request':
            return False

        # merge POST/PUT body query
        post_query = other.get('_post_query')
        if post_query:
            url = append_post_query(self['url'], post_query)
            self['urlkey'] = canonicalize(url, surt_ordered)
            other['urlkey'] = self['urlkey']

        referer = other.record.status_headers.get_header('referer')
        if referer:
            self['_referer'] = referer

        return True


#=================================================================
class DefaultRecordIter(object):
    def __init__(self, **options):
        self.options = options
        self.entry_cache = {}

    def _create_index_entry(self, rec_type):
        try:
            entry = self.entry_cache[rec_type]
            entry.reset_entry()
        except:
            if self.options.get('cdxj'):
                entry = OrderedArchiveIndexEntry()
            else:
                entry = ArchiveIndexEntry()

            self.entry_cache[rec_type] = entry

        return entry

    def create_record_iter(self, arcv_iter):
        append_post = self.options.get('append_post')
        include_all = self.options.get('include_all')
        block_size = self.options.get('block_size', 16384)
        surt_ordered = self.options.get('surt_ordered', True)
        minimal = self.options.get('minimal')
        append_post = self.options.get('append_post')

        if append_post and minimal:
            raise Exception('Sorry, minimal index option and ' +
                            'append POST options can not be used together')

        for record in arcv_iter.iter_records(block_size):
            entry = None

            if not include_all and not minimal and (record.status_headers.get_statuscode() == '-'):
                continue

            if record.format == 'warc':
                if (record.rec_type in ('request', 'warcinfo') and
                     not include_all and
                     not append_post):
                    continue

                elif (not include_all and
                      record.content_type == 'application/warc-fields'):
                    continue

                entry = self.parse_warc_record(record)
            elif record.format == 'arc':
                entry = self.parse_arc_record(record)

            if not entry:
                continue

            if entry.get('url') and not entry.get('urlkey'):
                entry['urlkey'] = canonicalize(entry['url'], surt_ordered)

            compute_digest = False

            if (entry.get('digest', '-') == '-' and
                record.rec_type not in ('revisit', 'request', 'warcinfo')):

                compute_digest = True

            elif not minimal and record.rec_type == 'request' and append_post:
                method = record.status_headers.protocol
                len_ = record.status_headers.get_header('Content-Length')

                post_query = extract_post_query(method,
                                                entry.get('mime'),
                                                len_,
                                                record.stream)

                entry['_post_query'] = post_query

            arcv_iter.read_to_end(record, compute_digest)
            entry.set_rec_info(*arcv_iter.member_info)
            entry.record = record

            yield entry

    def join_request_records(self, entry_iter):
        prev_entry = None

        for entry in entry_iter:
            if not prev_entry:
                prev_entry = entry
                continue

            # check for url match
            if (entry['url'] != prev_entry['url']):
                pass

            # check for concurrency also
            elif (entry.record.rec_headers.get_header('WARC-Concurrent-To') !=
                  prev_entry.record.rec_headers.get_header('WARC-Record-ID')):
                pass

            elif (entry.merge_request_data(prev_entry, self.options) or
                  prev_entry.merge_request_data(entry, self.options)):
                yield prev_entry
                yield entry
                prev_entry = None
                continue

            yield prev_entry
            prev_entry = entry

        if prev_entry:
            yield prev_entry


    #=================================================================
    def parse_warc_record(self, record):
        """ Parse warc record
        """

        entry = self._create_index_entry(record.rec_type)

        if record.rec_type == 'warcinfo':
            entry['url'] = record.rec_headers.get_header('WARC-Filename')
            entry['urlkey'] = entry['url']
            entry['_warcinfo'] = record.stream.read(record.length)
            return entry

        entry['url'] = record.rec_headers.get_header('WARC-Target-Uri')

        # timestamp
        entry['timestamp'] = iso_date_to_timestamp(record.rec_headers.
                                                   get_header('WARC-Date'))

        # mime
        if record.rec_type == 'revisit':
            entry['mime'] = 'warc/revisit'
        elif self.options.get('minimal'):
            entry['mime'] = '-'
        else:
            def_mime = '-' if record.rec_type == 'request' else 'unk'
            entry.extract_mime(record.status_headers.
                               get_header('Content-Type'),
                               def_mime)

        # status -- only for response records (by convention):
        if record.rec_type == 'response' and not self.options.get('minimal'):
            entry.extract_status(record.status_headers)
        else:
            entry['status'] = '-'

        # digest
        digest = record.rec_headers.get_header('WARC-Payload-Digest')
        entry['digest'] = digest
        if digest and digest.startswith('sha1:'):
            entry['digest'] = digest[len('sha1:'):]

        elif not entry.get('digest'):
            entry['digest'] = '-'

        # optional json metadata, if present
        metadata = record.rec_headers.get_header('WARC-Json-Metadata')
        if metadata:
            entry['metadata'] = metadata

        return entry


    #=================================================================
    def parse_arc_record(self, record):
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

        entry = self._create_index_entry(record.rec_type)
        entry['url'] = url

        # timestamp
        entry['timestamp'] = record.rec_headers.get_header('archive-date')
        if len(entry['timestamp']) > 14:
            entry['timestamp'] = entry['timestamp'][:14]

        if not self.options.get('minimal'):
            # mime
            entry.extract_mime(record.rec_headers.get_header('content-type'))

            # status
            entry.extract_status(record.status_headers)

        # digest
        entry['digest'] = '-'

        return entry

    def __call__(self, fh):
        aiter = ArchiveIterator(fh, self.options.get('minimal', False),
                                    self.options.get('verify_http', False))

        entry_iter = self.create_record_iter(aiter)

        if self.options.get('append_post'):
            entry_iter = self.join_request_records(entry_iter)

        for entry in entry_iter:
            if (entry.record.rec_type in ('request', 'warcinfo') and
                 not self.options.get('include_all')):
                continue

            yield entry

class ArchiveIndexEntry(ArchiveIndexEntryMixin, dict):
    pass

class OrderedArchiveIndexEntry(ArchiveIndexEntryMixin, OrderedDict):
    pass
