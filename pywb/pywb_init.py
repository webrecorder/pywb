import archiveloader
import query
import indexreader
import replay
import replay_resolvers
import cdxserve
from archivalrouter import ArchivalRequestRouter, Route
import os


def pywb_config(head_insert = ''):
    # Current test dir
    test_dir = os.path.dirname(os.path.realpath(__file__)) + '/../test/'

    # Standard loader which supports WARC/ARC files
    aloader = archiveloader.ArchiveLoader()

    # Source for cdx source
    #query_h = query.QueryHandler(indexreader.RemoteCDXServer('http://cdx.example.com/cdx'))
    #test_cdx = [test_dir + 'iana.cdx', test_dir + 'example.cdx', test_dir + 'dupes.cdx']
    query_h = query.QueryHandler(indexreader.LocalCDXServer([test_dir]))

    # Loads warcs specified in cdx from these locations
    prefixes = [replay_resolvers.PrefixResolver(test_dir)]

    # Create rewriting replay handler to rewrite records
    replayer = replay.RewritingReplayHandler(resolvers = prefixes, archiveloader = aloader, headInsert = head_insert, buffer_response = True)

    # Create Jinja2 based html query renderer
    htmlquery = query.J2QueryRenderer('./ui/', 'query.html')

    # Handler which combins query, replayer, and html_query
    wb_handler = replay.WBHandler(query_h, replayer, htmlquery = htmlquery)

    # Finally, create wb router
    return ArchivalRequestRouter(
        {
            Route('echo_req', query.DebugEchoRequest()), # Debug ex: just echo parsed request
            Route('pywb',   wb_handler),
            Route('cdx', query_h)
        },
        # Specify hostnames that pywb will be running on
        # This will help catch occasionally missed rewrites that fall-through to the host
        # (See archivalrouter.ReferRedirect)
        hostpaths = ['http://localhost:8080/'])


