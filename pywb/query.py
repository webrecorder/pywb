import indexreader
import utils
import wbrequestresponse
import wbexceptions

class QueryHandler:
    def __init__(self, cdxserver = None):
        if not cdxserver:
            cdxserver = indexreader.RemoteCDXServer('http://web.archive.org/cdx/search/cdx')

        self.cdxserver = cdxserver

    def __call__(self, wbrequest):
        wburl = wbrequest.wb_url

        # init standard params
        params = self.cdxserver.getQueryParams(wburl)

        # add any custom params from the request
        params.update(wbrequest.customParams)

        cdxlines = self.cdxserver.load(wburl.url, params)

        cdxlines = utils.peek_iter(cdxlines)

        if cdxlines is not None:
            return wbrequestresponse.WbResponse.text_stream(cdxlines)

        raise wbexceptions.NotFoundException('WB Does Not Have Url: ' + wburl.url)

## ===========
## Simple handlers for debuging
class EchoEnv:
    def __call__(self, wbrequest):
        return wbrequestresponse.WbResponse.text_response(str(wbrequest.env))

class EchoRequest:
    def __call__(self, wbrequest):
        return wbrequestresponse.WbResponse.text_response(str(wbrequest))


