import archiveloader
import views
import handlers
import indexreader
import replay_views
import replay_resolvers
import cdxserve
from archivalrouter import ArchivalRequestRouter, Route
import os


## ===========
default_head_insert = """

<!-- WB Insert -->
<script src='/static/wb.js'> </script>
<link rel='stylesheet' href='/static/wb.css'/>
<!-- End WB Insert -->
"""

def pywb_config():
    # Current test dir
    test_dir = os.path.dirname(os.path.realpath(__file__)) + '/../test/'

    # Standard loader which supports WARC/ARC files
    aloader = archiveloader.ArchiveLoader()

    # Source for cdx source
    #query_h = query.QueryHandler(indexreader.RemoteCDXServer('http://cdx.example.com/cdx'))
    #test_cdx = [test_dir + 'iana.cdx', test_dir + 'example.cdx', test_dir + 'dupes.cdx']
    indexs = indexreader.LocalCDXServer([test_dir])

    # Loads warcs specified in cdx from these locations
    prefixes = [replay_resolvers.PrefixResolver(test_dir)]

    # Jinja2 head insert
    head_insert = views.J2HeadInsertView('./ui/', 'head_insert.html')

    # Create rewriting replay handler to rewrite records
    replayer = replay_views.RewritingReplayView(resolvers = prefixes, archiveloader = aloader, head_insert = head_insert, buffer_response = True)

    # Create Jinja2 based html query view
    html_view = views.J2QueryView('./ui/', 'query.html')

    # WB handler which uses the index reader, replayer, and html_view
    wb_handler = handlers.WBHandler(indexs, replayer, html_view)

    # cdx handler
    cdx_handler = handlers.CDXHandler(indexs)

    # Finally, create wb router
    return ArchivalRequestRouter(
        {
            Route('echo_req', handlers.DebugEchoHandler()), # Debug ex: just echo parsed request
            Route('pywb',   wb_handler),
            Route('cdx', cdx_handler),
        },
        # Specify hostnames that pywb will be running on
        # This will help catch occasionally missed rewrites that fall-through to the host
        # (See archivalrouter.ReferRedirect)
        hostpaths = ['http://localhost:8080/'])


