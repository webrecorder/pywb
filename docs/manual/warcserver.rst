.. _warcserver:

Warcserver
----------

The Warcserver component is the base component of the pywb stack and can function as a standalone HTTP server.

The Warcserver receives as input an HTTP request, and can serve WARC records from a variety of sources, including local WARC (or ARC) files, remote archives and the live web.

This process consists of an index lookup and a resource fetch. The index lookup is performed using the index (CDX) Server API, which is also exposed by the warcserver as a standalone API.

The warcserver can be started directly installing pywb simply by running ``warcserver`` (default port is 8070).

Note: when running ``wayback``, an instance of ``warcserver`` is also started automatically.


.. _warcserver-api:

Warcserver API
^^^^^^^^^^^^^^

The Warcserver API encompasses the :ref:`cdx-server-api` and provides a per collection endpoint, using a list of collections
defined in a YAML config file (default ``config.yaml``). It's also possible to use Warcserver without the YAML config (see: :ref:`custom-warcserver`). The endpoints are as follows:


* ``/`` - Home Page, JSON list of available endpoints.

For each collection ``<coll>``:

* ``/<coll>/index`` -- Direct Index (compatible with :ref:`cdx-server-api`)

* ``/<coll>/resource`` -- Direct Resource

* ``/<coll>/postreq/index`` -- POST request Index

* ``/<coll>/postreq/resource`` -- POST request Resource (most flexible for integration with downstream tools)

All endpoints accept the :ref:`cdx-server-api` query arguments, although the "direct index" route is usually most useful for index lookup.
while the "post request resource" route is most useful for integration with other downstream client tools.


POSTing vs Direct Input
"""""""""""""""""""""""

The Warcserver is designed to map input requests to output responses, and it is possible to send input requests "directly", eg::

  GET /coll/resource?url=http://example.com/
  Connection: close

or by "wrapping" the entire request in a POST request::

  POST /coll/postreq/resource?url=http://example.com/
  Content-Length: ...
  ...

  GET /
  Host: example.com
  Connection: close

The "post request" (``/postreq`` endpoint) approach allows more accurately transmitting any HTTP request and headers in the body of another POST request, without worrying about how the headers might be interpreted by the Warcserver connection. The "wrapped HTTP request" is thus unwrapped and processed, allowing hop-by-hop headers like ``Connection: close`` to be processed unaltered.

Index vs Resource Output
""""""""""""""""""""""""

For any query, the Warcserver can return a matching index result, or the first available WARC record.

Within each collection and input type, the following endpoints are available:

* ``/index`` - perform index lookup

* ``/resource`` - return a single WARC record for the first match of the index list.


For example, an index query might return the CDXJ index::

  => curl "http://localhost:8070/pywb/index?url=iana.org"
  org,iana)/ 20140126200624 {"url": "http://www.iana.org/", "mime": "text/html", "status": "200", "digest": "OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB", "redirect": "-", "robotflags": "-", "length": "2258", "offset": "334", "filename": "iana.warc.gz", "source": "pywb:iana.cdx"}


While switching to ``resource``, the result might be::

  => curl "http://localhost:8070/pywb/index?url=iana.org

  WARC/1.0
  WARC-Type: response
  ...


The resource lookup attempts to load the first available record (eg. by loading from specified WARC). If the record indicated by first line CDXJ line is not available,
the next CDXJ line is tried in succession, and so on, until one succeeds.

If no record can be loaded from any of the CDXJ index results (or if there are no index results), a 404 Not Found error is returned.

WARC Record HTTP Response
"""""""""""""""""""""""""

When using Warcserver, the entire *WARC record* is included in the HTTP response. This may seem confusing as the WARC record itself contains an HTTP response! Warcserver also includes additional metadata as custom HTTP headers.

The following example illustrates what is transmitted when retrieving ``curl``-ing ``http://localhost:8070/pywb/index?url=iana.org``::

  > GET /pywb/resource?url=iana.org HTTP/1.1
  > Host: localhost:8070
  > User-Agent: curl/7.54.0
  > Accept: */*
  > 
  < HTTP/1.1 200 OK
  < Warcserver-Cdx: org,iana)/ 20140126200624 {"url": "http://www.iana.org/", "mime": "text/html", "status": "200", "digest": "OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB", "redirect": "-", "robotflags": "-", "length": "2258", "offset": "334", "filename": "iana.warc.gz", "source": "pywb:iana.cdx"}
  < Link: <http://www.iana.org/>; rel="original"
  < WARC-Target-URI: http://www.iana.org/
  < Warcserver-Source-Coll: pywb:iana.cdx
  < Content-Type: application/warc-record
  < Memento-Datetime: Sun, 26 Jan 2014 20:06:24 GMT
  < Content-Length: 6357
  < Warcserver-Type: warc
  < Date: Tue, 17 Oct 2017 00:32:12 GMT

  < WARC/1.0
  < WARC-Type: response
  < WARC-Date: 2014-01-26T20:06:24Z
  < WARC-Target-URI: http://www.iana.org/
  < WARC-Record-ID: <urn:uuid:4eec4942-a541-410a-99f4-50de39b62118>
  ...

The HTTP payload is the WARC record itself but HTTP headers returned "surface" additional information
about the WARC record to make it easier for client to use the data.

* Memento Headers ``Memento-Datetime`` and ``Link`` -- The datetime is read from the WARC record, and the WARC record it itself a valid "memento" although full Memento compliance is not yet included.

* ``Warcserver-Cdx`` header includes the full CDXJ index line that was used to load this record (usually, but not always, the first line in the ``index`` query)

* ``Warcserver-Source-Coll`` header includes the source from which this record was loaded, corresponding to ``source`` field in the CDXJ

* ``Warcserver-Type: warc`` indicates that this is a Warcserver WARC record (may be removed in the future)


In particular, the CDXJ and source data can be used to further identify and process the WARC record, without having to parse it.
The Recorder component uses the source to determine if recording is necessary or should be skipped.


.. _warcserver-config:

Warcserver Index Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Warcserver supports several index source types, allow users to mix local and remote sources into a single
collection or across multiple collections:

The sources include:

* Local File
 
* Local ZipNum File

* Live Web Proxy (implicit index)

* Redis sorted-set key

* Memento TimeGate Endpoint

* CDX Server API Endpoint


The index types can be defined using either shorthand *sourcename+<url>* notation or a long-form full property declaration

The following is an example of defining different special collections::

  collections:
      # Live Index
      live: $live

      # rhizome via memento (shorthand)
      rhiz: memento+http://webenact.rhizome.org/all/

      # rhizome via memento (equivalent full properties)
      rhiz_long:
          index:
              type: memento
              timegate_url: http://webenact.rhizome.org/all/{url}
              timemap_url: http://webenact.rhizome.org/all/timemap/link/{url}
              replay_url: http://webenact.rhizome.org/all/{timestamp}id_/{url}


Warcserver Index Aggregators
""""""""""""""""""""""""""""

In addition to individual index types, Warcserver supports 'index aggregators', which
represent not a single source but multiple index sources, explicit or implicit.

Some explicit aggregators are:

* Local Directory

* Redis Key Template (scan/lookup of multiple redis keys)

* A generic group of index sources looked up in parallel (best match)


The aggregators allow for a complex lookup chains to lookup of resources in dynamic directory structures,
using Redis keys, and external web archives.

Note: Warcserver automatically includes a Local Directory aggregator pointing to the ``collections`` directory, as
explained in the :ref:`configuring-pywb` 


Sample "Memento" Aggregator
"""""""""""""""""""""""""""

For example, the following config defines the collection endpoint ``many_archives`` to 
lookup three remote archives, two using memento, and one using CDX Server API::

  collections:
    # many archives
    many_archives:
      index_group:
        rhiz: memento+http://webenact.rhizome.org/all/
        ia:   cdx+http://web.archive.org/cdx;/web
        apt:  memento+http://arquivo.pt/wayback/

      timeout: 10

This allows Warcserver to serve as a "Memento Aggregator", aggregating results from
multiple existing archives (using the Memento API and other APIs).

An optional ``timeout`` property configures how many seconds to wait for each source before
it is considered to have 'timed out'. (If unspecified, the default value is 5 seconds).

Sequential Fallback Collections
"""""""""""""""""""""""""""""""

It is also possible to define a "sequential" collection, where if one source/aggregator
fails to produce a result, a "fallback" aggregator is tried, until there is a result::


  collections:

    # Sequence
    web:
        sequence:
            - 
              index: ./local/indexes
              resource: ./local/data
              name: local

            - 
              index_group:
                  rhiz: memento+http://webenact.rhizome.org/all/
                  ia:   cdx+http://web.archive.org/cdx;/web
                  apt:  memento+http://arquivo.pt/wayback/

            - 
              index: $live
              name: live

In the above example, first the local archive is tried, if the resource could not be successfully loaded,
then the group of 3 archives is tried, if they all fail to produce a successful response, the live web is tried.
Note that successful response includes a successful index lookup + successful resource fetch -- if an index
contains results, but they can not be fetched, the next group in the sequence is tried.

The ``name`` of each item is include in the CDXJ index in the ``source`` field to allow the caller to identify
which archive source was used.

Adding Custom Index Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^

It should be easy to add a custom index source, by extending :class:`pywb.warcserver.index.indexsource.BaseIndexSource` ::

  class MyIndexSource(BaseIndexSource):
     def load_index(self, params):
        ... lookup index data as needed to fill CDXObject
        cdx = CDXObject()
        cdx['url'] = ...
        ...
        yield cdx

    @classmethod
    def init_from_string(cls, value):
        if value == 'my-index-src':
            return cls()
        ...

    @classmethod
    def init_from_config(cls, config):
        if config['type'] != 'my-index-src':
            return
  
   # Register Index with Warcserver
   register_source(MyIndexSource)


You can then use the index in a ``config.yaml``::

  collections:
    my-coll: my-index-src

    
For more information and definition of existing indexes, see :mod:`pywb.warcserver.index.indexsource`

.. _custom-warcserver:

Custom Warcserver Deployments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is also possible to use Warcserver directly without the use of a ``config.yaml`` file, for more complex
deployment scenarios. (Webrecorder uses a customized deployment).

For example, the following ``config.yaml`` config::

  collections:
    live: $live

    memento:
      index_group:
        rhiz:  memento+http://webenact.rhizome.org/all/
        ia:    memento+http://web.archive.org/web/
        local: ./collections/


could be initialized explicitly, using the :class:`pywb.warcserver.basewarcserver.BaseWarcServer` class
which does not use a YAML config

.. code-block:: python

  app = BaseWarcServer()

  # /live endpoint
  live_agg = SimpleAggregator({'live': LiveIndexSource()})

  app.add_route('/live', DefaultResourceHandler(live_agg))


  # /memento endpoint
  sources = {'rhiz': MementoIndexSource.from_timegate_url('http://webenact.rhizome.org/vvork/'),
             'ia': MementoIndexSource.from_timegate_url('http://web.archive.org/web/'),
             'local': DirectoryIndexSource('./collections')
            }

  multi_agg = GeventTimeoutAggregator(sources)

  app.add_route('/memento', DefaultResourceHandler(multi_agg))


For more examples on custom Warcserver usage, consult the Warcserver tests, such as those in :mod:`pywb.warcserver.test.test_handlers.py`







