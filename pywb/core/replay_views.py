import re
from io import BytesIO

from pywb.utils.bufferedreaders import ChunkedDataReader
from pywb.framework.wbrequestresponse import WbResponse

from pywb.framework.wbexceptions import CaptureException, InternalRedirect
from pywb.warc.recordloader import ArchiveLoadFailed

from pywb.utils.loaders import LimitReader

#=================================================================
class ReplayView:

    STRIP_SCHEME = re.compile('^([\w]+:[/]*)?(.*?)$')

    def __init__(self, content_loader, content_rewriter, head_insert_view = None,
                 redir_to_exact = True, buffer_response = False, reporter = None):

        self.content_loader = content_loader
        self.content_rewriter = content_rewriter

        self.head_insert_view = head_insert_view

        self.redir_to_exact = redir_to_exact
        # buffer or stream rewritten response
        self.buffer_response = buffer_response

        self._reporter = reporter


    def __call__(self, wbrequest, cdx_lines, cdx_loader):
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

                (status_headers, stream) = (self.content_loader.
                                            resolve_headers_and_payload(cdx, failed_files, cdx_loader))

                # check and reject self-redirect
                self._reject_self_redirect(wbrequest, cdx, status_headers)

                # check if redir is needed
                self._redirect_if_needed(wbrequest, cdx)

                # one more check for referrer-based self-redirect
                self._reject_referrer_self_redirect(wbrequest)

                response = None

                # if Content-Length for payload is present, ensure we don't read past it
                content_length = status_headers.get_header('content-length')
                if content_length:
                    stream = LimitReader.wrap_stream(stream, content_length)

                if self.content_rewriter and wbrequest.wb_url.mod != 'id_':
                    response = self.rewrite_content(wbrequest, cdx, status_headers, stream)
                else:
                    (status_headers, stream) = self.sanitize_content(status_headers, stream)
                    #status_headers.remove_header('content-length')

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

        result = self.content_rewriter.rewrite_headers(urlrewriter,
                                                       status_headers,
                                                       stream,
                                                       cdx['urlkey'])
        (rewritten_headers, stream) = result

        # no rewriting needed!
        if rewritten_headers.text_type is None:
            response_iter = self.stream_to_iter(stream)
            return WbResponse(rewritten_headers.status_headers, response_iter)

        def make_head_insert(rule):
            return (self.head_insert_view.render_to_string(wbrequest=wbrequest,
                                                           cdx=cdx,
                                                           rule=rule))
         # do head insert
        if self.head_insert_view:
            head_insert_func = make_head_insert
        else:
            head_insert_func = None

        result = self.content_rewriter.rewrite_content(urlrewriter,
                                                       rewritten_headers,
                                                       stream,
                                                       head_insert_func,
                                                       cdx['urlkey'])

        (status_headers, response_gen) = result

        if self.buffer_response:
            if wbrequest.wb_url.mod == 'id_':
                status_headers.remove_header('content-length')

            return self.buffered_response(status_headers, response_gen)

        return WbResponse(status_headers, response_gen)


    # Buffer rewrite iterator and return a response from a string
    def buffered_response(self, status_headers, iterator):
        out = BytesIO()

        try:
            for buff in iterator:
                out.write(bytes(buff))

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
        """
        Check if response is a 3xx redirect to the same url
        If so, reject this capture to avoid causing redirect loop
        """
        if not status_headers.statusline.startswith('3'):
            return

        # skip all 304s
        if (status_headers.statusline.startswith('304') and
            not wbrequest.wb_url.mod == 'id_'):

            raise CaptureException('Skipping 304 Modified: ' + str(cdx))

        request_url = wbrequest.wb_url.url.lower()
        location_url = status_headers.get_header('Location')
        if not location_url:
           return

        location_url = location_url.lower()

        if (ReplayView.strip_scheme(request_url) == ReplayView.strip_scheme(location_url)):
            raise CaptureException('Self Redirect: ' + str(cdx))

    def _reject_referrer_self_redirect(self, wbrequest):
        """
        Perform final check for referrer based self-redirect.
        This method should be called after verifying request timestamp matches capture.
        if referrer is same as current url, reject this response and try another capture
        """
        if not wbrequest.referrer:
            return

        # build full url even if using relative-rewriting
        request_url = (wbrequest.host_prefix +
                       wbrequest.rel_prefix + str(wbrequest.wb_url))

        if (ReplayView.strip_scheme(request_url) ==
            ReplayView.strip_scheme(wbrequest.referrer)):
            raise CaptureException('Self Redirect via Referrer: ' + str(wbrequest.wb_url))


    @staticmethod
    def strip_scheme(url):
        """
        >>> ReplayView.strip_scheme('https://example.com') == ReplayView.strip_scheme('http://example.com')
        True

        >>> ReplayView.strip_scheme('https://example.com') == ReplayView.strip_scheme('http:/example.com')
        True

        >>> ReplayView.strip_scheme('https://example.com') == ReplayView.strip_scheme('example.com')
        True

        >>> ReplayView.strip_scheme('about://example.com') == ReplayView.strip_scheme('example.com')
        True
        """
        m = ReplayView.STRIP_SCHEME.match(url)
        if not m:
            return url

        match = m.group(2)
        if match:
            return match
        else:
            return url

if __name__ == "__main__":
    import doctest
    doctest.testmod()
