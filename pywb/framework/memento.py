from pywb.utils.wbexception import BadRequestException
from pywb.utils.timeutils import http_date_to_timestamp
from pywb.utils.timeutils import timestamp_to_http_date

from wbrequestresponse import WbRequest, WbResponse
from pywb.rewrite.wburl import WbUrl

LINK_FORMAT = 'application/link-format'


#=================================================================
class MementoReqMixin(object):
    def _parse_extra(self):
        self.is_timegate = False

        if not self.wb_url:
            return

        if self.wb_url.type != self.wb_url.LATEST_REPLAY:
            return

        self.is_timegate = True

        accept_datetime = self.env.get('HTTP_ACCEPT_DATETIME')
        if not accept_datetime:
            return

        try:
            timestamp = http_date_to_timestamp(accept_datetime)
        except Exception:
            raise BadRequestException('Invalid Accept-Datetime: ' +
                                      accept_datetime)

        self.wb_url.set_replay_timestamp(timestamp)


#=================================================================
class MementoRequest(MementoReqMixin, WbRequest):
    pass


#=================================================================
class MementoRespMixin(object):
    def _init_derived(self, params):
        wbrequest = params.get('wbrequest')
        cdx = params.get('cdx')

        if not wbrequest or not wbrequest.wb_url:
            return

        is_timegate = wbrequest.is_timegate

        if is_timegate:
            self.status_headers.headers.append(('Vary', 'accept-datetime'))

        # Determine if memento:
        # if no cdx included, definitely not a memento
        if not cdx:
            is_memento = False

        # otherwise, if in proxy mode, then always a memento
        elif wbrequest.is_proxy:
            is_memento = True

        # otherwise only for replay
        else:
            is_memento = (wbrequest.wb_url.type == wbrequest.wb_url.REPLAY)

        if is_memento:
            http_date = timestamp_to_http_date(cdx['timestamp'])
            self.status_headers.headers.append(('Memento-Datetime', http_date))

        req_url = wbrequest.wb_url.url

        link = []

        if is_memento and is_timegate:
            link.append(self.make_link(req_url, 'original timegate'))
        else:
            link.append(self.make_link(req_url, 'original'))

        # for now, include timemap only in non-proxy mode
        if not wbrequest.is_proxy and (is_memento or is_timegate):
            link.append(self.make_timemap_link(wbrequest))

        if is_memento and not is_timegate:
            timegate = wbrequest.urlrewriter.get_timestamp_url('')
            link.append(self.make_link(timegate, 'timegate'))

        link = ', '.join(link)

        self.status_headers.headers.append(('Link', link))

    def make_link(self, url, type):
        return '<{0}>; rel="{1}"'.format(url, type)

    def make_timemap_link(self, wbrequest):
        format_ = '<{0}>; rel="timemap"; type="{1}"'

        prefix = wbrequest.wb_prefix

        url = prefix + (wbrequest.wb_url.
                        to_str(mod='timemap',
                               timestamp='',
                               type=wbrequest.wb_url.QUERY))

        return format_.format(url, LINK_FORMAT)


#=================================================================
class MementoResponse(MementoRespMixin, WbResponse):
    pass


#=================================================================
def make_memento_link(cdx, prefix, datetime=None, rel='memento', end=',\n'):
    memento = '<{0}>; rel="{1}"; datetime="{2}"' + end

    string = WbUrl.to_wburl_str(url=cdx['original'],
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

    # get first memento as it'll be used for 'from' field
    first_cdx = cdx_lines.next()
    from_date = timestamp_to_http_date(first_cdx['timestamp'])

    # timemap link
    timemap = ('<{0}>; rel="self"; ' +
               'type="application/link-format"; from="{1}",\n')
    yield timemap.format(prefix + wbrequest.wb_url.to_str(), from_date)

    # original link
    original = '<{0}>; rel="original",\n'
    yield original.format(url)

    # timegate link
    timegate = '<{0}>; rel="timegate",\n'
    yield timegate.format(prefix + url)

    # first memento link
    yield make_memento_link(first_cdx, prefix,
                            datetime=from_date)

    prev_cdx = None

    for cdx in cdx_lines:
        if prev_cdx:
            yield make_memento_link(prev_cdx, prefix)

        prev_cdx = cdx

    # last memento link, if any
    if prev_cdx:
        yield make_memento_link(prev_cdx, prefix, end='')
