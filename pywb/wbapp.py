from query import QueryHandler, EchoEnv, EchoRequest
from replay import FullHandler
import wbexceptions
import indexreader

from wbrequestresponse import WbResponse, StatusAndHeaders
from archivalrouter import ArchivalRequestRouter



## ===========
headInsert = """

<!-- WB Insert -->
<script src='/static/wb.js'> </script>
<link rel='stylesheet' href='/static/wb.css'/>
<!-- End WB Insert -->
"""


## ===========
def createDefaultWB(headInsert):
    query = QueryHandler(indexreader.RemoteCDXServer('http://web.archive.org/cdx/search/cdx'))
    return ArchivalRequestRouter(
    {
     'echo' : [EchoEnv()],
     'req'  : [EchoRequest()],
     'cdx'  : [query],
     'web'  : [query],
    },
    hostpaths = ['http://localhost:9090/'])
## ===========


try:
    import globalwb
    wbparser = globalwb.createDefaultWB(headInsert)
except:
    print " *** Test Wayback Inited *** "
    wbparser = createDefaultWB(headInsert)




def application(env, start_response):
    response = None

    try:
        response = wbparser.handleRequest(env)

        if not response:
            raise wbexceptions.NotFoundException(env['REQUEST_URI'] + ' was not found')

    except wbexceptions.InternalRedirect as ir:
        response = WbResponse(StatusAndHeaders(ir.status, ir.httpHeaders))

    except (wbexceptions.NotFoundException, wbexceptions.AccessException) as e:
        print "[INFO]: " + str(e)
        response = handleException(env, e)

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


