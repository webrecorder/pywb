PyWb 0.0.1
==========

Python implementation of Wayback Machine replay.

Currently, this module handles the replay and routing components.

(The calendar page/query is just a raw CDX stream at the moment)

It read records from WARC and ARC files and rewrites them in
'archival url' format like:

`http://<host>/<collection>/<timestamp>/<original url>`

Optionally, custom text may also be inserted into the HTML head, which may render a banner or other overlay.

The Internet Archive Wayback Machine has urls of the form:

`http://web.archive.org/web/20131015120316/http://archive.org/`

Note: The module consumes a CDX stream, currently produced by the [wayback-cdx-server][1] and does not read the CDX index files itself.


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

one could declare a `createWB()` method as follows:

    def createWB():
        aloader = archiveloader.ArchiveLoader()
        query = QueryHandler(indexreader.RemoteCDXServer('http://cdx.example.com/cdx'))
    
        prefixes = [replay.PrefixResolver('http://warcs.example.com/servewarc/'),
                    replay.PrefixResolver('http://warcs.example.com/anotherpath/')]
    
        replay = replay.RewritingReplayHandler(resolvers = prefixes, archiveloader = aloader, headInsert = headInsert)
    
        return ArchivalRequestRouter(
        {
              MatchPrefix('mycoll': replay.WBHandler(query, replay)),
        },
        hostpaths = ['http://mywb.example.com:8080/'])


Quick File Reference
--------------------

 - `archivalrouter.py`- Archival mode routing and referer fallback, include MatchPrefix and MatchRegex

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
