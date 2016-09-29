from pywb.utils.wbexception import BadRequestException
from pywb.utils.timeutils import http_date_to_timestamp
from pywb.utils.timeutils import timestamp_to_http_date

from pywb.framework.wbrequestresponse import WbRequest, WbResponse
from pywb.rewrite.wburl import WbUrl

import six
LINK_FORMAT = 'application/link-format'


#=================================================================
class MementoReqMixin(object):
    def _parse_extra(self):
        if not self.wb_url:
            return

        if self.wb_url.type != self.wb_url.LATEST_REPLAY:
            return

        self.options['is_timegate'] = True

        accept_datetime = self.env.get('HTTP_ACCEPT_DATETIME')
        if not accept_datetime:
            return

        try:
            timestamp = http_date_to_timestamp(accept_datetime)
        except Exception:
            raise BadRequestException('Invalid Accept-Datetime: ' +
                                      accept_datetime)

        # note: this changes from LATEST_REPLAY -> REPLAY
        self.wb_url.set_replay_timestamp(timestamp)


#=================================================================
class MementoRequest(MementoReqMixin, WbRequest):
    pass


#=================================================================
class MementoRespMixin(object):
    def _init_derived(self, params):
        wbrequest = params.get('wbrequest')
        is_redirect = params.get('memento_is_redir', False)
        cdx = params.get('cdx')

        if not wbrequest or not wbrequest.wb_url:
            return

        mod = wbrequest.options.get('replay_mod', '')

        #is_top_frame = wbrequest.wb_url.is_top_frame
        is_top_frame = wbrequest.options.get('is_top_frame', False)

        is_timegate = (wbrequest.options.get('is_timegate', False) and
                       not is_top_frame)

        if is_timegate:
            self.status_headers.replace_header('Vary', 'accept-datetime')

        # Determine if memento:
        is_memento = False
        is_original = False

        # if no cdx included, not a memento, unless top-frame special
        if not cdx:
            # special case: include the headers but except Memento-Datetime
            # since this is really an intermediate resource
            if is_top_frame:
                is_memento = True

        # otherwise, if in proxy mode, then always a memento
        elif wbrequest.options['is_proxy']:
            is_memento = True
            is_original = True

        # otherwise only if timestamp replay (and not a timegate)
        #elif not is_timegate:
        #    is_memento = (wbrequest.wb_url.type == wbrequest.wb_url.REPLAY)
        elif not is_redirect:
            is_memento = (wbrequest.wb_url.is_replay())

        link = []
        req_url = wbrequest.wb_url.url

        if is_memento or is_timegate:
            url = req_url
            if cdx:
                ts = cdx['timestamp']
                url = cdx['url']
            # for top frame
            elif wbrequest.wb_url.timestamp:
                ts = wbrequest.wb_url.timestamp
            else:
                ts = None

            if ts:
                http_date = timestamp_to_http_date(ts)

                if is_memento:
                    self.status_headers.replace_header('Memento-Datetime',
                                                       http_date)

                canon_link = wbrequest.urlrewriter.get_new_url(mod=mod,
                                                               timestamp=ts,
                                                               url=url)

                # set in replay_views -- Must set content location
                #if is_memento and is_timegate:
                #    self.status_headers.headers.append(('Content-Location',
                #                                        canon_link))

                # don't set memento link for very long urls...
                if len(canon_link) < 512:
                    link.append(self.make_memento_link(canon_link,
                                                       'memento',
                                                       http_date))

        if is_original and is_timegate:
            link.append(self.make_link(req_url, 'original timegate'))
        else:
            link.append(self.make_link(req_url, 'original'))

        # for now, include timemap only in non-proxy mode
        if not wbrequest.options['is_proxy'] and (is_memento or is_timegate):
            link.append(self.make_timemap_link(wbrequest))

        if is_memento and not is_timegate:
            timegate = wbrequest.urlrewriter.get_new_url(mod=mod, timestamp='')
            link.append(self.make_link(timegate, 'timegate'))

        link = ', '.join(link)

        self.status_headers.replace_header('Link', link)

    def make_link(self, url, type):
        return '<{0}>; rel="{1}"'.format(url, type)

    def make_memento_link(self, url, type_, dt):
        return '<{0}>; rel="{1}"; datetime="{2}"'.format(url, type_, dt)

    def make_timemap_link(self, wbrequest):
        format_ = '<{0}>; rel="timemap"; type="{1}"'

        url = wbrequest.urlrewriter.get_new_url(mod='timemap',
                                                timestamp='',
                                                type=wbrequest.wb_url.QUERY)

        return format_.format(url, LINK_FORMAT)


#=================================================================
class MementoResponse(MementoRespMixin, WbResponse):
    pass


#=================================================================
def make_timemap_memento_link(cdx, prefix, datetime=None,
                             rel='memento', end=',\n', mod=''):

    memento = '<{0}>; rel="{1}"; datetime="{2}"' + end

    string = WbUrl.to_wburl_str(url=cdx['url'],
                                mod=mod,
                                timestamp=cdx['timestamp'],
                                type=WbUrl.REPLAY)

    url = prefix + string

    if not datetime:
        datetime = timestamp_to_http_date(cdx['timestamp'])

    return memento.format(url, rel, datetime)


#=================================================================
def make_timemap(wbrequest, cdx_lines):
    prefix = wbrequest.wb_prefix
    url = wbrequest.wb_url.url
    mod = wbrequest.options.get('replay_mod', '')

    # get first memento as it'll be used for 'from' field
    try:
        first_cdx = six.next(cdx_lines)
        from_date = timestamp_to_http_date(first_cdx['timestamp'])
    except StopIteration:
        first_cdx = None


    if first_cdx:
        # timemap link
        timemap = ('<{0}>; rel="self"; ' +
                   'type="application/link-format"; from="{1}",\n')
        yield timemap.format(prefix + wbrequest.wb_url.to_str(),
                             from_date)

    # original link
    original = '<{0}>; rel="original",\n'
    yield original.format(url)

    # timegate link
    timegate = '<{0}>; rel="timegate",\n'
    timegate_url= WbUrl.to_wburl_str(url=url,
                                     mod=mod,
                                     type=WbUrl.LATEST_REPLAY)

    yield timegate.format(prefix + timegate_url)

    if not first_cdx:
        # terminating timemap link, no from
        timemap = ('<{0}>; rel="self"; type="application/link-format"')
        yield timemap.format(prefix + wbrequest.wb_url.to_str())
        return

    # first memento link
    yield make_timemap_memento_link(first_cdx, prefix,
                            datetime=from_date, mod=mod)

    prev_cdx = None

    for cdx in cdx_lines:
        if prev_cdx:
            yield make_timemap_memento_link(prev_cdx, prefix, mod=mod)

        prev_cdx = cdx

    # last memento link, if any
    if prev_cdx:
        yield make_timemap_memento_link(prev_cdx, prefix, end='', mod=mod)
