from wbrequestresponse import WbResponse
from archiveurl import archiveurl
from archivalrouter import ArchivalRequestRouter
import indexreader
import json

class WBHandler:
    def run(self, wbrequest):
        wburl = archiveurl(wbrequest.wb_url)
        return WbResponse.text_response(repr(wburl))

class QueryHandler:
    def __init__(self):
        self.cdxserver = indexreader.RemoteCDXServer('http://web.archive.org/cdx/search/cdx')

    @staticmethod
    def get_query_params(wburl):
        print wburl.type
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

        params = QueryHandler.get_query_params(wburl)

        #parse_cdx = (wburl.mod == 'json')
        cdxlines = self.cdxserver.load(wburl.url, params)

        return WbResponse.text_stream(cdxlines)

        #if parse_cdx:
        #    text = str("\n".join(map(str, cdxlines)))
        #    text = json.dumps(cdxlines, default=lambda o: o.__dict__)
        #else:
        #    text = cdxlines


## ===========
parser = ArchivalRequestRouter({'/web/': QueryHandler()}, hostpaths = ['http://localhost:9090/'])
## ===========


def application(env, start_response):
    response = None

    try:
        response = parser.handle_request(env)

    except Exception as e:
        last_exc = e
        import traceback
        traceback.print_exc()
        response = parser.handle_exception(env, e)

    if not response:
        response = parser.handle_not_found(env)

    return response(env, start_response)
