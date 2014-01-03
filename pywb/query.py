import indexreader
import utils
import wbrequestresponse
import wbexceptions

class QueryHandler:
    def __init__(self, cdxserver = None):
        if not cdxserver:
            cdxserver = indexreader.RemoteCDXServer('http://web.archive.org/cdx/search/cdx')

        self.cdxserver = cdxserver

    def __call__(self, wbrequest, prev_wbresponse):
        wburl = wbrequest.wb_url

        params = self.cdxserver.getQueryParams(wburl)

        cdxlines = self.cdxserver.load(wburl.url, params)

        cdxlines = utils.peek_iter(cdxlines)

        if cdxlines is not None:
            return wbrequestresponse.WbResponse.text_stream(cdxlines)

        raise wbexceptions.NotFoundException('WB Does Not Have Url: ' + wburl.url)


