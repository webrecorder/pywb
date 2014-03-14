from pywb.utils.wbexception import BadRequestException
from pywb.utils.timeutils import http_date_to_timestamp
from pywb.utils.timeutils import timestamp_to_http_date

from wbrequestresponse import WbRequest, WbResponse


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

        if is_memento and is_timegate:
            link = self.make_link(req_url, 'original timegate')
        elif is_memento:
            timegate = wbrequest.urlrewriter.get_timestamp_url('')

            link = []
            link.append(self.make_link(req_url, 'original'))
            link.append(self.make_link(timegate, 'timegate'))
            link = ', '.join(link)
        else:
            link = self.make_link(req_url, 'original')

        self.status_headers.headers.append(('Link', link))

    def make_link(self, url, type):
        return '<{0}>; rel="{1}"'.format(url, type)


#=================================================================
class MementoResponse(MementoRespMixin, WbResponse):
    pass
