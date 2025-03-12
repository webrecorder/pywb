.. _configuring-pywb:

Configuring the Web Archive
===========================

pywb offers an extensible YAML based configuration format via a main ``config.yaml`` at the root of each web archive.

.. _framed_vs_frameless:

Framed vs Frameless Replay
--------------------------

pywb supports several modes for serving archived web content.

With **framed replay**, the archived content is loaded into an iframe, and a top frame UI provides info and metadata.
In this mode, the top frame url is for example, ``http://my-archive.example.com/<coll name>/http://example.com/`` while
the actual content is served at ``http://my-archive.example.com/<coll name>/mp_/http://example.com/``

With **frameless replay**, the archived content is loaded directly. As of pywb 2.7, frameless replay is bannerless
unless a custom banner is added via the ``custom_banner.html`` template.


.. warning::
    pywb 2.7 introduces a breaking change around frameless replay and banners.
    Any custom banner intended to be used with frameless replay in pywb 2.7 and
    higher must be specified in the ``custom_banner.html`` template. This may
    require moving custom content from ``banner.html`` to the new
    ``custom_banner.html``.

    The default banner will no longer be served in frameless replay.


In this mode, the content is served directly at ``http://my-archive.example.com/<coll name>/http://example.com/``

For security reasons, we recommend running pywb in framed mode, because a malicious site
`could tamper with the banner <http://labs.rhizome.org/presentations/security.html#/13>`_

However, for certain situations, frameless replay made be appropriate.

To disable framed replay add:

``framed_replay: false`` to your config.yaml


Note: pywb also supports HTTP/S **proxy mode** which requires additional setup. See :ref:`https-proxy` for more details.

.. _client_side_replay:

Client-side replay
------------------

In pywb 2.8.0+, client-side replay can optionally be enabled for framed replay.

To enable client-side framed replay add:

``client_side_replay: true`` to your config.yaml

In this mode, pywb will use the `wabac.js <https://github.com/webrecorder/wabac.js>`_ service worker-based replay system that underlines `ReplayWeb.page <https://replayweb.page/>`_ in live proxy mode. This may result in better replay for certain JavaScript-heavy sites.


.. _dir_structure:

Directory Structure
-------------------

The pywb system is designed to automatically access and manage web archive collections that follow a defined directory structure.
The directory structure can be fully customized and "special" collections can be defined outside the structure as well.

The default directory structure for a web archive is as follows::


    +-- config.yaml (optional)
    |
    +-- templates (optional)
    |
    +-- static (optional)
    |
    +-- collections
        |
        +-- <coll name>
            |
            +-- archive
            |     |
            |     +-- (WARC or ARC files here)
            |
            +-- indexes
            |     |
            |     +-- (CDXJ index files here)
            |
            |
            +-- acl
            |     |
            |     +-- (.aclj access control files)
            | 
            +-- templates
            |     |
            |     +-- (optional html templates here)
            |
            +-- static
                  |
                  +-- (optional custom static assets here)
              

If running with default settings, the ``config.yaml`` can be omitted.

It is possible to config these directory paths in the config.yaml
The following are some of the implicit default settings which can be customized::

  collections_root: collections
  archive_paths: archive
  index_paths: indexes

(For a complete list of defaults, see the ``pywb/default_config.yaml`` file for reference)

Index Paths
^^^^^^^^^^^

The ``index_paths`` key defines the subdirectory for index files (usually CDXJ) and determine the contents of each archive collection.

The index files usually contain a pointer to a WARC file, but not the absolute path.

Archive Paths
^^^^^^^^^^^^^

The ``archive_paths`` key indicates how pywb will resolve WARC files listed in the index.

For example, it is possible to configure multiple archive paths::

  archive_paths:
    - archive
    - http://remote-bakup.example.com/collections/

When resolving a ``example.warc.gz``, pywb will then check (in order):

 * First, ``collections/<coll name>/example.warc.gz``
 * Then, ``http://remote-backup.example.com/collections/<coll name>/example.warc.gz`` (if first lookup unsuccessful)


Access Controls
^^^^^^^^^^^^^^^

With pywb 2.4, pywb includes an extensible :ref:`access-control` system.
By default, the access control files are stored in ``acl`` directory of each collection.


UI Customizations
^^^^^^^^^^^^^^^^^

The  ``templates`` directory supports custom Jinja templates to allow customizing the UI.
See :ref:`ui-customizations` for more details on available options.


Special and Custom Collections
------------------------------

While pywb can detect automatically collections following the above directory structure,
it also provides the option to fully declare :ref:`custom-coll` explicitly.

In addition, several "special" collection definitions are possible.

All custom defined collections are placed under the ``collections`` key in ``config.yaml``

.. _live-web:

Live Web Collection
^^^^^^^^^^^^^^^^^^^

The live web collection proxies all data to the live web, and can be defined as follows::

  collections:
    live: $live

This configures the ``/live/`` route to point to the live web.

(As a shortcut, ``wayback --live`` adds this collection via cli w/o modifying the config.yaml)

This collection can be useful for testing, or even more powerful, when combined with recording.


SOCKS Proxy for Live Web
""""""""""""""""""""""""

pywb can be configured to use a SOCKS5 proxy when connecting to the live web. This allows pywb to be used with `Tor <https://torproject.org/>`_ and other
services that require a SOCKS proxy.

If the ``SOCKS_HOST`` and optionally ``SOCKS_PORT`` environment variables are set, pywb will attempt to route all live web traffic through the SOCKS5 proxy.
Note that, at this time, it is not possible to configure a SOCKS proxy per pywb collection -- all live web traffic will use the SOCKS proxy if enabled.


.. _auto-all:

Auto "All" Aggregate Collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The aggregate all collections automatically aggregates data from all collections in the ``collections`` directory::

  collections:
    all: $all

Accessing ``/all/<url>`` will cause an aggregate lookup within the collections directory.

Note: It is not (yet) possible to exclude collections from the auto-all collection, although "special" collections are not included.

Collection Provenance
"""""""""""""""""""""

When using the auto-all collection, it is possible to determine the original collection of each resource by looking at the ``Link`` header metadata
if :ref:`memento-api` is enabled. The header will include the extra ``collection`` field, specifying the collection::

  Link: <http://example.com/>; rel="original", <http://localhost:8080/all/mp_/http://example.com/>; rel="timegate", <http://localhost:8080/all/timemap/link/http://example.com/>; rel="timemap"; type="application/link-format", <http://localhost:8080/all/20170920185327mp_/http://example.com/>; rel="memento"; datetime="Wed, 20 Sep 2017 18:20:19 GMT"; collection="coll-1"


For example, if two collections ``coll-1`` and ``coll-2`` contain ``http://example.com/``, loading the timemap for
``/all/timemap/link/http://example.com/`` might look like as follows::

  <http://localhost:8080/all/timemap/link/http://example.com/>; rel="self"; type="application/link-format"; from="Wed, 20 Sep 2017 03:53:27 GMT",
  <http://localhost:8080/all/mp_/http://example.com/>; rel="timegate",
  <http://example.com/>; rel="original",
  <http://example.com/>; rel="memento"; datetime="Wed, 20 Sep 2017 03:53:27 GMT"; collection="coll-1",
  <http://example.com/>; rel="memento"; datetime="Wed, 20 Sep 2017 04:53:27 GMT"; collection="coll-2",


Remote Memento Collection
^^^^^^^^^^^^^^^^^^^^^^^^^

It's also possible to define remote archives as easily as location collections.
For example, the following defines a collection ``/ia/`` which accesses
Internet Archive's Wayback Machine as a single collection::

  collections:
    ia: memento+https://web.archive.org/web/

Many additional options, including memento "aggregation", fallback chains are possible
using the Warcserver configuration syntax. See :ref:`warcserver-config` for more info.


.. _custom-coll:

Custom User-Defined Collections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The collection definition syntax allows for explicitly setting the index, archive paths
and all other templates, per collection, for example::

  collections:
    custom:
       index: ./path/to/indexes
       resource: ./some/other/path/to/archive/
       query_html: ./path/to/templates/query.html


If possible, it is recommended to use the default directory structure to avoid per-collection configuration.
However, this configuration allows for using pywb with existing collections that have unique path requirements.


Root Collection
^^^^^^^^^^^^^^^

It is also possible to define a "root" collection, for example, accessible at ``http://my-archive.example.com/<url>``
Such a collection must be defined explicitly using the ``$root`` as collection name::

  collections:
    $root:
       index: ./path/to/indexes
       resource: ./path/to/archive/

Note: When a root collection is set, no other collections are currently accessible, they are ignored.


.. _recording-mode:

Recording Mode
--------------

Recording mode enables pywb to support recording into any automatically managed collection, using
the ``/<coll>/record/<url>`` path. Accessing this path will result in pywb writing new WARCs directly into 
the collection ``<coll>``.

To enable recording from the live web, simply run ``wayback --record``.

To further customize recording mode, add the ``recorder`` block to the root of ``config.yaml``.

The command-line option is equivalent to adding ``recorder: live``.

The full set of configurable options (with their default settings) is as follows::

  recorder:
     source_coll: live
     rollover_size: 100000000
     rollover_idle_secs: 600
     filename_template: my-warc-{timestamp}-{hostname}-{random}.warc.gz
     source_filter: live
     enable_put_custom_record: false

The required ``source_coll`` setting specifies the source collection from which to load content that will be recorded.
Most likely this will be the :ref:`live-web` collection, which should also be defined. 
However, it could be any other collection, allowing for "extraction" from other collections or remote web archives.
Both the request and response are recorded into the WARC file, and most standard HTTP verbs should be recordable.

The other options are optional and may be omitted. The ``rollover_size`` and ``rollover_idle_secs`` specified
the maximum size and maximum idle time, respectively, after which a new WARC file is created.
For example, a new WARC will be created if more than 100MB are recorded, or after 600 seconds have elapsed between
subsequent requests. This allows the WARC size to be more manageable and prevents files from being left open for long periods of time.

The ``filename-template`` specifies the naming convention for WARC files, and allows a timestamp, current hostname, and
random string to be inserted into the filename.

When using an aggregate collection or sequential fallback collection as the source, recording can be limited to pages
fetched from certain child collection by specifying ``source_filter`` as an regex matching the name of the sub-collection.

For example, if recording with the above config into a collection called ``my-coll``, the user would access:

``http://my-archive.example.com/my-coll/record/http://example.com/``, which would load ``http://example.com/`` from the live web
and write the request and response to a WARC named something like:

``./collections/my-coll/archive/my-warc-20170102030000000000-archive.example.com-QRTGER.warc.gz``

If running with auto indexing, the WARC will also get automatically indexed and available for replay after the index interval.

As a shortcut, ``recorder: live`` can also be used to specify only the ``source_coll`` option.


Dedup Options for Recording
^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, recording mode will record every URL.

Starting with pywb 2.5.0, it is possible to configure pywb to either write revisit records or skip duplicate URLs altogether using the ``dedup_policy`` key.

Using deduplication requires a Redis instance, which will keep track of the index for deduplication in a sorted-set key.
The default Redis key used is ``redis://localhost:6379/0/pywb:{coll}:cdxj`` where ``{coll}`` is replaced with current collection id.

The field can be customized using the ``dedup_index_url`` field in the recorder config. The URL must start with ``redis://``, as that is the only
supported dedup index at this time.

- To skip duplicate URLs, set ``dedup_policy: skip``. With this setting, only one instance of any URL will be recorded.

- To write revist records, set ``dedup_policy: revisit``. With this setting, WARC ``revisit`` records will be written when a duplicate URL is detected
and has the same digest as a previous response.

- To keep all duplicates, use ``dedup_policy: keep``. All WARC records are written to disk normally as with no policy, however, the Redis dedup index is still populated,
which allows for instant replay (see below).

- To disable the dedup system, set to ``dedup_policy: none`` or omit the field. This is the default, and no Redis is required.

Another option, pywb can add an aggressive Cache-Control header to force the browser to cache all responses on a page.
This feature is still experimental, but can be enabled via ``cache: always`` setting.


For example, the following will enable ``revisit`` records to be written using the given Redis URL, and also enable aggressive cacheing when recording::

  recorder:
     ...
     cache: always
     dedup_policy: revisit
     dedup_index_url: 'redis://localhost:6379/0/pywb:{coll}:cdxj'   # default when omitted


Instant Replay (experimental)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Starting with pywb 2.5.0, when the ``dedup_policy`` is set, pywb can do 'instant replay' after recording, without having to regenerate the CDX or waiting for it to be updated with auto-indexing.

When any dedup_policy, pywb can also access the dedup Redis index, along with any on-disk CDX, when replaying the collection.

This feature is still experimental but should generally work. Additional options for working with the Redis Dedup index will be added in the futuer.


.. _put-custom-record:

Adding Custom Resource Records
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

pywb now also supports adding custom data to a WARC ``resource`` record. This can be used to add custom resources, such as screenshots, logs, error messages,
etc.. that are not normally captured as part of recording, but still useful to store in WARCs.

To add a custom resources, simply call ``PUT /<coll>/record`` with the data to be added as the request body and the type of the data specified as the content-type. The ``url`` can be specified as a query param.

For example, adding a custom record ``file:///my-custom-resource`` containing ``Some Custom Data`` can be done using ``curl`` as follows::

  curl -XPUT "localhost:8080/my-web-archive/record?url=file:///my-custom-resource" --data "Some Custom Data"


This feature is only available if ``enable_put_custom_record: true`` is set in the recorder config.


.. _auto-fetch:

Auto-Fetch Responsive Recording
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When recording (or browsing the 'live' collection), pywb has an option to inspect and automatically fetch additional resources, including:

 * Any urls found in ``<img srcset="...">`` attributes.

 * Any urls within CSS ``@media`` rules.

This allows pywb to better capture responsive pages, where all the resources are not directly loaded by the browser, but may be needed for future replay.

The detected urls are loaded in the background using a web worker while the user is browsing the page.

To enable this functionality, add ``--enable-auto-fetch`` to the command-line or ``enable_auto_fetch: true`` to the root of the ``config.yaml``

The auto-fetch system is provided as part of the :ref:`wombat`


Auto-Indexing Mode
------------------

If auto-indexing is enabled, pywb will update the indexes stored in the ``indexes`` directory whenever files are added or modified in the
``archive`` directory. Auto-indexing can be enabled via the ``autoindex`` option set to the check interval in seconds::

  autoindex: 30

This specifies that the ``archive`` directories should be every 30 seconds. Auto-indexing is useful when WARCs are being
appended to or added to the ``archive`` by an external operation.

If a user is manually adding a new WARC to the collection, ``wb-manager add <coll> <path/to/warc>`` is recommended,
as this will add the WARC and perform a one-time reindex the collection, without the need for auto-indexing.

Note: Auto-indexing also does not support deletion of removal of WARCs from the ``archive`` directory.

This is not a common operation for web archives, a WARC must be manually removed from the 
``collections/<coll>/archive/`` directory and then collection index can be regenreated from the remaining WARCs
by running ``wb-manager reindex <coll>``

The auto-indexing mode can also be enabled via command-line by running ``wayback -a`` or ``wayback -a --auto-interval 30`` to also set the interval.

(If running pywb with uWSGI in multi-process mode, the auto-indexing is only run in a single worker to avoid race conditions and duplicate indexing)


.. _wombat:

Client-Side Rewriting System (wombat.js)
----------------------------------------

In addition to server-side rewriting, pywb includes a Javascript client-rewriting system.

This system intercepts network traffic and emulates the correct JS environment expected by a replayed page.

The auto-fetch system is also implemented as part of wombat.

Wombat was integrated into pywb upto 2.2.x. Starting with 2.3, wombat has been spun off into its own
standalone JS module.

For more information on wombat.js and client-side rewriting, see the `wombat README <https://github.com/webrecorder/wombat/blob/master/README.md>`_


.. _https-proxy:

HTTP/S Proxy Mode
-----------------

In addition to "url rewriting prefix mode" (the default), pywb can also act as a full-fledged HTTP and HTTPS proxy, allowing
any browser or client supporting HTTP and HTTPS proxy to access web archives through the proxy.

Proxy mode can provide access to a single collection at time, eg. instead of accessing ``http://localhost:8080/my-coll/2017/http://example.com/``,
the user enters ``http://example.com/`` and is served content from the ``my-coll`` collection.
As a result, the collection and timestamp must be specified separately.

Configuring HTTP Proxy
^^^^^^^^^^^^^^^^^^^^^^

At this time, pywb requires the collection to be configured at setup time (though collection switching will be added soon).

To enable proxy mode, the collection can be specified by running: ``wayback --proxy my-coll`` or by adding to the config::

  proxy:
    coll: my-coll

For HTTP proxy access, this is all that is needed to use the proxy. If pywb is running on port 8080 on localhost, the following curl command should provide proxy access: ``curl -x "localhost:8080"  http://example.com/``


Default Timestamp
^^^^^^^^^^^^^^^^^

The timestamp can also be optionally specified by running: ``wayback --proxy my-coll --proxy-default-timestamp 20181226010203`` or by specifying the config::

  proxy:
    coll: my-coll
    default_timestamp: "20181226010203"

The ISO date format, eg. ``2018-12-26T01:02:03`` is also accepted.

If the timestamp is omitted, proxy mode replay defaults to the latest capture.

The timestamp can also be dynamically overriden per-request using the :ref:`memento-proxy`.


Proxy Mode Rewriting
^^^^^^^^^^^^^^^^^^^^

By default, pywb performs minimal html rewriting to insert a default banner into the proxy mode replay to make it clear to users that they are viewing replayed content.

Custom rewriting code from the ``head_insert.html`` template may also be inserted into ``<head>``.

Checking for the ``{% if env.pywb_proxy_magic %}`` allows for inserting custom content for proxy mode only.

However, content rewriting in proxy mode is not necessary and can be disabled completely by customizing the ``proxy`` block in the config.

This may be essential when proxying content to older browsers for instance.

 * To disable all content rewriting/modifications from pywb via the ``head_insert.html`` template, add ``enable_content_rewrite: false``

   If set to false, this setting overrides and disables all the other options.

 * To disable just the banner, add ``enable_banner: false``

 * To add a light version of rewriting (for overriding Date, random number generators), add ``enable_wombat: true``


If :ref:`auto-fetch` is enabled in the global config, the ``enable_wombat: true`` is implied, unless ``enable_content_rewrite: false``
is also set (as it will disable the auto-fetch system from being injected into the page).


If omitted, the defaults for these options are::

   proxy:
     enable_banner: true
     enable_wombat: false
     enable_content_rewrite: true

For example, to enable wombat rewriting but disable the banner, use the config::

   proxy:
     enable_banner: false
     enable_wombat: true

To disable all content rewriting::

   proxy:
     enable_content_rewrite: false


Proxy Recording
^^^^^^^^^^^^^^^

The proxy can additional be set to recording mode, equivalent to access the ``/<my-coll>/record/`` path,
by adding ``recording: true``, as follows::

  proxy:
    coll: my-coll
    recording: true

By default, proxy recording will use the ``live`` collection if not otherwise configured.

See :ref:`recording-mode` for full set of configurable recording options.


HTTPS Proxy and pywb Certificate Authority
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For HTTPS proxy access, pywb provides its own Certificate Authority and dynamically generates certificates for each host and signs the responses
with these certificates. By design, this allows pywb to act as "man-in-the-middle" serving archived copies of a given site.

However, the pywb Certificate Authority (CA) certificate will need to be accepted by the browser. The CA cert can be downloaded from pywb directly
using the special download paths. Recommended set up for using the proxy is as follows:

1. Start pywb with proxy mode enabled (with ``--proxy`` option or with a ``proxy:`` option block present in the config).

   (The CA root certificate will be auto-created when first starting pywb with proxy mode if it doesn't exist.)

2. Configure the browser proxy settings host port, for example ``localhost`` and ``8080`` (if running locally)

3. Download the CA:

   * For most browsers, use the PEM format: ``http://wsgiprox/download/pem``

   * For windows, use the PKCS12 format: ``http://wsgiprox/download/p12``

4. You may need to agree to "Trust this CA" to identify websites.

The auto-generated pywb CA, created at ``./proxy-certs/pywb-ca.pem`` may also be added to a keystore directly.

The location of the CA file and the CA name displayed can be changed by setting the  ``ca_file_cache`` and ``ca_name`` proxy options, respectively.

The following are all the available proxy options -- only ``coll`` is required::

  proxy:
    coll: my-coll
    ca_name: pywb HTTPS Proxy CA
    ca_file_cache: ./proxy-certs/pywb-ca.pem
    recording: false
    enable_banner: true
    enable_content_rewrite: true
    default_timestamp: ''

The HTTP/S functionality is provided by the separate :mod:`wsgiprox` utility which provides HTTP/S proxy routing
to any WSGI application.

Using `wsgiprox <https://github.com/webrecorder/wsgiprox>`_, pywb sets ``FrontEndApp.proxy_route_request()`` as the proxy resolver, and this function returns the full collection path that pywb uses to route each proxy request. The default implementation returns a path to the fixed collection ``coll`` and injects content into ``<head>`` if ``enable_content_rewrite`` is true. The default banner is inserted if ``enable_banner`` is set to true.

Extensions to pywb can override ``proxy_route_request()`` to provide custom handling, such as setting the collection dynamically or based on external data sources.

See the `wsgiprox README <https://github.com/webrecorder/wsgiprox/blob/master/README.rst>`_ for additional details on setting a proxy resolver.

For more information on custom certificate authority (CA) installation, the `mitmproxy certificate page <http://docs.mitmproxy.org/en/stable/certinstall.html>`_ provides a good overview for installing a custom CA on different platforms.


Compatibility: Redirects, Memento, Flash video overrides
--------------------------------------------------------

Exact Timestamp Redirects
^^^^^^^^^^^^^^^^^^^^^^^^^

By default, pywb does not redirect urls to the 'canonical' representation of a url with the exact timestamp.

For example, when requesting ``/my-coll/2017js_/http://example.com/example.js`` but the actual timestamp of the resource is ``2017010203000400``,
there is not a redirect to ``/my-coll/2017010203000400js_/http://example.com/example.js``.


Instead, this 'canonical' url is returned with the response in the ``Content-Location`` header.
(This behavior is recommended for performance reasons as it avoids an extra roundtrip to the server for a redirect.)

However, if the classic redirect behavior is desired, it can be enable by adding::

  redirect_to_exact: true

to the config. This will force any url to be redirected to the exact url, and is consistent with previous behavior and other "wayback machine" implementations.


Memento Protocol
^^^^^^^^^^^^^^^^

:ref:`memento-api` support is enabled by default, and works with no-timestamp-redirect and classic redirect behaviors.

However, Memento API support can be disabled by adding::

  enable_memento: false


Flash Video Override
^^^^^^^^^^^^^^^^^^^^

A custom system to override Flash video with a custom download via ``youtube-dl`` and replay with a custom player was enabled in previous versions of pywb.
However, this system was not widely used and is in need of improvements, and was designed when most video was Flash-based.
The system is seldom used now that most video is HTML5 based.

For these reasons, this functionality, previously enabled by including the script ``/static/vidrw.js``, is disabled by default.

To enable the previous behavior, add to config::

  enable_flash_video_rewrite: true

The system may be revamped in the future and enabled by default, but for now, it is provided "as-is" for compatibility reasons.

Verify SSL-Certificates
-----------------------

By default, SSL-Certificates of websites are not verified. To enable verification, add the following to the config::

  certificates:
    cert_reqs: 'CERT_REQUIRED'
    ca_cert_dir: '/etc/ssl/certs'

``ca_cert_dir`` can optionally point to a directory containing the CA certificates that you trust. Most linux distributions provide CA certificates via a package called ``ca-certificates``.
If omitted, the default system CA used by Python is used.
