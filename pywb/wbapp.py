from utils import rel_request_uri
from query import QueryHandler, EchoEnv, EchoRequest
from replay import WBHandler
import wbexceptions
import indexreader

from wbrequestresponse import WbResponse, StatusAndHeaders
from archivalrouter import ArchivalRequestRouter, MatchPrefix

## ===========
headInsert = """

<!-- WB Insert -->
<script src='/static/wb.js'> </script>
<link rel='stylesheet' href='/static/wb.css'/>
<!-- End WB Insert -->
"""


## ===========
'''
The below createDefaultWB() function is just a sample/debug which loads publicly accessible cdx data


To declare Wayback with one collection, `mycoll`
and will be accessed by user at:

`http://mywb.example.com:8080/mycoll/`

and will load cdx from cdx server running at:

`http://cdx.example.com/cdx`

and look for warcs at paths:

`http://warcs.example.com/servewarc/` and
`http://warcs.example.com/anotherpath/`,

one could declare a `createWB()` method as follows:

    def createWB():
        aloader = archiveloader.ArchiveLoader()
        query = QueryHandler(indexreader.RemoteCDXServer('http://cdx.example.com/cdx'))
    
        prefixes = [replay.PrefixResolver('http://warcs.example.com/servewarc/'),
                   replay.PrefixResolver('http://warcs.example.com/anotherpath/')]
    
        replay = replay.RewritingReplayHandler(resolvers = prefixes, archiveloader = aloader, headInsert = headInsert)
    
        return ArchivalRequestRouter(
        {
              MatchPrefix('mycoll', WBHandler(query, replay))
        },
        hostpaths = ['http://mywb.example.com:8080/'])
'''
## ===========
def createDefaultWB(headInsert):
    query = QueryHandler(indexreader.RemoteCDXServer('http://web.archive.org/cdx/search/cdx'))
    return ArchivalRequestRouter(
    {
      MatchPrefix('echo', EchoEnv()),     # Just echo the env
      MatchPrefix('req',  EchoRequest()), # Echo the WbRequest
      MatchPrefix('cdx',  query),         # Query the CDX
      MatchPrefix('web',  query),         # Query the CDX
    },
    hostpaths = ['http://localhost:9090/'])
## ===========


try:
    import globalwb
    wbparser = globalwb.createDefaultWB(headInsert)
except:
    print " *** Note: Inited With Sample Wayback *** "
    wbparser = createDefaultWB(headInsert)
    import traceback
    traceback.print_exc()




def application(env, start_response):

    if env.get('SCRIPT_NAME') or not env.get('REQUEST_URI'):
        env['REL_REQUEST_URI'] = rel_request_uri(env)
    else:
        env['REL_REQUEST_URI'] = env['REQUEST_URI']

    response = None

    try:
        response = wbparser(env)

        if not response:
            raise wbexceptions.NotFoundException(env['REL_REQUEST_URI'] + ' was not found')

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


