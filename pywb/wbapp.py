from wbrequestresponse import WbResponse
from archiveurl import archiveurl
from archivalrouter import ArchivalRequestRouter
import indexreader
import json
import wbexceptions
import utils

class WBHandler:
    def run(self, wbrequest):
        wburl = archiveurl(wbrequest.wb_url)
        wbrequest.parsed_url = wburl
        return WbResponse.text_stream(str(vars(wburl)))

class QueryHandler:
    def __init__(self):
        self.cdxserver = indexreader.RemoteCDXServer('http://web.archive.org/cdx/search/cdx')

    @staticmethod
    def get_query_params(wburl):
        return {

            archiveurl.QUERY:
                {'collapseTime': '10', 'filter': '!statuscode:(500|502|504)', 'limit': '150000'},

            archiveurl.URL_QUERY:
                {'collapse': 'urlkey', 'matchType': 'prefix', 'showGroupCount': True, 'showUniqCount': True, 'lastSkipTimestamp': True, 'limit': '100',
                 'fl': 'urlkey,original,timestamp,endtimestamp,groupcount,uniqcount',
                },

            archiveurl.REPLAY:
                {'sort': 'closest', 'filter': '!statuscode:(500|502|504)', 'limit': '10', 'closest': wburl.timestamp, 'resolveRevisits': True},

            archiveurl.LATEST_REPLAY:
                {'sort': 'reverse', 'filter': 'statuscode:[23]..', 'limit': '1', 'resolveRevisits': True}

        }[wburl.type]


    def run(self, wbrequest):
        wburl = archiveurl(wbrequest.wb_url)
        #wburl = wbresponse.body.parsed_url

        params = QueryHandler.get_query_params(wburl)

        cdxlines = self.cdxserver.load(wburl.url, params)

        cdxlines = utils.peek_iter(cdxlines)

        if cdxlines is not None:
            return WbResponse.text_stream(cdxlines)

        raise wbexceptions.NotFoundException('WB Does Not Have Url: ' + wburl.url)



## ===========
parser = ArchivalRequestRouter(
    {'/t1/' : WBHandler(),
     '/t2/' : QueryHandler()
    },
    hostpaths = ['http://localhost:9090/'])
## ===========


def application(env, start_response):
    response = None

    try:
        response = parser.handle_request(env)

        if not response:
            raise wbexceptions.NotFoundException(env['REQUEST_URI'] + ' was not found')

    except Exception as e:
        last_exc = e
        import traceback
        traceback.print_exc()
        response = handle_exception(env, e)

    return response(env, start_response)

def handle_exception(env, exc):
    if hasattr(exc, 'status'):
        status = exc.status()
    else:
        status = '400 Bad Request'

    return WbResponse.text_response(status + ' Error: ' + str(exc), status = status)

#def handle_not_found(env):
#    return WbResponse.text_response('Not Found: ' + env['REQUEST_URI'], status = '404 Not Found')


