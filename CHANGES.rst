pywb 0.6.5 changelist
~~~~~~~~~~~~~~~~~~~~~

* fix static handling when content type can not be guessed, default to 'application/octet-stream'

* rewrite fix: understand partially encoded urls such as http%3A// in WbUrl, decode correctly

* rewrite fix: rewrite \/\/example.com and \\/\\/example.com in JS same as \\example.com

* cookies: add exact cookie rewriter which sets cookie to exact url only, never collection or host root

* don't rewrite rel=canonical links for services which rely on these

* cdx-indexer: Detect non-gzip chunk encoded .warc.gz/arc.gz archive files and show a meaningful
  error message explaining how to fix issue (uncompress and possibly use warctools warc2warc to recompress)


pywb 0.6.4 changelist
~~~~~~~~~~~~~~~~~~~~~

* Ignore bad multiline headers in warc.

* Rewrite fix: Don't parse html entities in HTML rewriter.

* Ensure cdx iterator closed when reeading.

* Rewrite fix: remove pywb prefix from any query params.

* Rewrite fix: better JS rewriting, avoid // comments when matching protocol-relative urls.

* WARC metadata and resource records include in cdx from cdx-indexer by default


pywb 0.6.3 changelist
~~~~~~~~~~~~~~~~~~~~~

* Minor fixes for extensability and support https://webrecorder.io, easier to override any request (handle_request), handle_replay or handle_query via WBHandler


pywb 0.6.2 changelist
~~~~~~~~~~~~~~~~~~~~~

* Invert framed replay paradigm: Canonical page is always without a modifier (instead of with `mp_`), if using frames, the page redirects to `tf_`, and uses replaceState() to change url back to canonical form.

* Enable Memento support for framed replay, include Memento headers in top frame

* Easier to customize just the banner html, via `banner_html` setting in the config. Default banner uses ui/banner.html and inserts the script default_banner.js, which creates the banner.

  Other implementations may create banner via custom JS or directly insert HTML, as needed. Setting `banner_html: False` will disable the banner.

* Small improvements to streaming response, read in fixed chunks to allow better streaming from live.

* Improved cookie and csrf-token rewriting, including: ability to set `cookie_scope: root` per collection to have all replayed cookies have their Path set to application root.

  This is useful for replaying sites which share cookies amongst different pages and across archived time ranges.

* New, implified notation for fuzzy match rules on query params (See: `Fuzzy Match Rules <https://github.com/ikreymer/pywb/wiki/Fuzzy-Match-Rules>`_)


pywb 0.6.0 changelist
~~~~~~~~~~~~~~~~~~~~~

* HTTPS Proxy Support! (See: `Proxy Mode Usage <https://github.com/ikreymer/pywb/wiki/Pywb-Proxy-Mode-Usage>`_)

* Revamped HTTP/S system: proxy collection and capture time switching via cookie!

* removed *hostnames* setting in config.yaml. pywb no longer needs to know the host(s) it is running on, 
  can infer the correct path from referrer on a fallback handling.

* remove PAC config, just using direct proxy (HTTP and HTTPS) for simplicity.


pywb 0.5.4 changelist
~~~~~~~~~~~~~~~~~~~~~

* bug fix: self-redirect check resolves relative Location: redirects

* rewrite rules: 'parse_comments' option to parse html comments as JS, regex rewrite update to match '&quot;http:\\\\/' double backslash

* bug fixes in framed replay for html content, update top frame for html content on load when possible


pywb 0.5.3 changelist
~~~~~~~~~~~~~~~~~~~~~
* better framed replay for non-html content -- include live rewrite timestamp via temp 'pywb.timestamp' cookie, updating banner of iframe load. All timestamp formatting moved to client-side for better customization.

* refactoring of replay/live handlers for better extensability.

* banner-only rewrite mode (via 'bn_' modifier) to support only banner insertion with no rewriting, server-side or client-side.


pywb 0.5.1 changelist
~~~~~~~~~~~~~~~~~~~~~
minor fixes:

* cdxindexer accepts unicode filenames, encodes via sys encoding

* SCRIPT_NAME now defaults to '' if not present


pywb 0.5.0 changelist
~~~~~~~~~~~~~~~~~~~~~

* Catch live rewrite errors and display more friendly pywb error message.

* LiveRewriteHandler and WBHandler refactoring: LiveRewriteHandler now supports a root search page html template.

* Proxy mode option: 'unaltered_replay' to proxy archival data with no modifications (no banner, no server or client side rewriting).

* Fix client side rewriting (wombat.js) for proxy mode: only rewrite https -> http in absolute urls.

* Fixes to memento timemap/timegate to work with framed replay mode.

* Support for a fallback handler which will be called from a replay handler instead of a 404 response.

  The handler, specified via the ``fallback`` option, can be the name of any other replay handler. Typically, it can be used with a live rewrite handler to fetch missing content from live instead of showing a 404.

* Live Rewrite can now be included as a 'collection type' in a pywb deployment by setting index path to ``$liveweb``.

* ``live-rewrite-server`` has optional ``--proxy host:port`` param to specify a loading live web data through an HTTP/S proxy, such as for use with a recording proxy.

* wombat: add document.cookie -> document.WB_wombat_cookie rewriting to check and rewrite Path= to archival url

* Better parent relative '../' path rewriting, resolved to correct absolute urls when rewritten. Additional testing for parent relative urls.

* New 'proxy_options' block, including 'use_default_coll' to allow defaulting to first collection w/o proxy auth.

* Improved support for proxy mode, allow different collections to be selected via proxy auth


pywb 0.4.7 changelist
~~~~~~~~~~~~~~~~~~~~~

* Tests: Additional testing of bad cdx lines, missing revisit records.

* Rewrite: Removal of lxml support for now, as it leads to problematic replay and not much performance improvements.

* Rewrite: Parsing of html as raw bytes instead of decode/encode, detection still needed for non-ascii compatible encoding.

* Indexing: Refactoring of cdx-indexer using a seperate 'archive record iterator' and pluggable cdx writer classes. Groundwork for creating custom indexers.

* Indexing: Support for 9 field cdx formats with -9 flag.

* Rewrite: Improved top -> WB_wombat_top rewriting.

* Rewrite: Better handling of framed replay url notification

pywb 0.4.5 changelist
~~~~~~~~~~~~~~~~~~~~~

* Support for framed or non-framed mode replay, toggleable via the ``framed_replay`` flag in the config.yaml

* Cookie rewriter: remove Max-Age to use ensure session-expiry instead of long-term cookie (experimental).

* Live Rewrite: proxy all headers, instead of a whitelist.

* Fixes to ``<base>`` tag handling, now correctly rewriting remainder of urls with the set base.

* ``cdx-indexer`` options for resolving POST requests, and indexing request records. (``-p`` and ``-a``)

* Improved `POST request replay <https://github.com/ikreymer/pywb/wiki/POST-request-replay>`_, allowing for improved replay of many captures relying on POST requests.

pywb 0.4.0 changelist
~~~~~~~~~~~~~~~~~~~~~

* Improved test coverage throughout the project.

* live-rewrite-server: A new web server for checking rewriting rules against live content. A white-list of request headers is sent to 
  the destination server. See `rewrite_live.py <https://github.com/ikreymer/pywb/blob/master/pywb/rewrite/rewrite_live.py>`_ for more details.

* Cookie Rewriting in Archival Mode: HTTP Set-Cookie header rewritten to remove Expires, rewrite Path and Domain. If Domain is used, Path is set to / to ensure cookie is visible from all archival urls.

* Much improved handling of chunk encoded responses, better handling of zero-length chunks and fix bug where not enough gzip data was read for a full chunk to be decoded. Support for chunk-decoding w/o gzip decompression
  (for example, for binary data).

* Redis CDX: Initial support for reading entire CDX 'file' from a redis key via ZRANGEBYLEX, though needs more testing.

* Jinja templates: additional keyword args added to most templates for customization, export 'urlsplit' to use by templates.

* Remove SeekableLineReader, just using standard file-like object for binary search.

* Proper handling of js_ cs_ modifiers to select content-type.

* New, experimental support for top-level 'frame mode', used by live-rewrite-server, to display rewritten content in a frame. The mp_ modifier is used
  to indicate the main page when top-level page is a frame.

* cdx-indexer: Support for creation of non-SURT, url-ordered as well SURT-ordered CDX files. 

* Further rewrite of wombat.js: support for window.open, postMessage overrides, additional rewriting at Node creation time, better hash change detection.
  Use ``Object.defineProperty`` whenever possible to better override assignment to various JS properties.
  See `wombat.js <https://github.com/ikreymer/pywb/blob/master/pywb/static/wombat.js>`_ for more info.

* Update wombat.js to support: scheme-relative urls rewriting, dom manipulation rewriting, disable web Worker api which could leak to live requests

* Fixed support for empty arc/warc records. Indexed with '-', replay with '204 No Content'

* Improve lxml rewriting, letting lxml handle parsing and decoding from bytestream directly (to address #36)


pywb 0.3.0 changelist
~~~~~~~~~~~~~~~~~~~~~

* Generate cdx indexs via command-line `cdx-indexer` script. Optionally sorting, and output to either a single combined file or a file per-directory.
  Refer to ``cdx-indexer -h`` for more info.
  
* Initial support for prefix url queries, eg: http://localhost:8080/pywb/\*/http://example.com\* to query all captures from http://example.com

* Support for optional LXML html-based parser for fastest possible parsing. If lxml is installed on the system and via ``pip install lxml``, lxml parser is enabled by default.
  (This can be turned off by setting ``use_lxml_parser: false`` in the config)

* Full support for `Memento Protocol RFC7089 <http://www.mementoweb.org/guide/rfc/>`_ Memento, TimeGate and TimeMaps. Memento: TimeMaps in ``application/link-format`` provided via the ``/timemap/*/`` query.. eg: http://localhost:8080/pywb/timemap/\*/http://example.com
  
* pywb now features new `domain-specific rules <https://github.com/ikreymer/pywb/blob/master/pywb/rules.yaml>`_ which are applied to resolve and render certain difficult and dynamic content, in order to make accurate web replay work.
  This ruleset will be under further iteration to address further challenges as the web evoles.
