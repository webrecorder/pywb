from gzip2 import GzipFile

from pywb.utils.timeutils import iso_date_to_timestamp
from recordloader import ArcWarcRecordLoader

import surt

import hashlib
import base64
import re

from collections import OrderedDict


#=================================================================
class ArchiveIndexer(object):
    def __init__(self, filename):
        self.filename = filename
        self.loader = ArcWarcRecordLoader()

    def make_index(self):
        self.fh = open(self.filename, 'r')
        gf = GzipFile(fileobj=self.fh)

        member = gf.read_member()
        offset = self.fh.tell()

        print ' CDX N b a m s k r M S V g'

        while member:
            offset = self._process_member(member, offset)
            member = gf.read_member()

    def _parse_warc_record(self, record):
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

        result = OrderedDict()
        result['urlkey'] = surt.surt(url)
        result['timestamp'] = timestamp
        result['url'] = url
        result['mimetype'] = mime
        result['statuscode'] = status
        result['digest'] = digest
        return result

    def _parse_arc_record(self, record):
        if record.rec_type == 'arc_header':
            return None

        url = record.rec_headers.get_header('uri')
        status = record.status_headers.statusline.split(' ')[0]
        mime = record.rec_headers.get_header('content-type')
        mime = self._extract_mime(mime)

        result = OrderedDict()
        result['urlkey'] = surt.surt(url)
        result['timestamp'] = record.rec_headers.get_header('archive-date')
        result['url'] = url
        result['mimetype'] = mime
        result['statuscode'] = status
        result['digest'] = '-'
        return result

    MIME_RE = re.compile('[; ]')

    def _extract_mime(self, mime):
        if mime:
            mime = self.MIME_RE.split(mime, 1)[0]
        if not mime:
            mime = 'unk'
        return mime

    def _process_member(self, member, offset):
        record = self.loader.parse_record_stream(member)

        if record.format == 'warc':
            result = self._parse_warc_record(record)
        elif record.format == 'arc':
            result = self._parse_arc_record(record)

        if not result:
            self.read_rest(member)
            new_offset = self.fh.tell()
            return new_offset

        result['redirect'] = '-'
        result['metaflags'] = '-'

        #if result['mimetype'] != 'warc/revisit':
        #    result['digest'] = '-'

        if result['digest'] == '-':
            digester = hashlib.sha1()
            self.read_rest(record.stream, digester)
            result['digest'] = base64.b32encode(digester.digest())

        self.read_rest(member)

        new_offset = self.fh.tell()
        length = new_offset - offset

        result['length'] = str(length)
        result['offset'] = str(offset)
        result['filename'] = self.filename

        print ' '.join(v for k, v in result.iteritems())

        return new_offset

    def read_rest(self, member, digester=None):
        while True:
            b = member.read(8192)
            if not b:
                break
            if digester:
                digester.update(b)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        index = ArchiveIndexer(sys.argv[1])
        index.make_index()
