from pywb.utils.timeutils import iso_date_to_timestamp
from pywb.warc.recordloader import ArcWarcRecordLoader, ArchiveLoadFailed
from pywb.utils.wbexception import NotFoundException

import six


#=================================================================
class ResolvingLoader(object):
    MISSING_REVISIT_MSG = 'Original for revisit record could not be loaded'

    def __init__(self, path_resolvers, record_loader=ArcWarcRecordLoader(), no_record_parse=False):
        self.path_resolvers = path_resolvers
        self.record_loader = record_loader
        self.no_record_parse = no_record_parse

    def __call__(self, cdx, failed_files, cdx_loader, *args, **kwargs):
        headers_record, payload_record = self.load_headers_and_payload(cdx, failed_files, cdx_loader)

        # Default handling logic when loading http status/headers

        # special case: set header to payload if old-style revisit
        # with missing header
        if not headers_record:
            headers_record = payload_record
        elif headers_record != payload_record:
            # close remainder of stream as this record only used for
            # (already parsed) headers
            headers_record.stream.close()

            # special case: check if headers record is actually empty
            # (eg empty revisit), then use headers from revisit
            if not headers_record.status_headers.headers:
                headers_record = payload_record

        if not headers_record or not payload_record:
            raise ArchiveLoadFailed('Could not load ' + str(cdx))

        # ensure status line is valid from here
        headers_record.status_headers.validate_statusline('204 No Content')

        return (headers_record.status_headers, payload_record.stream)

    def load_headers_and_payload(self, cdx, failed_files, cdx_loader):
        """
        Resolve headers and payload for a given capture
        In the simple case, headers and payload are in the same record.
        In the case of revisit records, the payload and headers may be in
        different records.

        If the original has already been found, lookup original using
        orig. fields in cdx dict.
        Otherwise, call _load_different_url_payload() to get cdx index
        from a different url to find the original record.
        """
        has_curr = (cdx['filename'] != '-')
        #has_orig = (cdx.get('orig.filename', '-') != '-')
        orig_f = cdx.get('orig.filename')
        has_orig = orig_f and orig_f != '-'

        # load headers record from cdx['filename'] unless it is '-' (rare)
        headers_record = None
        if has_curr:
            headers_record = self._resolve_path_load(cdx, False, failed_files)

        # two index lookups
        # Case 1: if mimetype is still warc/revisit
        if cdx.get('mime') == 'warc/revisit' and headers_record:
            payload_record = self._load_different_url_payload(cdx,
                                                              headers_record,
                                                              failed_files,
                                                              cdx_loader)

        # single lookup cases
        # case 2: non-revisit
        elif (has_curr and not has_orig):
            payload_record = headers_record

        # case 3: identical url revisit, load payload from orig.filename
        elif (has_orig):
            payload_record = self._resolve_path_load(cdx, True, failed_files)

        return headers_record, payload_record


    def _resolve_path_load(self, cdx, is_original, failed_files):
        """
        Load specific record based on filename, offset and length
        fields in the cdx.
        If original=True, use the orig.* fields for the cdx

        Resolve the filename to full path using specified path resolvers

        If failed_files list provided, keep track of failed resolve attempts
        """

        if is_original:
            (filename, offset, length) = (cdx['orig.filename'],
                                          cdx['orig.offset'],
                                          cdx['orig.length'])
        else:
            (filename, offset, length) = (cdx['filename'],
                                          cdx['offset'],
                                          cdx.get('length', '-'))

        # optimization: if same file already failed this request,
        # don't try again
        if failed_files is not None and filename in failed_files:
            raise ArchiveLoadFailed('Skipping Already Failed', filename)

        any_found = False
        last_exc = None
        last_traceback = None
        for resolver in self.path_resolvers:
            possible_paths = resolver(filename, cdx)

            if not possible_paths:
                continue

            if isinstance(possible_paths, six.string_types):
                possible_paths = [possible_paths]

            for path in possible_paths:
                any_found = True
                try:
                    return (self.record_loader.
                             load(path, offset, length,
                               no_record_parse=self.no_record_parse))

                except Exception as ue:
                    last_exc = ue
                    import sys
                    last_traceback = sys.exc_info()[2]

        # Unsuccessful if reached here
        if failed_files is not None:
            failed_files.append(filename)

        if last_exc:
            #msg = str(last_exc.__class__.__name__)
            msg = str(last_exc)
        else:
            msg = 'Archive File Not Found'

        #raise ArchiveLoadFailed(msg, filename), None, last_traceback
        six.reraise(ArchiveLoadFailed, ArchiveLoadFailed(msg, filename), last_traceback)

    def _load_different_url_payload(self, cdx, headers_record,
                                    failed_files, cdx_loader):
        """
        Handle the case where a duplicate of a capture with same digest
        exists at a different url.

        If a cdx_server is provided, a query is made for matching
        url, timestamp and digest.

        Raise exception if no matches found.
        """

        ref_target_uri = (headers_record.rec_headers.
                          get_header('WARC-Refers-To-Target-URI'))

        target_uri = headers_record.rec_headers.get_header('WARC-Target-URI')

        # if no target uri, no way to find the original
        if not ref_target_uri:
            raise ArchiveLoadFailed(self.MISSING_REVISIT_MSG)

        ref_target_date = (headers_record.rec_headers.
                           get_header('WARC-Refers-To-Date'))

        if not ref_target_date:
            ref_target_date = cdx['timestamp']
        else:
            ref_target_date = iso_date_to_timestamp(ref_target_date)

        digest = cdx.get('digest', '-')

        try:
            orig_cdx_lines = self.load_cdx_for_dupe(ref_target_uri,
                                                    ref_target_date,
                                                    digest,
                                                    cdx_loader)
        except NotFoundException:
            raise ArchiveLoadFailed(self.MISSING_REVISIT_MSG)

        for orig_cdx in orig_cdx_lines:
            try:
                payload_record = self._resolve_path_load(orig_cdx, False,
                                                         failed_files)
                return payload_record

            except ArchiveLoadFailed as e:
                pass

        raise ArchiveLoadFailed(self.MISSING_REVISIT_MSG)

    def load_cdx_for_dupe(self, url, timestamp, digest, cdx_loader):
        """
        If a cdx_server is available, return response from server,
        otherwise empty list
        """
        if not cdx_loader:
            return iter([])

        filters = []

        filters.append('!mime:warc/revisit')

        if digest and digest != '-':
            filters.append('digest:' + digest)

        params = dict(url=url,
                      closest=timestamp,
                      filter=filters)

        return cdx_loader(params)
