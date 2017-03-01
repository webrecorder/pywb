from pywb.utils.bufferedreaders import DecompressingBufferedReader

from pywb.warc.recordloader import ArcWarcRecordLoader

import six
import sys


# ============================================================================
BUFF_SIZE = 16384


class ArchiveIterator(six.Iterator):
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
                 verify_http=False, arc2warc=False, block_size=BUFF_SIZE):

        self.fh = fileobj

        self.loader = ArcWarcRecordLoader(verify_http=verify_http,
                                          arc2warc=arc2warc)
        self.reader = None

        self.offset = 0
        self.known_format = None

        self.mixed_arc_warc = arc2warc

        self.member_info = None
        self.no_record_parse = no_record_parse

        self.reader = DecompressingBufferedReader(self.fh,
                                                  block_size=block_size)
        self.offset = self.fh.tell()

        self.next_line = None

        self._raise_invalid_gzip = False
        self._is_empty = False
        self._is_first = True
        self.last_record = None

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            if not self._is_first:
                self._finish_record()

            self._is_first = False

            try:
                self.last_record = self._next_record(self.next_line)
                if self._raise_invalid_gzip:
                    self._raise_invalid_gzip_err()

                return self.last_record

            except EOFError:
                self._is_empty = True

    def _finish_record(self):
        if self.last_record:
            self.read_to_end(self.last_record)

        if self.reader.decompressor:
            # if another gzip member, continue
            if self.reader.read_next_member():
                return

            # if empty record, then we're done
            elif self._is_empty:
                raise StopIteration()

            # otherwise, probably a gzip
            # containing multiple non-chunked records
            # raise this as an error
            else:
                self._raise_invalid_gzip = True

        # non-gzip, so we're done
        elif self._is_empty:
            raise StopIteration()

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

            if len(stripped) == 0 or first_line:
                empty_size += len(line)

                if len(stripped) != 0:
                    # if first line is not blank,
                    # likely content-length was invalid, display warning
                    err_offset = self.fh.tell() - self.reader.rem_length() - empty_size
                    sys.stderr.write(self.INC_RECORD.format(err_offset, line))

                first_line = False
                continue

            return line, empty_size

    def read_to_end(self, record, payload_callback=None):
        """ Read remainder of the stream
        If a digester is included, update it
        with the data read
        """

        # already at end of this record, don't read until it is consumed
        if self.member_info:
            return None

        num = 0
        curr_offset = self.offset

        while True:
            b = record.stream.read(BUFF_SIZE)
            if not b:
                break
            num += len(b)
            if payload_callback:
                payload_callback(b)

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

        self.member_info = (curr_offset, length)
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
        if not self.mixed_arc_warc:
            self.known_format = record.format

        return record


