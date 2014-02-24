import StringIO

from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.utils.bufferedreaders import ChunkedDataReader
from wbrequestresponse import WbResponse

from wbexceptions import CaptureException, InternalRedirect
from pywb.warc.recordloader import ArchiveLoadFailed

#=================================================================
class ReplayView:
    def __init__(self, content_loader, content_rewriter, head_insert_view = None,
                 redir_to_exact = True, buffer_response = False, reporter = None):

        self.content_loader = content_loader
        self.content_rewriter = content_rewriter

        self.head_insert_view = head_insert_view

        self.redir_to_exact = redir_to_exact
        # buffer or stream rewritten response
        self.buffer_response = buffer_response

        self._reporter = reporter


    def __call__(self, wbrequest, cdx_lines):
        last_e = None
        first = True

        # List of already failed w/arcs
        failed_files = []

        # Iterate over the cdx until find one that works
        # The cdx should already be sorted in closest-to-timestamp order (from the cdx server)
        for cdx in cdx_lines:
            try:
                # optimize: can detect if redirect is needed just from the cdx, no need to load w/arc data
                if first:
                    self._redirect_if_needed(wbrequest, cdx)
                    first = False

                (status_headers, stream) = self.content_loader.resolve_headers_and_payload(cdx, failed_files)

                # check and reject self-redirect
                self._reject_self_redirect(wbrequest, cdx, status_headers)

                # check if redir is needed
                self._redirect_if_needed(wbrequest, cdx)

                # one more check for referrer-based self-redirect
                self._reject_referrer_self_redirect(wbrequest, status_headers)

                response = None

                if self.content_rewriter and wbrequest.wb_url.mod != 'id_':
                    response = self.rewrite_content(wbrequest, cdx, status_headers, stream)
                else:
                    (status_headers, stream) = self.sanitize_content(status_headers, stream)
                    response_iter = self.stream_to_iter(stream)
                    response = WbResponse(status_headers, response_iter)

                # notify reporter callback, if any
                if self._reporter:
                    self._reporter(wbrequest, cdx, response)

                return response


            except (CaptureException, ArchiveLoadFailed) as ce:
                import traceback
                traceback.print_exc()
                last_e = ce
                pass

        if last_e:
            raise last_e
        else:
            raise WbException('No Content Loaded for: ' + wbrequest.wb_url)

    @staticmethod
    def stream_to_iter(stream):
        try:
            buff = stream.read()
            while buff:
                yield buff
                buff = stream.read()

        finally:
            stream.close()

    def sanitize_content(self, status_headers, stream):
        # remove transfer encoding chunked and wrap in a dechunking stream
        if (status_headers.remove_header('transfer-encoding')):
            stream = ChunkedDataReader(stream)

        return (status_headers, stream)

    def rewrite_content(self, wbrequest, cdx, status_headers, stream):
        urlrewriter = wbrequest.urlrewriter

        (rewritten_headers, stream) = self.content_rewriter.rewrite_headers(urlrewriter, status_headers, stream)

        # no rewriting needed!
        if rewritten_headers.text_type is None:
            response_iter = self.stream_to_iter(stream)
            return WbResponse(rewritten_headers.status_headers, response_iter)

        # do head insert
        if self.head_insert_view:
            head_insert_str = self.head_insert_view.render_to_string(wbrequest = wbrequest, cdx = cdx)
        else:
            head_insert_str = None

        (status_headers, response_gen) = self.content_rewriter.rewrite_content(urlrewriter, rewritten_headers, stream, head_insert_str)

        if self.buffer_response:
            if wbrequest.wb_url.mod == 'id_':
                status_headers.remove_header('content-length')

            return self.buffered_response(status_headers, response_gen)

        return WbResponse(status_headers, response_gen)


    # Buffer rewrite iterator and return a response from a string
    def buffered_response(self, status_headers, iterator):
        out = StringIO.StringIO()

        try:
            for buff in iterator:
                out.write(buff)

        finally:
            content = out.getvalue()

            content_length_str = str(len(content))
            status_headers.headers.append(('Content-Length', content_length_str))
            out.close()

        return WbResponse(status_headers, value = [content])


    def _redirect_if_needed(self, wbrequest, cdx):
        if self.redir_to_exact and not wbrequest.is_proxy and cdx and (cdx['timestamp'] != wbrequest.wb_url.timestamp):
            new_url = wbrequest.urlrewriter.get_timestamp_url(cdx['timestamp'], cdx['original'])
            raise InternalRedirect(new_url)

        return None


    def _reject_self_redirect(self, wbrequest, cdx, status_headers):
        # self-redirect via location
        if status_headers.statusline.startswith('3'):
            request_url = wbrequest.wb_url.url.lower()
            location_url = status_headers.get_header('Location').lower()

            #TODO: canonicalize before testing?
            if (UrlRewriter.strip_protocol(request_url) == UrlRewriter.strip_protocol(location_url)):
                raise CaptureException('Self Redirect: ' + str(cdx))

    def _reject_referrer_self_redirect(self, wbrequest, status_headers):
        # at correct timestamp now, but must check for referrer redirect
        # indirect self-redirect, via meta-refresh, if referrer is same as current url
        if status_headers.statusline.startswith('2'):
            # build full url even if using relative-rewriting
            request_url = wbrequest.host_prefix + wbrequest.rel_prefix + str(wbrequest.wb_url)
            referrer_url = wbrequest.referrer
            if (referrer_url and UrlRewriter.strip_protocol(request_url) == UrlRewriter.strip_protocol(referrer_url)):
                raise CaptureException('Self Redirect via Referrer: ' + str(wbrequest.wb_url))




