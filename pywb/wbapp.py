import indexreader
import json
import wbexceptions
import utils

from wbrequestresponse import WbResponse
from archivalrouter import ArchivalRequestRouter

class EchoEnv:
    def run(self, wbrequest):
        return WbResponse.text_response(str(wbrequest.env))

class WBHandler:
    def run(self, wbrequest):
        return WbResponse.text_response(str(wbrequest))

class QueryHandler:
    def __init__(self):
        self.cdxserver = indexreader.RemoteCDXServer('http://web.archive.org/cdx/search/cdx')


    def run(self, wbrequest):
        wburl = wbrequest.wb_url

        params = self.cdxserver.getQueryParams(wburl)

        cdxlines = self.cdxserver.load(wburl.url, params)

        cdxlines = utils.peek_iter(cdxlines)

        if cdxlines is not None:
            return WbResponse.text_stream(cdxlines)

        raise wbexceptions.NotFoundException('WB Does Not Have Url: ' + wburl.url)



## ===========
parser = ArchivalRequestRouter(
    {
     't0' : EchoEnv(),
     't1' : WBHandler(),
     't2' : QueryHandler()
    },
    hostpaths = ['http://localhost:9090/'])
## ===========


def application(env, start_response):
    response = None

    try:
        response = parser.handleRequest(env)

        if not response:
            raise wbexceptions.NotFoundException(env['REQUEST_URI'] + ' was not found')

    except Exception as e:
        last_exc = e
        import traceback
        traceback.print_exc()
        response = handleException(env, e)

    return response(env, start_response)

def handleException(env, exc):
    if hasattr(exc, 'status'):
        status = exc.status()
    else:
        status = '400 Bad Request'

    return WbResponse.text_response(status + ' Error: ' + str(exc), status = status)

#def handle_not_found(env):
#    return WbResponse.text_response('Not Found: ' + env['REQUEST_URI'], status = '404 Not Found')


