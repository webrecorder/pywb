from utils import rel_request_uri
import wbexceptions

from wbrequestresponse import WbResponse, StatusAndHeaders

## ===========
default_head_insert = """

<!-- WB Insert -->
<script src='/static/wb.js'> </script>
<link rel='stylesheet' href='/static/wb.css'/>
<!-- End WB Insert -->
"""


## ===========
'''

To declare Wayback with one collection, `mycoll`
and will be accessed by user at:

`http://mywb.example.com:8080/mycoll/`

and will load cdx from cdx server running at:

`http://cdx.example.com/cdx`

and look for warcs at paths:

`http://warcs.example.com/servewarc/` and
`http://warcs.example.com/anotherpath/`,

one could declare a `sample_wb_settings()` method as follows
'''

# TODO: simplify this!!

def sample_wb_settings():
    import archiveloader
    import query, indexreader
    import replay, replay_resolvers
    from archivalrouter import ArchivalRequestRouter, Route


    # Standard loader which supports WARC/ARC files
    aloader = archiveloader.ArchiveLoader()

    # Source for cdx source
    query_h = query.QueryHandler(indexreader.RemoteCDXServer('http://cdx.example.com/cdx'))

    # Loads warcs specified in cdx from these locations
    prefixes = [replay_resolvers.PrefixResolver('http://warcs.example.com/servewarc/'),
                replay_resolvers.PrefixResolver('http://warcs.example.com/anotherpath/')]

    # Create rewriting replay handler to rewrite records
    replayer = replay.RewritingReplayHandler(resolvers = prefixes, archiveloader = aloader, headInsert = default_head_insert)

    # Create Jinja2 based html query renderer
    htmlquery = query.J2QueryRenderer('./ui/', 'query.html')

    # Handler which combins query, replayer, and html_query
    wb_handler = replay.WBHandler(query_h, replayer, htmlquery = htmlquery)

    # Finally, create wb router
    return ArchivalRequestRouter(
        {
            Route('echo_req', query.DebugEchoRequest()), # Debug ex: just echo parsed request
            Route('mycoll',   wb_handler)
        },
        # Specify hostnames that pywb will be running on
        # This will help catch occasionally missed rewrites that fall-through to the host
        # (See archivalrouter.ReferRedirect)
        hostpaths = ['http://mywb.example.com:8080/'])



def create_wb_app(wb_router):

    # Top-level wsgi application
    def application(env, start_response):
        if env.get('SCRIPT_NAME') or not env.get('REQUEST_URI'):
            env['REL_REQUEST_URI'] = rel_request_uri(env)
        else:
            env['REL_REQUEST_URI'] = env['REQUEST_URI']

        response = None

        try:
            response = wb_router(env)

            if not response:
                raise wbexceptions.NotFoundException(env['REL_REQUEST_URI'] + ' was not found')

        except wbexceptions.InternalRedirect as ir:
            response = WbResponse(StatusAndHeaders(ir.status, ir.httpHeaders))

        except (wbexceptions.NotFoundException, wbexceptions.AccessException) as e:
            print "[INFO]: " + str(e)
            response = handle_exception(env, e)

        except Exception as e:
            last_exc = e
            import traceback
            traceback.print_exc()
            response = handle_exception(env, e)

        return response(env, start_response)


    return application


def handle_exception(env, exc):
    if hasattr(exc, 'status'):
        status = exc.status()
    else:
        status = '400 Bad Request'

    return WbResponse.text_response(status + ' Error: ' + str(exc), status = status)


if __name__ == "__main__":
    app = create_wb_app(sample_wb_settings())


#=================================================================
import globalwb
application = create_wb_app(globalwb.create_global_wb(default_head_insert))
#=================================================================


