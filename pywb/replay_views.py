import StringIO
from urllib2 import URLError
import chardet
import copy
import itertools

import archiveloader
from wbrequestresponse import WbResponse, StatusAndHeaders
import utils

from url_rewriter import UrlRewriter
from header_rewriter import HeaderRewriter
import html_rewriter
import regex_rewriters

import wbexceptions


#=================================================================
class ReplayView:
    def __init__(self, resolvers, archiveloader):
        self.resolvers = resolvers
        self.loader = archiveloader

    def __call__(self, wbrequest, cdx_lines, cdx_reader):
        last_e = None
        first = True

        # List of already failed w/arcs
        failed_files = []

        # Iterate over the cdx until find one that works
        # The cdx should already be sorted in closest-to-timestamp order (from the cdx server)
        for cdx in cdx_lines:
            try:
                # ability to intercept and redirect
                if first:
                    self._check_redir(wbrequest, cdx)
                    first = False

                response = self.do_replay(cdx, wbrequest, cdx_reader, failed_files)

                if response:
                    response.cdx = cdx
                    return response

            except wbexceptions.CaptureException as ce:
                import traceback
                traceback.print_exc()
                last_e = ce
                pass

        if last_e:
            raise last_e
        else:
            raise wbexceptions.UnresolvedArchiveFileException()

    def _check_redir(self, wbrequest, cdx):
        return None

    def _load(self, cdx, revisit, failed_files):
        if revisit:
            (filename, offset, length) = (cdx['orig.filename'], cdx['orig.offset'], cdx['orig.length'])
        else:
            (filename, offset, length) = (cdx['filename'], cdx['offset'], cdx['length'])

        #optimization: if same file already failed this request, don't try again
        if failed_files and filename in failed_files:
            raise wbexceptions.ArchiveLoadFailed(filename, 'Skipping Already Failed')

        any_found = False
        last_exc = None
        for resolver in self.resolvers:
            possible_paths = resolver(filename)

            if possible_paths:
                for path in possible_paths:
                    any_found = True
                    try:
                        return self.loader.load(path, offset, length)

                    except URLError as ue:
                        last_exc = ue
                        print last_exc
                        pass

        # Unsuccessful if reached here
        if failed_files:
           failed_files.append(filename)

        if not any_found:
            raise wbexceptions.UnresolvedArchiveFileException('Archive File Not Found: ' + filename)
        else:
            raise wbexceptions.ArchiveLoadFailed(filename, last_exc.reason if last_exc else '')


    def do_replay(self, cdx, wbrequest, cdx_reader, failed_files):
        has_curr = (cdx['filename'] != '-')
        has_orig = (cdx.get('orig.filename','-') != '-')

        # load headers record from cdx['filename'] unless it is '-' (rare)
        headers_record = self._load(cdx, False, failed_files) if has_curr else None

        # two index lookups
        # Case 1: if mimetype is still warc/revisit
        if cdx['mimetype'] == 'warc/revisit' and headers_record:
            payload_record = self._load_different_url_payload(wbrequest, cdx_reader, cdx, headers_record, failed_files)

        # single lookup cases
        # case 2: non-revisit
        elif (has_curr and not has_orig):
            payload_record = headers_record

        # case 3: identical url revisit, load payload from orig.filename
        elif (has_orig):
            payload_record = self._load(cdx, True, failed_files)

        # special case: set header to payload if old-style revisit with missing header
        if not headers_record:
            headers_record = payload_record
        elif headers_record != payload_record:
            # close remainder of stream as this record only used for (already parsed) headers
            headers_record.stream.close()

            # special case: check if headers record is actually empty (eg empty revisit), then use headers from revisit
            if not headers_record.status_headers.headers:
                headers_record = payload_record


        if not headers_record or not payload_record:
            raise wbexceptions.CaptureException('Invalid CDX' + str(cdx))


        response = WbResponse(headers_record.status_headers, self.create_stream_gen(payload_record.stream))
        response._stream = payload_record.stream
        return response



    # Handle the case where a duplicate of a capture with same digest exists at a different url
    # Must query the index at that url filtering by matching digest
    # Raise exception if no matches found
    def _load_different_url_payload(self, wbrequest, cdx_reader, cdx, headers_record, failed_files):
        ref_target_uri = headers_record.rec_headers.get_header('WARC-Refers-To-Target-URI')

        # Check for unresolved revisit error, if refers to target uri not present or same as the current url
        if not ref_target_uri or (ref_target_uri == headers_record.rec_headers.get_header('WARC-Target-URI')):
            raise wbexceptions.CaptureException('Missing Revisit Original' + str(cdx))

        ref_target_date = headers_record.rec_headers.get_header('WARC-Refers-To-Date')

        if not ref_target_date:
            ref_target_date = cdx['timestamp']
        else:
            ref_target_date = utils.iso_date_to_timestamp(ref_target_date)

        # clone WbRequest
        orig_wbreq = copy.copy(wbrequest)
        orig_wbreq.wb_url = copy.copy(orig_wbreq.wb_url)

        orig_wbreq.wb_url.url = ref_target_uri
        orig_wbreq.wb_url.timestamp = ref_target_date

        # Must also match digest
        orig_wbreq.query_filter.append('digest:' + cdx['digest'])

        orig_cdx_lines = cdx_reader.load_for_request(orig_wbreq, parsed_cdx = True)

        for cdx in orig_cdx_lines:
            try:
                #cdx = cdx_reader.CDXCaptureResult(cdx)
                #print cdx
                payload_record = self._load(cdx, False, failed_files)
                return payload_record

            except wbexceptions.CaptureException as e:
                pass

        raise wbexceptions.CaptureException('Original for revisit could not be loaded')


    def resolve_full(self, filename):
        # Attempt to resolve cdx file to full path
        full_url = None
        for resolver in self.resolvers:
            full_url = resolver(filename)
            if full_url:
                return full_url

        raise wbexceptions.UnresolvedArchiveFileException('Archive File Not Found: ' + filename)

    # Create a generator reading from a stream, with optional rewriting and final read call
    @staticmethod
    def create_stream_gen(stream, rewrite_func = None, final_read_func = None, first_buff = None):
        try:
            buff = first_buff if first_buff else stream.read()
            while buff:
                if rewrite_func:
                    buff = rewrite_func(buff)
                yield buff
                buff = stream.read()

            # For adding a tail/handling final buffer
            if final_read_func:
                buff = final_read_func()
                if buff:
                    yield buff

        finally:
            stream.close()


#=================================================================
class RewritingReplayView(ReplayView):

    def __init__(self, resolvers, archiveloader, head_insert = None, header_rewriter = None, redir_to_exact = True, buffer_response = False):
        ReplayView.__init__(self, resolvers, archiveloader)
        self.head_insert = head_insert
        self.header_rewriter = header_rewriter if header_rewriter else HeaderRewriter()
        self.redir_to_exact = redir_to_exact

        # buffer or stream rewritten response
        self.buffer_response = buffer_response


    def _text_content_type(self, content_type):
        for ctype, mimelist in self.REWRITE_TYPES.iteritems():
            if any ((mime in content_type) for mime in mimelist):
                return ctype

        return None


    def __call__(self, wbrequest, index, cdx_reader):
        urlrewriter = UrlRewriter(wbrequest.wb_url, wbrequest.wb_prefix)
        wbrequest.urlrewriter = urlrewriter

        response = ReplayView.__call__(self, wbrequest, index, cdx_reader)

        if response and response.cdx:
            self._check_redir(wbrequest, response.cdx)

        rewritten_headers = self.header_rewriter.rewrite(response.status_headers, urlrewriter)

        # TODO: better way to pass this?
        stream = response._stream

        # de_chunking in case chunk encoding is broken
        # TODO: investigate further
        de_chunk = False

        # handle transfer-encoding: chunked
        if (rewritten_headers.contains_removed_header('transfer-encoding', 'chunked')):
            stream = archiveloader.ChunkedLineReader(stream)
            de_chunk = True

        # Transparent, though still may need to dechunk
        if wbrequest.wb_url.mod == 'id_':
            if de_chunk:
                response.status_headers.remove_header('transfer-encoding')
                response.body = self.create_stream_gen(stream)

            return response

        # non-text content type, just send through with rewritten headers
        # but may need to dechunk
        if rewritten_headers.text_type is None:
            response.status_headers = rewritten_headers.status_headers

            if de_chunk:
                response.body = self.create_stream_gen(stream)

            return response

        # Handle text rewriting

        # special case -- need to ungzip the body
        if (rewritten_headers.contains_removed_header('content-encoding', 'gzip')):
            stream = archiveloader.LineReader(stream, decomp = utils.create_decompressor())

        # TODO: is this right?
        if rewritten_headers.charset:
            encoding = rewritten_headers.charset
            first_buff = None
        else:
            (encoding, first_buff) = self._detect_charset(stream)

            # if chardet thinks its ascii, use utf-8
            if encoding == 'ascii':
                #encoding = None
                encoding = 'utf-8'

        # Buffering response for html, streaming for others?
        #if rewritten_headers.text_type == 'html':
        #    return self._rewrite_html(encoding, urlrewriter, stream, rewritten_headers.status_headers, first_buff)
        #else:
        #    return self._rewrite_other(rewritten_headers.text_type, encoding, urlrewriter, stream, rewritten_headers.status_headers, first_buff)

        text_type = rewritten_headers.text_type
        status_headers = rewritten_headers.status_headers

        if text_type == 'html':
            rewriter = html_rewriter.HTMLRewriter(urlrewriter, outstream = None, head_insert = self.head_insert)
        elif text_type == 'css':
            rewriter = regex_rewriters.CSSRewriter(urlrewriter)
        elif text_type == 'js':
            rewriter = regex_rewriters.JSRewriter(urlrewriter)
        elif text_type == 'xml':
            rewriter = regex_rewriters.XMLRewriter(urlrewriter)
        else:
            raise Exception('Unknown Text Type for Rewrite: ' + text_type)

        # Create generator for response
        response_gen = self._create_rewrite_stream(rewriter, encoding, stream, first_buff)

        if self.buffer_response:
            return self._create_buffer_response(status_headers, response_gen)
        else:
            return WbResponse(status_headers, value = response_gen)


    # Buffer rewrite generator and return a response from a string
    def _create_buffer_response(self, status_headers, generator):
        out = StringIO.StringIO()

        try:
            for buff in generator:
                out.write(buff)

        finally:
            content = out.getvalue()

            content_length_str = str(len(content))
            status_headers.headers.append(('Content-Length', content_length_str))
            out.close()

        return WbResponse(status_headers, value = [content])

    # Create rewrite response from record (no Content-Length), may even be chunked by front-end
    def _create_rewrite_stream(self, rewriter, encoding, stream, first_buff = None):
        def do_rewrite(buff):
            if encoding:
                buff = self._decode_buff(buff, stream, encoding)

            buff = rewriter.rewrite(buff)

            if encoding:
                buff = buff.encode(encoding)

            return buff

        def do_finish():
            return rewriter.close()

        return self.create_stream_gen(stream, rewrite_func = do_rewrite, final_read_func = do_finish, first_buff = first_buff)


    def _decode_buff(self, buff, stream, encoding):
        try:
            buff = buff.decode(encoding)
        except UnicodeDecodeError, e:
            # chunk may have cut apart unicode bytes -- add 1-3 bytes and retry
            for i in range(3):
                buff += stream.read(1)
                try:
                    buff = buff.decode(encoding)
                    break
                except UnicodeDecodeError:
                    pass
            else:
                raise

        return buff


    def _detect_charset(self, stream):
        buff = stream.read(8192)
        result = chardet.detect(buff)
        print "chardet result: " + str(result)
        return (result['encoding'], buff)


    def _check_redir(self, wbrequest, cdx):
        if self.redir_to_exact and cdx and (cdx['timestamp'] != wbrequest.wb_url.timestamp):
            new_url = wbrequest.urlrewriter.get_timestamp_url(cdx['timestamp'], cdx['original'])
            raise wbexceptions.InternalRedirect(new_url)
            #return WbResponse.better_timestamp_response(wbrequest, cdx['timestamp'])

        return None


    def do_replay(self, cdx, wbrequest, index, failed_files):
        wbresponse = ReplayView.do_replay(self, cdx, wbrequest, index, failed_files)

        # Check for self redirect
        if wbresponse.status_headers.statusline.startswith('3'):
            if self.is_self_redirect(wbrequest, wbresponse.status_headers):
                raise wbexceptions.CaptureException('Self Redirect: ' + str(cdx))

        return wbresponse

    def is_self_redirect(self, wbrequest, status_headers):
        request_url = wbrequest.wb_url.url.lower()
        location_url = status_headers.get_header('Location').lower()
        #return request_url == location_url
        return (UrlRewriter.strip_protocol(request_url) == UrlRewriter.strip_protocol(location_url))



