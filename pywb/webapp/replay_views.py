import re
from io import BytesIO

from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.wbexception import WbException, NotFoundException
from pywb.utils.loaders import LimitReader

from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.memento import MementoResponse

from pywb.warc.recordloader import ArchiveLoadFailed


#=================================================================
class CaptureException(WbException):
    """
    raised to indicate an issue with a specific capture
    and will be caught and result in a retry, if possible
    if not, will result in a 502
    """
    def status(self):
        return '502 Internal Server Error'


#=================================================================
class ReplayView(object):
    STRIP_SCHEME = re.compile('^([\w]+:[/]*)?(.*?)$')

    def __init__(self, content_loader, content_rewriter, head_insert_view=None,
                 redir_to_exact=True, buffer_response=False, reporter=None,
                 memento=False):

        self.content_loader = content_loader
        self.content_rewriter = content_rewriter

        self.head_insert_view = head_insert_view

        self.redir_to_exact = redir_to_exact
        # buffer or stream rewritten response
        self.buffer_response = buffer_response

        self._reporter = reporter

        if memento:
            self.response_class = MementoResponse
        else:
            self.response_class = WbResponse

    def __call__(self, wbrequest, cdx_lines, cdx_loader):
        last_e = None
        first = True

        # List of already failed w/arcs
        failed_files = []

        response = None

        # Iterate over the cdx until find one that works
        # The cdx should already be sorted in
        # closest-to-timestamp order (from the cdx server)
        for cdx in cdx_lines:
            try:
                # optimize: can detect if redirect is needed just from the cdx,
                # no need to load w/arc data if requiring exact match
                if first:
                    redir_response = self._redirect_if_needed(wbrequest, cdx)
                    if redir_response:
                        return redir_response

                    first = False

                response = self.replay_capture(wbrequest,
                                               cdx,
                                               cdx_loader,
                                               failed_files)

            except (CaptureException, ArchiveLoadFailed) as ce:
                import traceback
                traceback.print_exc()
                last_e = ce
                pass

            if response:
                return response

        if not last_e:
            # can only get here if cdx_lines is empty somehow
            # should be filtered out before hand, but if not
            msg = 'No Captures found for: ' + wbrequest.wb_url.url
            last_e = NotFoundException(msg)

        raise last_e

    def replay_capture(self, wbrequest, cdx, cdx_loader, failed_files):
        (status_headers, stream) = (self.content_loader.
                                    resolve_headers_and_payload(cdx,
                                                                failed_files,
                                                                cdx_loader))

        # check and reject self-redirect
        self._reject_self_redirect(wbrequest, cdx, status_headers)

        # check if redir is needed
        redir_response = self._redirect_if_needed(wbrequest, cdx)
        if redir_response:
            return redir_response

        length = status_headers.get_header('content-length')
        stream = LimitReader.wrap_stream(stream, length)

        # one more check for referrer-based self-redirect
        self._reject_referrer_self_redirect(wbrequest)

        urlrewriter = wbrequest.urlrewriter

        head_insert_func = None
        if self.head_insert_view:
            head_insert_func = (self.head_insert_view.
                                create_insert_func(wbrequest))

        result = (self.content_rewriter.
                  rewrite_content(urlrewriter,
                                  headers=status_headers,
                                  stream=stream,
                                  head_insert_func=head_insert_func,
                                  urlkey=cdx['urlkey'],
                                  sanitize_only=wbrequest.wb_url.is_identity,
                                  cdx=cdx,
                                  mod=wbrequest.wb_url.mod))

        (status_headers, response_iter, is_rewritten) = result

        # buffer response if buffering enabled
        if self.buffer_response:
            response_iter = self.buffered_response(status_headers,
                                                   response_iter)

        response = self.response_class(status_headers,
                                       response_iter,
                                       wbrequest=wbrequest,
                                       cdx=cdx)

        # notify reporter callback, if any
        if self._reporter:
            self._reporter(wbrequest, cdx, response)

        return response

    # Buffer rewrite iterator and return a response from a string
    def buffered_response(self, status_headers, iterator):
        out = BytesIO()

        try:
            for buff in iterator:
                out.write(bytes(buff))

        finally:
            content = out.getvalue()

            content_length_str = str(len(content))

            # remove existing content length
            status_headers.replace_header('Content-Length',
                                          content_length_str)
            out.close()

        return content

    def _redirect_if_needed(self, wbrequest, cdx):
        if wbrequest.is_proxy:
            return None

        # todo: generalize this?
        redir_needed = (hasattr(wbrequest, 'is_timegate') and
                        wbrequest.is_timegate)

        if not redir_needed and self.redir_to_exact:
            redir_needed = (cdx['timestamp'] != wbrequest.wb_url.timestamp)

        if not redir_needed:
            return None

        new_url = wbrequest.urlrewriter.get_timestamp_url(cdx['timestamp'],
                                                          cdx['original'])

        status_headers = StatusAndHeaders('302 Internal Redirect',
                                          [('Location', new_url)])

        # don't include cdx to indicate internal redirect
        return self.response_class(status_headers,
                                   wbrequest=wbrequest)

    def _reject_self_redirect(self, wbrequest, cdx, status_headers):
        """
        Check if response is a 3xx redirect to the same url
        If so, reject this capture to avoid causing redirect loop
        """
        if not status_headers.statusline.startswith('3'):
            return

        # skip all 304s
        if (status_headers.statusline.startswith('304') and
            not wbrequest.wb_url.is_identity):

            raise CaptureException('Skipping 304 Modified: ' + str(cdx))

        request_url = wbrequest.wb_url.url.lower()
        location_url = status_headers.get_header('Location')
        if not location_url:
            return

        location_url = location_url.lower()

        if (ReplayView.strip_scheme(request_url) ==
             ReplayView.strip_scheme(location_url)):
            raise CaptureException('Self Redirect: ' + str(cdx))

    def _reject_referrer_self_redirect(self, wbrequest):
        """
        Perform final check for referrer based self-redirect.
        This method should be called after verifying that
        the request timestamp == capture timestamp

        If referrer is same as current url,
        reject this response and try another capture.
        """
        if not wbrequest.referrer:
            return

        # build full url even if using relative-rewriting
        request_url = (wbrequest.host_prefix +
                       wbrequest.rel_prefix + str(wbrequest.wb_url))

        if (ReplayView.strip_scheme(request_url) ==
             ReplayView.strip_scheme(wbrequest.referrer)):
            raise CaptureException('Self Redirect via Referrer: ' +
                                   str(wbrequest.wb_url))

    @staticmethod
    def strip_scheme(url):
        """
        >>> ReplayView.strip_scheme('https://example.com') ==\
            ReplayView.strip_scheme('http://example.com')
        True

        >>> ReplayView.strip_scheme('https://example.com') ==\
            ReplayView.strip_scheme('http:/example.com')
        True

        >>> ReplayView.strip_scheme('https://example.com') ==\
            ReplayView.strip_scheme('example.com')
        True

        >>> ReplayView.strip_scheme('about://example.com') ==\
            ReplayView.strip_scheme('example.com')
        True

        >>> ReplayView.strip_scheme('http://') ==\
            ReplayView.strip_scheme('')
        True

        >>> ReplayView.strip_scheme('#!@?') ==\
            ReplayView.strip_scheme('#!@?')
        True
        """
        m = ReplayView.STRIP_SCHEME.match(url)
        match = m.group(2)
        return match


if __name__ == "__main__":
    import doctest
    doctest.testmod()
