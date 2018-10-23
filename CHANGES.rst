pywb 2.1.0 changelist
~~~~~~~~~~~~~~~~~~~~~

* Replay Fidelity Improvements:
   - Improved wombat web worker rewriting overrides, use custom modifier ``wkr_`` (#351)
   - Added checks to wombat that preserve the behavior of non-wombat added polyfills to native functions (#350)
   - Framed replay: Ensured the page title and favicon are displayed in the top-frame (#356, #369)
   - Improved replay of request sent as ``text/html`` but are actually ``application/json``` (#367)
   - Added replay of compressed resources by forcing decompression if the UA did not indicate it could handle the resources encoding (#372)
   - Added ``window.origin``, and ``setTimeout``, ``setInterval`` overrides to wombat to handle the non-function callback case (#381)
   - Added ``CSSStyleSheet.insertRule`` and ```Text``` overrides to wombat improve rewriting of dynamically added/modification of CSS (#382)
   - Remove extra ``window.frames`` override to avoid extra override if ``window.frames === window`` (#383)
   - Wombat inited via ``window._WBWombatInit(wbinfo);``, allows for reinit if inited 'synethically' and not from the page html insert (#383)
   - Added ``document.evaluate`` override in-order to deproxy the context node (#385)
   - Optimized argument de-proxying in wombat (#385)
   - Improved iframe srcdoc rewriting in wombat (#386)
   - Improved rewriting strings of full HTML by making the check case insensitive and looking for ``<!doctype html`` in wombat (#398)

* Auto Fetch System: Background image srcset and media query fetching (#359, #379, #378, #397):
   - Added image srcset and media query preservation system to wombat
   - Added ``--proxy-enable-wombat`` cli flag to enable the inject of ``wombatProxyMode.js`` in proxy mode (default: false)
   - Added ``--enable-auto-fetch`` cli flag to enable the auto fetch web worker system both url rewrite and proxy modes (default: false)
   - Added ``FrontEndApp.proxy_fetch()`` to allow the auto fetch worker to request cross-origin style sheets

* Fuzzy Matching:
    - Decreased the aggressiveness of fuzzy matching (#362)
    - Added an additional Facebook rule targeting timeline replay (#363)
    - Added vimeo rule that canonicalizes the variable ```hmac/timestamp``` portion of url (#375)

* Server-Side Rewriting:
    - Refactored the regular expression rewriters in-order to avoid multiple initialization (#354)
    - Improved unicode URL rewriting (#361, #376, #377, #380)
    - Improved cookie rewriting in framed replay mode (#386)
    - Improved handling of bad content-length HTTP header (#386)
    - Fix parsing of self-closing <script> and <style> tags and rewrite SVG xlink:href (#392)
    - Ensure 'Status' header is prefix-rewritten
    - Support using ``X-Forwarded-Proto`` header to specify scheme for URL rewriting (#395)

* Indexing:
    - Ensure that WARC/0.18 metadata records with mime = ``text/anvl`` are not replayed

* Recording:
    - Added an option to filter the source collection (#368)

* Misc Changes:
    - Added Github Issue Templates (#353)
    - Added replay testing to ci via webrecorder-tests (#355)
    - Support deploying pywb under a prefix, non-root (#373)

* Documentation improvements:
   - Improved cli help message (#360)
   - Fixed documentation enumeration bug (#364)
   - Add documentation for auto-fetch system (#394)


pywb 2.0.4 changelist
~~~~~~~~~~~~~~~~~~~~~

* Replay Fidelity Improvements:
   - Ensure title-only change event correctly handled by top-frame banner (#327)
   - Improved wombat ``document.write`` and ``document.writeln`` overrides to account for the variadic case (#325)
   - Improved wombat ``postMessage`` override logic of determining correct target origin (#328 and #338)
   - Improved server-side rewriting of ``link[rel=preload]`` (#332)
   - Improved server-side and client-side rewriting of "super relative" script src values ``script[src=path/it.php?js]`` (#334)
   - Improved wombat un-rewrite regular expression (#332)
   - Improved wombat ``Node.[appendChild|replaceChild|insertBefore]`` overrides to account for edge cases (#332)
   - Added ``MouseEvent`` override to wombat (#332)
   - Added ``insertAdjacentElement`` override to wombat (#332)
   - Added client-side rewriting of ``link[rel=preload]`` and ``link[rel=import]`` to wombat (#332)
   - Added FontFace override to wombat (#340)
   - Added server-side rewriting of ``link[rel=import]`` (#334)
   - Added SVG filter attribute rewriting to wombat (#341)
   - Improved detection of ServiceWorker JS, use ``sw_`` modifier which performs no rewriting but adds ``Service-Worker-Allowed`` header.
   - Don't bind already overridden ``requestAnimationFrame/clearAnimationFrame`` functions via JS object proxy (#350)
   - Don't reinit wombat in same window if new document is imported (#339)
   - Cookies: Use default mod ``mp_`` for client-side rewriting to ensure cookies set correctly on client-side documents (#330)

* Server-Side Rewriting:
   - Flash: Improved Rewriting for AMF, supporting py2 and py3 (#321)
   - Improved ``Origin`` header detection: Detect from ``Referer`` header if available (#329)
   - Expand JSONP matching if url contains 'callback=jsonp' (#336)
   - Ensure entity-escaped urls are rewritten, with escaping preserved (#337)

* Redirect Improvements:
   - Improved self-redirect detection for adjacent self-redirect capture results, avoiding self-redirect loops (#345)
   - Fix possible leak when handling self-redirects
   - Add slash-preserving redirect, if original ended in '/', ensure replayed version also ends with '/' (#344, #346)

* Misc Fixes:
   - Testing: Run local ``httpbin`` for any ``httpbin.org`` or ``test.httpbin.org`` tests to avoid external dependency.
   - Indexing: Avoid indexing error in py2 by decoding in utf-8 if warc has non-ascii target url (#312)
   - Gevent: Preserve %-escaped request url via ``REQUEST_URI`` (if available) to pass correct url to live upstream.

* Proxy Mode Options (#316, #317):
   - Add ``use_banner`` option, if false, disables banner insert in proxy mode (default: true)
   - Add ``use_head_insert`` option, if false, disables injecting ``head_insert.html`` in proxy mode (default: true)
   - Add ``FrontEndApp.proxy_route_request()`` to allow more customized proxy routing (default: route to fixed default collection)
   - Expand proxy mode docs


pywb 2.0.3 changelist
~~~~~~~~~~~~~~~~~~~~~

* Miscelaneous fixes:
   - Fixes for Memento Aggregation when no timeout specified (#310)
   - Fix HEAD request for replay (#309)
   - Redis Index: always decode to native string format (decode_respones=True)
   - Test fixes: Support latest fakeredis, more consistent tests (#313)
   - Support forcing scheme via ``force_scheme: https`` config option (#314)
   - Fix typo in rewrite_amf.py (#308)

* Documentation improvements:
   - Add docs for nginx deployment (#314)
   - Fix typo in memento docs (#307)
   - Mention timeout property Warcserver docs (#310)


pywb 2.0.2 changelist
~~~~~~~~~~~~~~~~~~~~~

* Top frame interaction improvements:
   - Only notify from top replay frame, never from inner replay frames
   - Don't update top frame from 'about:blank' or 'javascript:' urls
   - New title change message when 'document.title' changes
   - Fast redirect to top-frame when loading inner frame first

* addEventListener/removeEventListener override improvements: more generic override, also handle window.onmessage

* Proxy-mode improvements:
   - don't include wombat.js (unused in proxy mode by default)
   - set banner title to document.title on load
   - update docs for configuring proxy mode HTTPS certs

* cli: add -b/--bind flag to wayback cli to specify bind host (default to 0.0.0.0)


pywb 2.0.1 changelist
~~~~~~~~~~~~~~~~~~~~~

* Override ``Function.apply()`` to remove rewriting Proxy object from any native function calls
* Fix top-frame notifications in new system to use correct window
* Calendar query: Add back second display
* Fix tests when no youtube-dl installed (#270)
* Fix typos, setup.py classifiers, remove py2.6


pywb 2.0.0 changelist
~~~~~~~~~~~~~~~~~~~~~

See the docs at https://pywb.readthedocs.org for more info.

**TODO: more detailed changelist**


pywb 0.33.2 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Minor fixes from pull requests:
   - Better handling of exceptions from in wsgi_wrapper
   - Fix CommonCrawl tests
   - Fix broken links in README
   - Fix travis build (requires certauth<1.2)


pywb 0.33.1 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Client Rewriting Improvements:
   - Better rules for Instagram, Medium
   - Fix window.fetch() override
   - Work on eval() override (disabled for more testing)

* Add Python 3 classifiers to setup.py


pywb 0.33.0 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Client-Side Rewriting Improvements:
   - Video: More aggressive ``youtube-dl`` rewriting, try video query for any ``<object>`` with flashvars
   - proxy: disable most client side rewriting when in proxy mode, keep non-rewriting overrides (random, Date)
   - host relative extract: ``extract_orig()`` returns host-relative if url starts with ``/``
   - add geolocation and notifications overrides to (auto-disable)
   - proxy: use current protocl for video info query.
   - fix history check bug: support changing history to exact current origin.
   - add ``window.fetch()`` override
   - add ``srcset`` attribute rewriting
   - ajax: don't add ``X-Pywb-Requested-With`` header to ``data:`` urls
   - general JS fixes, add undefined checks before acccessing ``_wb_js``, top frame, and content frame.
  
* Server-Side Rewriting Improvements:
   - www canonicalization: improve regex to include urls containing ``\r``
   - memento: fix potential duplicate memento headers
   - proxy: when in proxy mode, only rewrite headers related to encoding or cache
   - proxy: add special 'proxy_js' rewriter which defaults to no rewriting for proxy mode but allows custom JS rules to still be applied. Used for JS and embedded JS in html.
   - WbUrl: add new modifier form starting with ``$`` in addition to ending with ``_``, eg. ``/$mod:foo/http://example.com/``
   - ajax: don't rewrite ``text/html`` responses retrieved by ajax requests (when ``X-Pywb-Requested-With`` header is present).
   
* Static Handler: if ``wsgi.file_wrapper`` fails, fallback to direct streaming of static ocntent.


pywb 0.32.1 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Template Responses: Calculate ``Content-Length`` correctly from encoded utf-8 text length

* WbUrl: Improved detection of url scheme, don't treat ``a.co/?http://foo`` as having a valid scheme


pywb 0.32.0 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Cross-Domain Framed Replay
   - pywb banner (outer) and content (inner) frames can be served from different domains
   - All cross-frame interaction done via ``postMessage``, including url, hash, cookie change notifications
  
* Server-Side Rewriting:
   - Don't rewrite relative urls (unless contain ``../`` or start with ``/``)
   - Rewrite svg ``<image>`` tag
   - Don't rewrite ``Proxy-Authenticate`` or ``WWW-Authenticate`` headers
   - Rewrite ``href`` on any element
   - Preserve HTML entities and spaces when rewriting CSS urls
   - Content detect: handle ``text/plain`` text as JS or CSS if ``js_`` or ``cs_`` modifiers used
   - Improved rewriting of ``on*`` attributes, ensure ``window.`` is added when accessing rewritten objects.
  
* Client-Side Rewriting:
   - Add cookie notification message for cookies with ``Domain=`` to allow server-side handling
   - Improved handling of Unicode prefixes, use ``decodeURI``
   - History API: properly override go, forward, back and preserve pushState/replaceState
   - Ensure client-rewriting for windows created by ``window.open``
   - Override ``navigator.sendBeacon``
   - Rewrite ``poster`` attr in dynamic elems
   - Rewrite ``src`` attr in video ``source`` elems
   
* Record Loader: Option to convert  ARC->WARC records implicitly, return WARC responses (enabled by default)
 
* Block Loader: Raise exceptions for 4xx or 5xx responses
 
* CDX API: return not found CDX error as JSON or plain text if using ``output=json`` or ``output=text``
 
 
pywb 0.31.0 changelist
~~~~~~~~~~~~~~~~~~~~~~

* HTML rewriting:
   - preserve empty attrs while parsing, eg. ``<tag attr>`` instead of ``<tag attr="">``
   - empty ``srcset`` attribute does not cause errors
   - better error checking of empty attributes for all custom parsers

* wombat/client side improvements:
   - use ``postMessage()`` for inner replay frame -> outer frame updates
   - Fix ``window.open()`` rewriting even if prototype is missing
   - Fix double-slash in relative url rewriting
   - ``Math.random()`` overrides uses correct window
  
* BufferedReader improvements:
   - More lenient of partially decompressed data, return what was decompressed instead of raising exception.
   - Support Brotli decompression, properly rewrite ``Content-Encoding: br``

* Python 2/3 Compatibility:
   - Decode all cdx fields to native string in py2
  
* BlockLoader improvements:
   - support custom profile urls, eg. ``profile+http://`` which allow a custom profile to be selected if a profile loader is registered via ``BlockLoader.set_profile_loader()``
  
   - s3 loader: support profiles and AWS creds directly set in username/password of url

* POST replay improvements:
   - support ``multipart/form-data`` encoding same as ``x-www-form-urlencoded``
   - support ``application/x-amf`` with experimental AMF rewriter (RewriteContentAMF rewriter)
   - support generic post-data matching exact base64 encoded value.


pywb 0.30.1 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Rules: match rule for Twitter video.

* Record Loader: Only parse ``http:`` and ``https:`` urls as HTTP in ``response``, ``request`` and ``revisit`` records.


pywb 0.30.0 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Support for Python 3.3+ in addition to Python 2.6+

* statusheaders: ``to_str()`` and ``to_bytes()`` to reconstruct status line and headers, with option to exclude certain headers

* cdxobject improvements:
   - ``conv_to_json()`` for serializing to json, with optional list of fields
   - ``to_json()`` and ``to_cdxj()``
   - Default JSON serialization includes all fields, except starting with ``_``
   - Default CDXJ serialization includes all fields, except urlkey and timestamp
   - Comparison operators for cdxobject
   - Reading cdxline as byte buffer, individual fields as strings (python 3)
  
* redis: full testing of ``zrangebylex`` with new fakeredis

* timeutils: add ``datetime_to_iso_date``
  
* cdx indexing refactor: rename ``DefaultRecordIter`` -> ``DefaultRecordParser``, a callable which creates an iterator

* warcrecord loader fully read streams with no content-length, don't force 204

* cookie improvements:
   - use httplib cookie pairs directly to avoid concatenated headers (eg. for ``Set-Cookie``)
   - don't remove ``max-age`` and ``expires`` when in live rewriting mode
   - convert `` UTC`` -> `` GMT`` in expires to avoid Python parsing issues
   - remove ``secure`` only if not serving from https
   - support custom cookie rewriter
   
* wombat/client side improvements:
   - rewrite ``frameElement`` -> ``WB_wombat_frameElement``, set to null for top replay frame
   - Allow changing of ``document.domain``
   - Rewrite ``<form action>`` and <input @value>`` in ``rewrite_elem``
 
* Tests: improved tests, replaced doctests of dict output to regular tests for improved compatibility with different python implementations
  
  



pywb 0.11.5 changelist
~~~~~~~~~~~~~~~~~~~~~~

* cdx index bug fix: fix bug with cdx indexing with post-append when WARC request and response records do not alternate in the WARC.

* load yaml config: ensure file stream gets closed.

* zipnum: resolve paths specified in zipnum .loc file relative to the .loc file, not to application root.


pywb 0.11.4 changelist
~~~~~~~~~~~~~~~~~~~~~~

* wombat: overrides ``window.crypto.getRandomValues()`` to use predictable 'random' values for improved
  replayability in many JS applications.

* fix gevent/uwsgi: run ``gevent.monkey.patch_all()`` explicitly when loading ``pywb.apps.wayback`` if ``GEVENT_MONKEY_PATCH=1`` env var is set. Set by default in ``uwsgi.ini`` for use with uwsgi. (Was previously relying on uwsgi ``gevent-early-monkey-patch`` but this flag is not yet available until uwsgi 2.1 is released).


pywb 0.11.3 changelist
~~~~~~~~~~~~~~~~~~~~~~

* rewrite: fix typo in ``<meta content="">`` rewrite (modifier was not being set)


pywb 0.11.2 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Rewriting: if no charset specified in original page, don't add charset to allow browser to detect.

* Rewriting: rewrite ``<meta content="">`` attribute if it is a url.

* wb.js: pad shorter timestamp to 14 digits.

* Indexing: fixed exception when indexing empty files.


pywb 0.11.1 changelist
~~~~~~~~~~~~~~~~~~~~~~

* WombatLocation: overriden properties (href, host, etc...) are enumerable to match Location to support cloning methods.

* WombatLocation: reload() override now works.
   
* Proxy: Custom ``Pywb-Rewrite-Prefix`` allows adding a custom prefix for proxy mode rewriting

* Proxy: Better error for invalid collection in ip resolve mode
   
* Warc Indexing Refactor: Allow custom iterators to buffer payload by overriding ``create_payload_buffer()`` to return a writable buffer.


pywb 0.11.0 changelist
~~~~~~~~~~~~~~~~~~~~~~

* New client-side test system for Wombat.js in place using Karma and SauceLabs with initial set of tests and travis integration.

* Wombat Improvements:
   - Better Safari/IE support: accessors overriden only when actually supported in browser, override gracefully skipped otherwise
   - Use ``getOwnPropertyDescriptor()`` to get properties in addition to ``__lookupGetter__``, ``__lookupSetter__``
   - ``baseURI`` overriden on correct prototype
   - ``CSSStyleSheet.href`` override
   - ``HTMLAnchorElement.toString()`` override
   - Avoid making ``<base>.href`` read-only
  
* Proxy Mode Improvements:
   - To avoid breaking HTTPS envelope, if no content-length provided, chunked encoding is used (HTTP/1.1) or response is buffered and content-length is computed (HTTP/1.0)
   - Rewriter: Scheme-only rewriter converts embedded urls to http or https to match the scheme of containing page.
   - IP Resolver: Supports IP cache in Redis
   - Default resolver set to cookie resolver, eg. ``cookie_resolver: true`` is the default.
   - Collection/datetime switching options removed from UI when auth or ip resolvers.
  
* Encoding: Use webencoding lib to better encode head-insert to match page encoding

* Live Proxy: Support for explicit recording mode, decoupled from using http/https proxy. Enabled when ``LiveRewriter.is_recording()`` is true. By default, http/s proxies imply recording but can be overriden in derived class.

* Rewriting: Convert relative urls for ``rel=canonical`` to absolute urls, even if not rewriting to ensure correct url.

* UI: Use custom webkit scrollbars to minimize scrollbar-in-iframe issues that sometimes occur in Chrome.

* Memento Improvements:
   - ``/collinfo.json`` by default returns a JSON spec for all collections as Memento endpoints, in a format compatible with MemGator.
   - ``Add /collinfo.json`` endpoint customizable via ``templates/collinfo.json`` and must be enabled with ``enable_coll_info: true``
   - 'Not Found' error for timemap query returns empty timemap instead of standard HTML 404.
  
* WARC Indexing:
  - Better detection of content-length < payload, skip to next record boundary and warn, if possible.
  - Use ujson if proper version (without forward-slash escaping) is available when writing CDXJ


pywb 0.10.10 changelist
~~~~~~~~~~~~~~~~~~~~~~

* extensible BlockLoadres: supported 'http', 'https', 's3' and local file system, additional
  loaders can now be registered by scheme.
  
* rewriting fixes:
   - wombat: fix occasional style rewrite bug that resulted in leaks.
   - strip leading or trailing spaces in url
   - charset: default to utf-8 if unknown charset specified in HTML

* live rewrite: LiveRewriter class overridable in config

* WARC indexing: ignore empty records when indexing and continue, rather than stopping at first empty record.

* tests: refactor integration tests to run signficantly faster.

* cdx-indexer


pywb 0.10.9.1 changelist
~~~~~~~~~~~~~~~~~~~~~~

* wombat: fix relative '/' rewrite which incorrectly handles rel scheme '//' urls


pywb 0.10.9 changelist
~~~~~~~~~~~~~~~~~~~~~~

* IPProxyResolver: Support new simple proxy resolver where collection and timestamp stored in server-side cache by IP and set via a rest api through `pywb.proxy` eg: ``curl -x "localhost:8080" http://pywb.proxy/set?ts=2015&coll=all``. No cookies or proxy auth needed in this mode. Useful for Docker-based deployments where virtual IP is fixed. Enabled with ``cookie_resolver: ip`` in ``proxy_options``.

* CDX Server: Add support for timestamp-bounded queries CDX queries ``from=`` and ``to=``, also support calendar query with (inclusive) ranges, eg. ``/2010-2015/example.com``, ``/2010-/example.com/``, ``/-2015/example.com/``.

* Proxy options: add ``use_banner`` to toggle banner insert, and ``use_client_rewrite`` to toggle wombat rewriting in proxy mode. (Client rewriting requires banner insert).

* Proxy and Video: When in proxy mode, load youtube-dl video info via proxy magic host `pywb.proxy`, and ensure CORS support.

* Rewrite: ensure ``<base>`` tag has trailing slash, or add ``<base>`` with trailing slash for host-name only urls, eg: ``http://localhost:8080/example.com``

* Rules: improved blogspot nav and yt rules, rule file cleanup

* Wombat 2.9 improvements, including:

   - improved handling of relative paths, '..', '.', '/'
   - better support for proxy mode, avoid cross-origin top-frame issues
   - rewrite_html() (document.write) override only if any html changed
   - improved form action rewrite
   - improved rewriting in 'root collection' mode
   
   
pywb 0.10.8 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Rewrite: url attribute entity unencoding only if attr starts with 'http', catch any exceptions.

* Fix top frame detection to avoid occasional banner insertion into intermediate frames.

* Fix special case ``href = "."`` rewriting.


pywb 0.10.7 changelist
~~~~~~~~~~~~~~~~~~~~~~

* wombat 2.8 improvements, including:

    - cookies: fixed rewriting with respect to comma, proper path and domain replacement
    - form action and textContent rewriting
    - document.write() improvements, buffering split tag and removing extraneous end tag
    - document.writeln() rewriting
    - object data attr conditional rewriting
    - proper ``setAttribute("style", ...`` rewriting
    - style rewrite regex now case-insensitive
    
* 10-field CDX format fully supported.
 
* rewrite: "background" attr rewriting, proper rewriting of entity-encoded attributes.
 
* Fix for regression for Vimeo videos that were recorded as Flash but replay as HTML.
  

pywb 0.10.6 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Disable url rewriting in JS by default! No longer needed due to improved client side rewriting of all urls.

* wombat 2.7 more rewriting improvements:

    - ``document.write`` override rewrites all elements, not just one top level elements.

    - iframe ``srcdoc`` also rewritten.

    - support for custom modifiers, such as ``js_`` for ``SCRIPT`` tag rewriting, otherwise for element overrides.

    - improved css rewriting, override standard css attributes on ``CSSStyleDeclaration`` to avoid mutation observers, rewrite ``STYLE`` text content.
    
    - ``postMessage``: original ``source`` window now also preserved along with origin.

    - cookie rewrite: don't remove expires, but adjust by date offset. Allow cookies to be deleted by setting to expired date.

* Embed mode, pywb framed replay can now be embedded in an iframe when ``embeddable: True`` option is set. ``postMessage`` on framed replay proxies between replay frame and embedded frame, and ``window.parent`` is not set to top replay frame, allowing access to containing frame.

* vidrw: don't replace video with generic swf, find better match.

* path index loader: ensure each request handled by own file reader.


pywb 0.10.5 changelist
~~~~~~~~~~~~~~~~~~~~~~

* wombat 2.6 client side rewriting improvements:

    - Override JS prototype getters and setters on ``href`` and ``src`` attributes of standard HTML elements, so that JavaScript access receives and sets the original url, but the element actually contains the rewritten url internally.
    
    - For ``<a>`` element override other url properties ``href``, ``hostname``, ``host``, ``pathname``, ``origin``, ``search``, ``port``, ``protocol``
    
    - Improved ``postMessage`` emulation: Ensure the original ``origin`` of the caller is saved, by wrapping ``X.postMessage`` in a special ``X.__WB_pmw(window).postMessage()`` call which will save origin of current window in X. Store origin and destination hosts.
    
    - Improved ``message`` listener emulation: Add filtering to skip messages that were not inteded for destination host.
    
    - Restored wombat if wiped by ``document.write`` / ``document.open`` (happens on FF).
    
    - When rewriting html for ``document.write``, keep ``<html>``, ``<head>``, ``<body>`` tags in rewritten html.
    
    
* Relative urls rewritten to stay relative, eg. ``/path/file.html`` -> ``/coll/http://example.com/path/file.html``
  Can be disabled with ``no_match_rel=True`` in ``rewrite_opts``.
    
* Optional ``force_html_decl`` option to add a ``<!DOCTYPE>`` or other HTML declaration if none is present.
    
* Improved handling for `redir_to_exact=False`` mode. When set, no redirect on memento timegate, and serve ``Content-Location   `` headers for actual memento, in conformance with Mememnto RFC Pattern 2.2 (http://tools.ietf.org/html/rfc7089#section-4.2.2)


* Proxy Mode Fixes: Ensure ``Content-Length`` header is always added and correct in proxy mode, needed for proper HTTPS      
  handling within ``CONNECT`` envelope.

* New default ``HostScopeCookieRewriter`` sets cookies with domain ``/coll/https://example.com/`` instead of ``/coll/``.
  Can be specified with ``cookie_scope: host`` per collection.
  This is now the default live rewrite proxy and should be much safer/secure. For rare login use cases, the collection
  root scope can be specified with ``cookie_scope: coll``.
  
* Cookie ``Path=`` value always a relative path for all cookie scopes, previously were often absolute paths.

* Default WSGI handler for ``wayback`` back to ``wsgiref``, as ``waitress`` does not support proxy mode.


pywb 0.10.2 changelist
~~~~~~~~~~~~~~~~~~~~~~

* wombat 2.5 update -- significant wombat improvements:

    - Cookies: more comprehensive client-side cookie overriding, including Path, Domain, and expires removal.

    - ``WB_wombat_location`` overriden on Object prototype, defaults to ``location`` if ``_WB_wombat_location``, the actual,     property is not set.

    - ``WB_wombat_location.href`` proxies to actual location, responsive to ``pushState`` / ``replaceState`` location changes.
    - ``.href`` and ``.src`` attributes correctly return original url in JavaScript.
    
    - More consistent and ``lookupGetter/lookupSetter`` overrides with ``Object.defineProperty``.

    - Added baseURI override, ``Element.prototype and ``document``.

    - Added ``insertAdjacentHTML()`` override.

    - Improved iframe override, including check for `contentDocument` changes.

    - Don't rewrite urls that start with ``{``

- Frames mode: ensure hash changes synchronized between inner and outer frames.

- video: don't rewrite generic 'swf' with flowplayer

- deprefix: support deprefixing of url-encoded queries.


pywb 0.10.1 changelist
~~~~~~~~~~~~~~~~~~~~~~

- Support ``Content-Encoding: deflate`` which was not being handled.

- Fix issues with ``fallback`` handlers: A POST request could result in double read of POST input data.

- ``youtube-dl`` removed from dependency as it is only needed for live proxy. (related tests only run if ``youtube-dl`` is installed).


pywb 0.10.0 changelist
~~~~~~~~~~~~~~~~~~~~~~

* Per-collection cacheing settings: ``rewrite_opts.http_cache`` can be set to:

    - ``pass`` - keep cacheing headers as-is (applies to ``Cache-Control``, ``Expires``, ``Etag`` and ``Last-Modified``)
    - ``0`` - add ``Cache-Control: no-cache; no-store``
    - ``N`` - add ``Cache-Control: max-age=N`` and corresponding ``Expires`` header
    - None (default) -- Rewrite cache headers, effectively removing them (current behavior)
  
* New improved Wombat, including:

    - better handling of new iframes set to ``about:blank``, add all overrides
    - createElement() override (can be disabled)
    - innerHTML prototype override (can be disabled)
    
* Rules: Improved rewriting for Google+, Twitter, YT comments

* Video: Improved support for LiveStream playlist, detect newly added <object> and <embed> videos (with mutation observers)

* Indexing: Add contents of ``WARC-Json-Metadata`` to ``metadata`` field in cdx-json

* Buffering: Only buffer when content-length is missing and only up-to first 16K

* ZipNum: Fix bug with contents of last block being inaccessible, improved test coverage for zipnum.
    


pywb 0.9.8 changelist
~~~~~~~~~~~~~~~~~~~~~

* auto config: allow custom settings set in shared ``config.yaml`` to be used with automatic collections.

* wombat fixes: fixes situation where setAttribute was not being rewritten.

* wombat fixes: obey ``_no_rewrite==true`` more consistently in rewrite_elem

* wombat fixes: remove incorrect timezone offset in Date override.

* wombat: new 'node added' mutation observer which will rewrite any newly added elements, may simplify other
  rewriting cases. Not enabled by default yet requires setting ``client.use_node_observers`` to use.

* regex rewrite: tweak ``top`` and scheme relative regexes to better avoid false positives

* html rewrite: handle ``parse_comments`` by rewriting as html, instead of as javascript.

* html rewrite: if html content has no <head> tags and no body tags, insert head_insert at end of document.

* html rewrite: don't insert banner in ajax requests, wombat always adds ``X-Requested-With: XMLHttpRequest``.

* scheme relative urls: rewrite to current scheme, if known, otherwise keep scheme relative, instead of defaulting to http.


pywb 0.9.7 changelist
~~~~~~~~~~~~~~~~~~~~~

* wombat enchancements: support for mutation observers instead of ``setAttribute`` override with ``client.use_attr_observers`` setting.
  Can also disable worker override with ``skip_disable_worker``
  
* wombat fixes: Better check for self-redirect when proxying ``replace()`` and ``assign()``, use ``querySelectorAll()`` for dom selection

* wombat fixes: Don't remove trailing slash in ``extract_orig()``, treat slash and no-slash urls as distinct on the client (as expected).

* cdx-indexer: Validation of HTTP protocol and request verbs now optional. Any protocol and verb will be accepted, unless ``-v`` flag is used,
  allowing for indexing of content with custom verbs, unexpected protocol, etc...


pywb 0.9.6 changelist
~~~~~~~~~~~~~~~~~~~~~

* framed replay: fix bug where outer frame url was not updated (in inverse mode) after navigating inner frame.

* framed replay: lookup frame by id, ``replay_iframe``, instead of by using ``window.frames[0]`` to allow for more customization.

* fix typo in wombat ``no_rewrite_prefixes``


pywb 0.9.5 changelist
~~~~~~~~~~~~~~~~~~~~~

* s3 loading: support ``s3://`` scheme in block loader, allowing for loading index and archive files from s3. ``boto`` library must be installed seperately
  via ``pip install boto``. Attempt default boto auth path, and if that fails, attempt anonymous s3 connection.
  
* Wombat/Client-Side Rewrite Customizations: New ``rewrite_opts.client`` settings from ``config.yaml`` are passed directly to wombat as json. 
  
  Allows for customizing wombat as needed. Currently supported options are: ``no_rewrite_prefixes`` for ignoring rewrite
  on certain domains, and ``skip_dom``, ``skip_setAttribute`` and ``skip_postmessage`` options for disabling 
  those overrides. Example usage in config:
  
  ::

    rewrite_opts:
        ...
        client:
            no_rewrite_prefixes: ['http://dont-rewrite-this.example.com/']
  
            skip_setAttribute: true
            skip_dom: true
            skip_postmessage: true
  
  
* Revamp template setup: All templates now use shared env, which is created on first use or can be explicitly set (if embedding)
  via ``J2TemplateView.init_shared_env()`` call. Support for specifiying a base env, as well as custom template lookup paths also provided
  
* Template lookup paths can also be set via config options ``templates_dirs``. The default list is: ``templates``, ``.``, ``/`` in that order.

* Embedding improvements: move custom env (``REL_REQUEST_URI`` setup) into routers, should be able to call router created by ``create_wb_router()`` 
  directly with WSGI enviorn and receive a callable response.

* Embedding improvements: If set, the contents of ``environ['pywb.template_params']`` dictionary are added directly to Jinja context, allowing for custom template
  params to be passed to pywb jinja templates.

* Root collection support: Can specify a route with `''` which will be the root collection. Fix routing paths to ensure root collection is checked last.

* Customization: support custom route_class for cdx server and pass wbrequest to ``not_found_html``  error handlers.

* Manager: Validate collection names to start with word char and contain alphanum or dash only.

* CLI refactor: easier to create custom cli apps and pass params, inherit shared params. ``live-rewrite-server`` uses new system cli system,
  defaults to framed inverse mode. Also runs on ``/live/`` path by default. See ``live-rewrite-server -h`` for a list of current options.

* Add ``cookie_scope: removeall`` cookie rewriter, which will, remove all cookies from replay headers.

* Security: disable file:// altogether for live rewrite path.

* Fuzzy match: better support for custom replace string >1 character: leave string, and strip remainder before fuzzy query.

* Urlrewriter and wburl fixes for various corner cases.

* Rangecache: use url as key if digest not present.

* Framed replay: attempt to mitigate chrome OS X scrolling issue by disabling ``-webkit-transform: none`` in framed mode. 
  Improves scrolling on many pages but not always consistent (a chrome bug).


pywb 0.9.3 changelist
~~~~~~~~~~~~~~~~~~~~~

* framed replay mode: support ``framed_replay: inverse`` where the top frame is the canonical archival url and the inner frame has ``mp_`` modifier.

* wb.js: improved redirect check: only redirect to top frame in framed mode and compare decoded urls.

* charset detection: read first 1024 bytes to determine charset and add to ``Content-Type`` header if no charset is specified there.

* indexing: support indexing of WARC records with ``urn:`` values as target uris, such as those created by `wpull <https://github.com/chfoo/wpull>`_

* remove certauth module: now using standalone `certauth <http://github.com/ikreymer/certauth>`_ package.

* BlockLoader: use ``requests`` instead of ``urllib2``.

* cdx: %-encode any non-ascii chars found in cdx fields.

* cdx: showNumPages query always return valid result (not 404) for 0 pages. If <1 block, load cdx to determine if 1 page or none.


pywb 0.9.2 changelist
~~~~~~~~~~~~~~~~~~~~~

* Collections Manager: Allow adding any templates to shared directory, fix adding WARCs with relative path.

* Replay: Remove limit by HTTP ``Content-Length`` as it may be invalid (only using the record length).

* WARC Revisit-Resolution Improvements: Support indexes and warcs without any ``digest`` field. If no digest is found, attempt to look up
  the original WARC record from the ``WARC-Refers-To-Target-URI`` and ``WARC-Refers-To-Date`` only, even for same url revisits.
  (Previously, only used this lookup original url was different from revisit url)


pywb 0.9.1 changelist
~~~~~~~~~~~~~~~~~~~~~

* Implement pagination support for zipnum cluster and added to cdx server api:

  https://github.com/ikreymer/pywb/wiki/CDX-Server-API

* cdx server query: add support for ``url=*.host`` and ``url=host/*`` as shortcuts for ``matchType=domain`` and ``matchType=prefix``

* zipnum cdx cluster: support loading index shared from prefix path instead of seperate location file.

  The ``shard_index_loc`` config property may contain match and replace properties.
  Regex replacement is then used to obtain path prefix from the shard prefix path.

* wombat: fix `document.write()` rewriting to rewrite each element at a time and use underlying write for better compatibility.


pywb 0.9.0 changelist
~~~~~~~~~~~~~~~~~~~~~

* New directory-based configuration-less init system! ``config.yaml`` no longer required.

* New ``wb-manager`` collection manager for adding warcs, indexing, adding/removing templates, setting metadata.

  More details at: `Auto-Configuration and Wayback Collections Manager <https://github.com/ikreymer/pywb/wiki/Auto-Configuration-and-Wayback-Collections-Manager>`_

* Support for user metadata via per-collection ``metadata.yaml``

* Templates: improved/simpified home page and collection search page, show user metadata by default.

* Support for writing and reading new cdx JSON format (.cdxj), with searchable key followed by json dictionary: ``urlkey timestamp { ... }`` on each line

* ``cdx-indexer -j``: support for generating cdxj format

* ``cdx-indexer -mj``: support for minimal cdx format (in JSON format) only which skips reading the HTTP record.

    Fields included in minimal format are: urlkey, timestamp, original url, record length, digest, offset, and filename

* ``cdx-indexer --root-dir <dir>``: option for custom root dir for cdx filenames to be relative to this directory.

* ``wb-manager cdx-convert``: option to convert any existing cdx to new cdxj format, including ensuring cdx key is in SURT canonicalized.

* ``wb-manager autoindex `` / ``wayback -a`` -- Support for auto-updating the cdx indexes whenever any WARC/ARC files are modified or created.

* Switch default ``wayback``,  ``cdx-server``, ``live-rewrite-server`` cli apps to use ``waitress`` WSGI container instead of wsgi ref.

  New cli options, including ``-p`` (port), ``-t`` (num threads), and ``-d`` (working directory)

* url rewrite: fixes to JS url rewrite (some urls with unencoded chars were not being rewritten),
  fixes to WbUrl parsing of urls starting with digits (eg. 1234.example.com) not being parsed properly.

* framed replay: update frame_insert.html to be html5 compliant.

* wombat: fixed to WB_wombat_location.href assignment, properly redirects to dest page even if url is already rewritten

* static paths: static content included with pywb moved from ``static/default`` -> ``static/__pywb`` to free up default as possible collection name
  and avoid any naming conflicts. For example, wombat.js can be accessed via ``/static/__pywb/wombat.js``

* default to replay with framed mode enabled: ``framed_replay: true``


pywb 0.8.3 changelist
~~~~~~~~~~~~~~~~~~~~~

* cookie rewrite: all cookie rewriters remove ``secure`` flag to allow equivalent replay of sites with cookies via HTTP and HTTPS.

* html rewrite: fix ``<base>`` tag rewriting to add a trailing slash to the url if it is a hostname with no path, ex:

  ``<base href="http://example.com" />`` -> ``<base href="http://localhost:8080/rewrite/http://example.com/" />``

* framed replay: fix double slash that remainded when rewriting top frame url.


pywb 0.8.2 changelist
~~~~~~~~~~~~~~~~~~~~~

* rewrite: fix for redirect loop related to pages with 'www.' prefix. Since canonicalization removes the prefix, treat redirect to 'www.' as self-redirect (for now).

* memento: ensure rel=memento url matches timegate redirect exactly (urls may differ due to canonicalization, use actual instead of requested for both)


pywb 0.8.1 changelist
~~~~~~~~~~~~~~~~~~~~~

* wb.js top frame notification: use ``window.__orig_parent`` when referencing actual parent as ``window.parent`` now overriden.

* live proxy security: enable ssl verification for live proxy by default, for use with python 2.7.9 ssl improvements. Was disabled
  due to incomplete ssl support in previous versions of python. Can be disabled via ``verify_ssl: False`` per collection.

* cdx-indexer: add recursive option to index warcs in all subdirectories with ``cdx-indexer -r <dir_name>``


pywb 0.8.0 changelist
~~~~~~~~~~~~~~~~~~~~~

Improvements to framed replay, memento support, IDN urls, and additional customization support in preparation for further config changes.

* Feature: Full support for 'non-exact' or sticky timestamp browsing in framed and non-framed mode.

  - setting ``redir_to_exact: False`` (per collection), no redirects will be issued to the exact timestamp of the capture.
    The user-specified timestamp will be preserved and the number of redirects will be reduced.

  - if no timestamp is present (latest-replay request), there is a redirect to the current time UTC timestamp,
    available via ``pywb.utils.timeutils.timestamp_now()`` function.

  - via head-insert, the exact request timestamp is provided as ``wbinfo.request_ts`` and accessible to the banner insert or the top frame when in framed mode.

* Frame Mode Replay Improvements, including:

  - wombat: modify ``window.parent`` and ``window.frameElement`` to hide top-level non replay frame.

  - memento improvements: add same memento headers to top-level frame to match replay frame to ensure top-level frame
    passes memento header validation.

  - frame mode uses the request timestamp instead of the capture timestamp to update frame url.
    By default, request timestamp == capture timestamp, unless ``redir_to_exact: False`` (see above).

* Client-Side Rewrite Improvements:

  - improved ``document.write`` override to also work when in ``<head>`` and append both ``<head>`` and ``<body>``

  - detect multiple calls to rewrite attribute to avoid rewrite loops.

* Customization improvements:

  - ability to override global UrlRewriter with custom class by setting ``urlrewriter_class`` config setting.

  - ability to disable JS url and location rewrite via ``js_rewrite_location: none`` setting.

  - ability to set a custom content loader in place of default ARC/WARC loader in ``ReplayView._init_replay_view``

* Improved Memento compatibility, ensuring all responses have a ``rel=memento`` link.

* IDN support: Improved handling of non-ascii domains.

  - all urls are internally converted to a Punycode host, percent encoded path using IDNA encoding (http://tools.ietf.org/html/rfc3490.html).
  - when rendering, return convert all urls to fully percent-encoded by default (to allow browser to convert to unicode characters).
  - ``punycode_links`` rewrite option can be enabled to keep ascii-punycode hostnames instead of percent-encoding.


pywb 0.7.8 changelist
~~~~~~~~~~~~~~~~~~~~~

* live rewrite fix: When forwarding ``X-Forwarded-Proto`` header, set scheme to actual url scheme to avoid possible redirect loops (#57)


pywb 0.7.7 changelist
~~~~~~~~~~~~~~~~~~~~~

* client-side rewrite: improved rewriting of all style changes using mutation observers

* rules: fix YT rewrite rule, add rule for wikimedia

* cdx-indexer: minor cleanup, add support for custom writer for batched cdx (write_multi_cdx_index)


pywb 0.7.6 changelist
~~~~~~~~~~~~~~~~~~~~~

* new not found Jinja2 template: Add per-collection-overridable ``not_found.html`` template, specified via ``not_found_html`` option. For missing resources, the ``not_found_html`` template is now used instead of the generic ``error_html``

* client-side rewrite: improved wombat rewrite of postMessage events, unrewrite target on receive, improved Vine replay

* packaging: allow adding multiple packages for Jinja2 template resolving

pywb 0.7.5 changelist
~~~~~~~~~~~~~~~~~~~~~

* Cross platform fixes to support Windows -- all tests pass on Linux, OS X and Windows now. Improved cross-platform support includes:

  - read all files as binary to avoid line ending issues
  - properly convert between platform dependent file paths and urls
  - add .gitattributes to ensure line endings on *.warc*, *.arc*, *.cdx* files are unaltered
  - avoid platform dependent apis (eg. %s for strftime)

* Change any unhandled exceptions to result in a 500 error, instead of 400.

* Setup: switch to ``zip_safe=True`` to allow for embedding pywb egg in one-file app with `pyinstaller <https://github.com/pyinstaller/pyinstaller>`_

* More compresensive client side ``src`` attribute rewriting (via wombat.js), additional server-side HTML tag rewriting.


pywb 0.7.2 changelist
~~~~~~~~~~~~~~~~~~~~~

* Experiment with disabling DASH for YT

* New ``req_cookie_rewrite`` rewrite directive to rewrite outgoing ``Cookie`` header, can be used to fix a certain cookie for a url prefix.

  A list of regex match/replace rules, applied in succession, can be set for each url prefix. See ``rules.yaml`` for more info.


pywb 0.7.1 changelist
~~~~~~~~~~~~~~~~~~~~~

* (0.7.1 fixes some missing static files from 0.7.0 release)

* Video/Audio Replay, Live Proxy and Recording Support (with pywb-webrecorder)!

  See: `Video Replay and Recording <https://github.com/ikreymer/pywb/wiki/Video-Replay-and-Recording>`_ for more detailed info.

* Support for replaying HTTP/1.1 range requests for any archived resorce (optional range cache be disabled via `enable_ranges: false`)

* Support for on-the-fly video replacement of Flash with HTML5 using new video rewrite system ``vidrw.js``.

  (Designed for all Flash videos, with varying levels of special cases for YouTube, Vimeo, Soundcloud and Dailymotion)

* Use `youtube-dl <http://rg3.github.io/youtube-dl/>`_ to find actual video streams from page urls, record video info.

* New, improved wombat 2.1 -- improved rewriting of dynamic content, including:

  - setAttribute override
  - Date override sets date to replay timestamp
  - Image() object override
  - ability to disable dynamic attribute rewriting by setting ``_no_rewrite`` on an element.

* Type detection: resolve conflict between text/html that is served under js_ mod, resolve if html or js.


pywb 0.6.6 changelist
~~~~~~~~~~~~~~~~~~~~~

* JS client side improvements: check for double-inits, preserve anchor in wb.js top location redirect

* JS Rewriters: add mixins for link + location (default), link only, location only rewriting by setting ``js_rewrite_location`` to ``all``, ``urls``, ``location``, respectively.

  (New: location only rewriting does not change JS urls)

* Beginning of new rewrite options, settable per collections and stored in UrlRewriter. Available options:

  - ``rewrite_base`` - set to False to disable rewriting ``<base href="...">`` tag
  - ``rewrite_rel_canon`` - set to false to disable rewriting ``<link rel=canon href="...">``

* JS rewrite: Don't rewrite location if starting with '$'


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

* Invert framed replay paradigm: Canonical page is always without a modifier (instead of with ``mp_``), if using frames, the page redirects to ``tf_``, and uses replaceState() to change url back to canonical form.

* Enable Memento support for framed replay, include Memento headers in top frame

* Easier to customize just the banner html, via ``banner_html`` setting in the config. Default banner uses ui/banner.html and inserts the script default_banner.js, which creates the banner.

  Other implementations may create banner via custom JS or directly insert HTML, as needed. Setting ``banner_html: False`` will disable the banner.

* Small improvements to streaming response, read in fixed chunks to allow better streaming from live.

* Improved cookie and csrf-token rewriting, including: ability to set ``cookie_scope: root`` per collection to have all replayed cookies have their Path set to application root.

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
