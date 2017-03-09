from pywb.utils.canonicalize import canonicalize
from pywb.utils.loaders import extract_post_query, append_post_query

from warcio.timeutils import iso_date_to_timestamp
from warcio.archiveiterator import ArchiveIterator

import hashlib
import base64
import six

import re
import sys

try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict


#=================================================================
class ArchiveIndexEntryMixin(object):
    MIME_RE = re.compile('[; ]')

    def __init__(self):
        super(ArchiveIndexEntryMixin, self).__init__()
        self.reset_entry()

    def reset_entry(self):
        self['urlkey'] = ''
        self['metadata'] = ''
        self.buffer = None
        self.record = None


    def extract_mime(self, mime, def_mime='unk'):
        """ Utility function to extract mimetype only
        from a full content type, removing charset settings
        """
        self['mime'] = def_mime
        if mime:
            self['mime'] = self.MIME_RE.split(mime, 1)[0]
            self['_content_type'] = mime

    def extract_status(self, status_headers):
        """ Extract status code only from status line
        """
        self['status'] = status_headers.get_statuscode()
        if not self['status']:
            self['status'] = '-'
        elif self['status'] == '204' and 'Error' in status_headers.statusline:
            self['status'] = '-'

    def set_rec_info(self, offset, length):
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

        referer = other.record.http_headers.get_header('referer')
        if referer:
            self['_referer'] = referer

        return True


#=================================================================
class DefaultRecordParser(object):
    def __init__(self, **options):
        self.options = options
        self.entry_cache = {}
        self.digester = None
        self.buff = None

    def _create_index_entry(self, rec_type):
        try:
            entry = self.entry_cache[rec_type]
            entry.reset_entry()
        except:
            if self.options.get('cdxj'):
                entry = OrderedArchiveIndexEntry()
            else:
                entry = ArchiveIndexEntry()

            # don't reuse when using append post
            # entry may be cached
            if not self.options.get('append_post'):
                self.entry_cache[rec_type] = entry

        return entry

    def begin_payload(self, compute_digest, entry):
        if compute_digest:
            self.digester = hashlib.sha1()
        else:
            self.digester = None

        self.entry = entry
        entry.buffer = self.create_payload_buffer(entry)

    def handle_payload(self, buff):
        if self.digester:
            self.digester.update(buff)

        if self.entry and self.entry.buffer:
            self.entry.buffer.write(buff)

    def end_payload(self, entry):
        if self.digester:
            entry['digest'] = base64.b32encode(self.digester.digest()).decode('ascii')

        self.entry = None

    def create_payload_buffer(self, entry):
        return None

    def create_record_iter(self, raw_iter):
        append_post = self.options.get('append_post')
        include_all = self.options.get('include_all')
        surt_ordered = self.options.get('surt_ordered', True)
        minimal = self.options.get('minimal')

        if append_post and minimal:
            raise Exception('Sorry, minimal index option and ' +
                            'append POST options can not be used together')

        for record in raw_iter:
            entry = None

            if not include_all and not minimal and (record.http_headers.get_statuscode() == '-'):
                continue

            if record.rec_type == 'arc_header':
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
                method = record.http_headers.protocol
                len_ = record.http_headers.get_header('Content-Length')

                post_query = extract_post_query(method,
                                                entry.get('_content_type'),
                                                len_,
                                                record.raw_stream)

                entry['_post_query'] = post_query

            entry.record = record

            self.begin_payload(compute_digest, entry)
            raw_iter.read_to_end(record, self.handle_payload)

            entry.set_rec_info(*raw_iter.member_info)
            self.end_payload(entry)

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
            entry['_warcinfo'] = record.raw_stream.read(record.length)
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
            entry.extract_mime(record.http_headers.
                               get_header('Content-Type'),
                               def_mime)

        # status -- only for response records (by convention):
        if record.rec_type == 'response' and not self.options.get('minimal'):
            entry.extract_status(record.http_headers)
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
            entry.extract_status(record.http_headers)

        # digest
        entry['digest'] = '-'

        return entry

    def __call__(self, fh):
        aiter = ArchiveIterator(fh, self.options.get('minimal', False),
                                    self.options.get('verify_http', False),
                                    self.options.get('arc2warc', False))

        entry_iter = self.create_record_iter(aiter)

        if self.options.get('append_post'):
            entry_iter = self.join_request_records(entry_iter)

        for entry in entry_iter:
            if (entry.record.rec_type in ('request', 'warcinfo') and
                 not self.options.get('include_all')):
                continue

            yield entry

    def open(self, filename):
        with open(filename, 'rb') as fh:
            for entry in self(fh):
                yield entry

class ArchiveIndexEntry(ArchiveIndexEntryMixin, dict):
    pass

class OrderedArchiveIndexEntry(ArchiveIndexEntryMixin, OrderedDict):
    pass


