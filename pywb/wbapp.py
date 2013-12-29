from query import QueryHandler
from replay import FullHandler
import wbexceptions

from wbrequestresponse import WbResponse
from archivalrouter import ArchivalRequestRouter


## ===========
class EchoEnv:
    def __call__(self, wbrequest, _):
        return WbResponse.text_response(str(wbrequest.env))

class WBHandler:
    def __call__(self, wbrequest, _):
        return WbResponse.text_response(str(wbrequest))


## ===========
query = QueryHandler()

import testwb

headInsert = """

<!-- WB Insert -->
<script src='/static/wb.js'> </script>
<link rel='stylesheet' href='/static/wb.css'/>
<!-- End WB Insert -->
"""

replay = testwb.createReplay(headInsert)

## ===========
parser = ArchivalRequestRouter(
    {
     't0' : [EchoEnv()],
     't1' : [WBHandler()],
     't2' : [query],
     't3' : [query, replay],
     'web': FullHandler(query, replay)
    },
    hostpaths = ['http://localhost:9090/'])
## ===========


def application(env, start_response):
    response = None

    try:
        response = parser.handleRequest(env)

        if not response:
            raise wbexceptions.NotFoundException(env['REQUEST_URI'] + ' was not found')

    except wbexceptions.InternalRedirect as ir:
        response = WbResponse(status = ir.status, headersList = ir.httpHeaders)

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


