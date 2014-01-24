PyWb 0.1 Alpha
==============

[![Build Status](https://travis-ci.org/ikreymer/pywb.png?branch=master)](https://travis-ci.org/ikreymer/pywb)

Python re-implementation of the Wayback Machine archival web replay.

(It is not currently deployed on archive.org)

Currently, this module handles the replay and routing components.

(The calendar page/query is just a raw CDX stream at the moment)

It read records from WARC and ARC files and rewrites them in
'archival url' format like:

`http://<host>/<collection>/<timestamp>/<original url>`


Ex: The [Internet Archive Wayback Machine][2] has urls of the form:

`http://web.archive.org/web/20131015120316/http://archive.org/`


The goal is to render archived content as accurately as possible, rewriting what is needed to generate an accurate
playback experience. 

There is a placeholder for a information banner that can be inserted.

Note: The module consumes a CDX stream, currently produced by the [wayback-cdx-server][1] and does not read the CDX index files itself.

Native support for reading CDX is in the works.


### Installation/Reqs

Currently only supports Python 2.7.x

`python setup.py install`

(Tested under 2.7.3 with uWSGI 1.9.20)

Start with `run.sh`



Sample Setup
------------

The main driver is wbapp.py and contains a sample WB declaration.

To declare Wayback with one collection, `mycoll`
and will be accessed by user at:

`http://mywb.example.com:8080/mycoll/`

and will load cdx from [cdx server][1] running at:

`http://cdx.example.com/cdx`

and look for warcs at paths:

`http://warcs.example.com/servewarc/` and
`http://warcs.example.com/anotherpath/`,

one could declare a sample config as follows:

```
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
```

The final wsgi application is than created by calling:


`application = create_wb_app(sample_wb_settings())`


Quick File Reference
--------------------

 - `archivalrouter.py`- Archival mode routing by regex and fallback based on referrer

 - `archiveloader.py` - IO for loading W/ARC data

 - `indexreader.py`,`query.py` - CDX reading (from remote cdx server)
   and parsing cdx

 - `wbarchivalurl.py` - representation of the 'archival url' eg: `/<collection>/<timestamp>/<original url>` form

 - `url_rewriter.py`, `header_rewriter.py`, `html_rewriter.py`,`regex_rewriter.py`- Various types of for rewriters. The urlrewriter converts url -> archival url, and is used by all the others. JS/CSS/XML are rewritten via regexs.
 
 - `wbrequestresponse.py` - Wrappers for request and response for WSGI, and wrapping status and headers
 
 - `replay.py` - drives the replay from archival content, either transparently or with rewriting

 - `utils.py`, `wbexceptions.py` - Misc util functions and all exceptions


 - `static/wb.css`, `static/wb.js` - static JS files, currently inserted into `<head>` and init the PyWb test banner on page load


  [1]: https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
  [2]: https://archive.org/web/
