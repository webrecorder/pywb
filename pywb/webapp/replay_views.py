import re
import logging

from io import BytesIO
from six.moves.urllib.parse import urlsplit
from itertools import chain

from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.wbexception import WbException, NotFoundException
from pywb.utils.loaders import LimitReader
from pywb.utils.timeutils import timestamp_now

from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.memento import MementoResponse

from pywb.rewrite.rewrite_content import RewriteContent
from pywb.warc.recordloader import ArchiveLoadFailed

from pywb.webapp.views import HeadInsertView

from pywb.webapp.rangecache import range_cache


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
    STRIP_SCHEME_WWW = re.compile('^([\w]+:[/]*(?:www[\d]*\.)?)?(.*?)$', re.MULTILINE)

    def __init__(self, content_loader, config):
        self.content_loader = content_loader

        framed = config.get('framed_replay')
        self.content_rewriter = RewriteContent(is_framed_replay=framed)

        self.head_insert_view = HeadInsertView.init_from_config(config)

        self.buffer_response = config.get('buffer_response', True)
        self.buffer_max_size = config.get('buffer_max_size', 16384)

        self.redir_to_exact = config.get('redir_to_exact', True)

        memento = config.get('enable_memento', False)
        if memento:
            self.response_class = MementoResponse
        else:
            self.response_class = WbResponse

        self.enable_range_cache = config.get('enable_ranges', True)

        self._reporter = config.get('reporter')

    def render_content(self, wbrequest, cdx_lines, cdx_loader):
        last_e = None
        first = True

        #cdx_lines = args[0]
        #cdx_loader = args[1]

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

                response = self.cached_replay_capture(wbrequest,
                                                      cdx,
                                                      cdx_loader,
                                                      failed_files)

            except (CaptureException, ArchiveLoadFailed) as ce:
                #import traceback
                #traceback.print_exc()
                logging.debug(ce)
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

    def cached_replay_capture(self, wbrequest, cdx, cdx_loader, failed_files):
        def get_capture():
            return self.replay_capture(wbrequest,
                                       cdx,
                                       cdx_loader,
                                       failed_files)

        if not self.enable_range_cache:
            return get_capture()

        range_info = wbrequest.extract_range()

        if not range_info:
            return get_capture()

        range_status, range_iter = (range_cache.
            handle_range(wbrequest,
                         cdx.get('digest', cdx['urlkey']),
                         get_capture,
                         *range_info))

        response = self.response_class(range_status,
                                       range_iter,
                                       wbrequest=wbrequest,
                                       cdx=cdx)
        return response

    def replay_capture(self, wbrequest, cdx, cdx_loader, failed_files):
        (status_headers, stream) = (self.content_loader(cdx,
                                                        failed_files,
                                                        cdx_loader,
                                                        wbrequest))

        # check and reject self-redirect
        self._reject_self_redirect(wbrequest, cdx, status_headers)

        # check if redir is needed
        redir_response = self._redirect_if_needed(wbrequest, cdx)
        if redir_response:
            return redir_response

        #length = status_headers.get_header('content-length')
        #stream = LimitReader.wrap_stream(stream, length)

        # one more check for referrer-based self-redirect
        # TODO: evaluate this, as refreshing in browser may sometimes cause
        # referrer to be set to the same page, incorrectly skipping a capture
        # self._reject_referrer_self_redirect(wbrequest)

        urlrewriter = wbrequest.urlrewriter

        # if using url rewriter, use original url for rewriting purposes
        if wbrequest and wbrequest.wb_url:
            wbrequest.wb_url.url = cdx['url']

        if wbrequest.options['is_ajax']:
            wbrequest.urlrewriter.rewrite_opts['is_ajax'] = True

        head_insert_func = None
        if self.head_insert_view:
            head_insert_func = (self.head_insert_view.
                                create_insert_func(wbrequest))

        result = (self.content_rewriter.
                  rewrite_content(urlrewriter,
                                  status_headers=status_headers,
                                  stream=stream,
                                  head_insert_func=head_insert_func,
                                  urlkey=cdx['urlkey'],
                                  cdx=cdx,
                                  env=wbrequest.env))

        (status_headers, response_iter, is_rewritten) = result

        # buffer response if buffering enabled
        if self.buffer_response:
            content_len = status_headers.get_header('content-length')
            try:
                content_len = int(content_len)
            except:
                content_len = 0

            if content_len <= 0:
                max_size = self.buffer_max_size
                response_iter = self.buffered_response(status_headers,
                                                       response_iter,
                                                       max_size)

        # Set Content-Location if not exact capture
        if not self.redir_to_exact:
            mod = wbrequest.options.get('replay_mod', wbrequest.wb_url.mod)
            canon_url = (wbrequest.urlrewriter.
                         get_new_url(timestamp=cdx['timestamp'],
                                     url=cdx['url'],
                                     mod=mod))

            status_headers.headers.append(('Content-Location', canon_url))

        if wbrequest.wb_url.mod == 'vi_':
            status_headers.headers.append(('access-control-allow-origin', '*'))

        response = self.response_class(status_headers,
                                       response_iter,
                                       wbrequest=wbrequest,
                                       cdx=cdx)

        # notify reporter callback, if any
        if self._reporter:
            self._reporter(wbrequest, cdx, response)

        return response

    # Buffer rewrite iterator and return a response from a string
    def buffered_response(self, status_headers, iterator, max_size):
        out = BytesIO()
        size = 0
        read_all = True

        try:
            for buff in iterator:
                buff = bytes(buff)
                size += len(buff)
                out.write(buff)
                if max_size > 0 and size > max_size:
                    read_all = False
                    break

        finally:
            content = out.getvalue()
            out.close()

        if read_all:
            content_length_str = str(len(content))

            # remove existing content length
            status_headers.replace_header('Content-Length',
                                          content_length_str)
            return [content]
        else:
            status_headers.remove_header('Content-Length')
            return chain(iter([content]), iterator)

    def _redirect_if_needed(self, wbrequest, cdx):
        if not self.redir_to_exact:
            return None

        if wbrequest.options['is_proxy']:
            return None

        if wbrequest.custom_params.get('noredir'):
            return None

        is_timegate = (wbrequest.options.get('is_timegate', False))
        if not is_timegate:
            is_timegate = wbrequest.wb_url.is_latest_replay()

        redir_needed = is_timegate or (cdx['timestamp'] != wbrequest.wb_url.timestamp)

        if not redir_needed:
            return None

        if self.enable_range_cache and wbrequest.extract_range():
            return None

        #if is_timegate:
        #    timestamp = timestamp_now()
        #else:
        timestamp = cdx['timestamp']

        new_url = (wbrequest.urlrewriter.
                   get_new_url(timestamp=timestamp,
                               url=cdx['url']))

        if wbrequest.method == 'POST':
            #   FF shows a confirm dialog, so can't use 307 effectively
            #   was: statusline = '307 Same-Method Internal Redirect'
            return None
        elif is_timegate:
            statusline = '302 Found'
        else:
            # clear cdx line to indicate internal redirect
            statusline = '302 Internal Redirect'
            cdx = None

        status_headers = StatusAndHeaders(statusline,
                                          [('Location', new_url)])

        return self.response_class(status_headers,
                                   wbrequest=wbrequest,
                                   cdx=cdx,
                                   memento_is_redir=True)

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
        if location_url.startswith('/'):
            host = urlsplit(cdx['url']).netloc
            location_url = host + location_url

        if (ReplayView.strip_scheme_www(request_url) ==
             ReplayView.strip_scheme_www(location_url)):
            raise CaptureException('Self Redirect: ' + str(cdx))

    # TODO: reevaluate this, as it may reject valid refreshes of a page
    def _reject_referrer_self_redirect(self, wbrequest):  # pragma: no cover
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

        if (ReplayView.strip_scheme_www(request_url) ==
             ReplayView.strip_scheme_www(wbrequest.referrer)):
            raise CaptureException('Self Redirect via Referrer: ' +
                                   str(wbrequest.wb_url))

    @staticmethod
    def strip_scheme_www(url):
        """
        >>> ReplayView.strip_scheme_www('https://example.com') ==\
            ReplayView.strip_scheme_www('http://example.com')
        True

        >>> ReplayView.strip_scheme_www('https://example.com') ==\
            ReplayView.strip_scheme_www('http:/example.com')
        True

        >>> ReplayView.strip_scheme_www('https://example.com') ==\
            ReplayView.strip_scheme_www('example.com')
        True

        >>> ReplayView.strip_scheme_www('https://example.com') ==\
            ReplayView.strip_scheme_www('http://www2.example.com')
        True

        >>> ReplayView.strip_scheme_www('about://example.com') ==\
            ReplayView.strip_scheme_www('example.com')
        True

        >>> ReplayView.strip_scheme_www('http://') ==\
            ReplayView.strip_scheme_www('')
        True

        >>> ReplayView.strip_scheme_www('#!@?') ==\
            ReplayView.strip_scheme_www('#!@?')
        True
        """
        m = ReplayView.STRIP_SCHEME_WWW.match(url)
        match = m.group(2)
        return match


if __name__ == "__main__":
    import doctest
    doctest.testmod()
