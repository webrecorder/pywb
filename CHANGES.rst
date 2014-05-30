pywb 0.4.0 changelist
~~~~~~~~~~~~~~~~~~~~~

* Improved test coverage throughout the project.

* live-rewrite-server: A new web server for checking rewriting rules against live content. A white-list of request headers is sent to 
  the destination server. See `rewrite_live.py <https://github.com/ikreymer/pywb/blob/develop/pywb/rewrite/rewrite_live.py>`_ for more details.

* Cookie Rewriting in Archival Mode: HTTP Set-Cookie header rewritten to remove Expires, rewrite Path and Domain. If Domain is used, Path is set to / to ensure cookie is visible
  from all archival urls.

* Much improved handling of chunk encoded responses, better handling of zero-length chunks and fix bug where not enough gzip data was read for a full chunk to be decoded. Support for chunk-decoding w/o gzip decompression
  (for example, for binary data).

* Redis CDX: Initial support for reading entire CDX 'file' from a redis key via ZRANGEBYLEX, though needs more testing.

* Jinja templates: additional keyword args added to most templates for customization, export 'urlsplit' to use by templates.

* Remove SeekableLineReader, just using standard file-like object for binary search.

* Proper handling of js_ cs_ modifiers to select content-type.

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
