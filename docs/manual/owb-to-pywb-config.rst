Converting OpenWayback Config to pywb Config
============================================

OpenWayback includes many different types of configurations.

For most use cases, using OutbackCDX with pywb is the recommended approach, as explained in :ref:`using-outback`.

The following are a few specific example of WaybackCollections gathered from active OpenWayback configurations
and how they can be configured for use with pywb.


Remote Collection / Access Point
--------------------------------

A collection configured with a remote index and WARC access can be converted to use OutbackCDX
for the remote index, while pywb can load WARCs directly from an HTTP endpoint.

For example, a configuration similar to:

.. code:: xml

    <bean name="standardaccesspoint" class="org.archive.wayback.webapp.AccessPoint">
      <property name="accessPointPath" value="/wayback/"/>
      <property name="collection" ref="remotecollection" /> 
      ...
    </bean>

    <bean id="remotecollection" class="org.archive.wayback.webapp.WaybackCollection">
      <property name="resourceStore">
        <bean class="org.archive.wayback.resourcestore.SimpleResourceStore">
          <property name="prefix" value="http://myarchive.example.com/RemoteStore/" />
        </bean>
      </property>
      <property name="resourceIndex">
        <bean class="org.archive.wayback.resourceindex.RemoteResourceIndex">
          <property name="searchUrlBase" value="http://myarchive.example.com/RemoteIndex" />
        </bean>
      </property>
    </bean>

can be converted to the following config, with OutbackCDX assumed to be running
at: ``http://myarchive.example.com/RemoteIndex``


.. code:: yaml

    collections:
        wayback:
            index_paths: cdx+http://myarchive.example.com/RemoteIndex
            archive_paths: http://myarchive.example.com/RemoteStore/

Local Collection / Access Point
-------------------------------

An OpenWayback configuration with a local collection and local CDX, for example:

.. code:: xml

     <bean id="collection" class="org.archive.wayback.webapp.WaybackCollection">
        <property name="resourceIndex">
          <bean class="org.archive.wayback.resourceindex.cdxserver.EmbeddedCDXServerIndex">
            ...
            <property name="cdxServer">
              <bean class="org.archive.cdxserver.CDXServer">
                <property name="cdxSource">
                  <bean class="org.archive.format.cdx.MultiCDXInputSource">
                    <property name="cdxUris">
                      <list>
                        <value>/wayback/cdx/mycdx1.cdx</value>
                        <value>/wayback/cdx/mycdx2.cdx</value>
                      </list>
                    </property>
                  </bean>
                </property>
                <property name="cdxFormat" value="cdx11"/>
                <property name="surtMode" value="true"/>
              </bean>
            </property>
            ...
          </bean>
        </property>
      </bean>


can be configured in pywb using the ``index_paths`` key.

Note that the CDX files should all be in the same format. See :ref:`migrating-cdx` for more info on converting
CDX to pywb native CDXJ format.


.. code:: yaml

    collections:
        wayback:
            index_paths: /wayback/cdx/
            archive_paths: ...


It's also possible to combine directories, individual CDX files, and even a remote index from OutbackCDX in a single collection
(as long as all CDX are in the same format).

pywb will query all the sources simultaneously to find the best match.

.. code:: yaml

    collections:
        wayback:
            index_group:
                cdx1: /wayback/cdx1/
                cdx2: /wayback/cdx2/mycdx.cdx
                remote: cdx+https://myarchive.example.com/outbackcdx

            archive_paths: ...

However, OutbackCDX is still recommended to avoid more complex CDX configurations.


WatchedCDXSource
^^^^^^^^^^^^^^^^

OpenWayback includes a 'Watched CDX Source' option which watches a directory for new CDX indexes.
This functionality is default in pywb when specifying a directory for the index path:

For example, the config:

.. code:: xml

     <property name="source">
       <bean class="org.archive.wayback.resourceindex.WatchedCDXSource">
         <property name="recursive" value="false" />
         <property name="filters">
           <list>
             <value>^.+\.cdx$</value>
           </list>
         </property>
         <property name="path" value="/wayback/cdx-index/" />
       </bean>
     </property>

can be replaced with:

.. code:: yaml

    collections:
        wayback:
            index_paths: /wayback/cdx-index/
            archive_paths: ...


pywb will load all CDX from that directory.


ZipNum Cluster Index
--------------------

pywb also supports using a compressed :ref:`zipnum` instead of a plain text CDX. For example, the following OpenWayback configuration:

.. code:: xml

    <bean id="collection" class="org.archive.wayback.webapp.WaybackCollection">
      <property name="resourceIndex">
        <bean class="org.archive.wayback.resourceindex.LocalResourceIndex">
          ...
          <property name="source">
            <bean class="org.archive.wayback.resourceindex.ZipNumClusterSearchResultSource">
              <property name="cluster">
                <bean class="org.archive.format.gzip.zipnum.ZipNumCluster">
                  <property name="summaryFile" value="/webarchive/zipnum-cdx/all.summary"></property>
                  <property name="locFile" value="/webarchive/zipnum-cdx/all.loc"></property>
                </bean>
              </property>
            ...
        </bean>
      </property>
    </bean>

can simply be converted to the pywb config:

.. code:: yaml

    collections:
      wayback:
        index_paths: /webarchive/zipnum-cdx

        # if the index is not surt ordered
        surt_ordered: false


pywb will automatically determine the ``.summary`` and use the ``.loc`` files for the ZipNum Cluster if they are present in the directory.

Note that if the ZipNum index is **not** SURT ordered, the ``surt_ordered: false`` flag must be added to support this format.



.. _path-index:

Path Index Configuration
------------------------

OpenWayback supports a 'path index' that can be used to look up a WARC by filename and map to an exact path.
For compatibility, pywb supports the same path index lookup, as well as loading WARC files by path or URL prefix.


For example, an OpenWayback configuration that includes a path index:

.. code:: xml

    <bean id="resourcefilelocationdb" class="org.archive.wayback.resourcestore.locationdb.FlatFileResourceFileLocationDB">
      <property name="path" value="/archive/warc-paths.txt"/>
    </bean>

    <bean id="resourceStore" class="org.archive.wayback.resourcestore.LocationDBResourceStore">
      <property name="db" ref="resourcefilelocationdb" />
    </bean>


can be configured in the ``archive_paths`` field of pywb collection configuration:

.. code:: yaml

    collections:
        wayback:
            index_paths: ...
            archive_paths: /archive/warc-paths.txt


The path index is a tab-delimited text file for mapping WARC filenames to full file paths or URLs, eg:

.. code::

    example.warc.gz<tab>/some/path/to/example.warc.gz
    another.warc.gz<tab>/some-other/path/another.warc.gz
    remote.warc.gz<tab>http://warcstore.example.com/serve/remote.warc.gz


However, if all WARC files are stored in the same directory, or in a few directories, a path index is not needed and pywb will try loading the WARC by prefix.

The ``archive_paths`` can accept a list of entries. For example, given the config:

.. code:: yaml

    collections:
        wayback:
            index_paths: ...
            archive_paths:
              - /archive/warcs1/
              - /archive/warcs2/
              - https://myarchive.example.com/warcs/
              - /archive/warc-paths.txt


And the WARC file: ``example.warc.gz``, pywb will try to find the WARC in order from:

.. code::

  1. /archive/warcs1/example.warc.gz
  2. /archive/warcs2/example.warc.gz
  3. https://myarchive.example.com/warcs/example.warc.gz
  4. Looking up example.warc.gz in /archive/warc-paths.txt


.. _lmdb-path-index:

LMDB Path Index
^^^^^^^^^^^^^^^

Each lookup in a path index file is a binary search in the file. For large path indexes, with millions of WARC files,
pywb can instead look up the WARC filenames in an `LMDB <http://www.lmdb.tech/doc/>`_ database, loaded from the same path index files.
It requires the optional `lmdb <https://pypi.org/project/lmdb/>`_ package (``pip install lmdb``, or ``pip install pywb[lmdb]``).

The database is configured in ``archive_paths`` as ``lmdb:///path/to/env?db=name``, the LMDB environment directory and the name of a database in it:

.. code:: yaml

    collections:
        wayback:
            index_paths: ...
            archive_paths:
              - lmdb:///archive/pathindex.lmdb?db=primary
              - lmdb:///archive/pathindex.lmdb?db=mirror


The ``lmdb-pathindex`` command loads path index files into a database, creating the environment if needed:

.. code:: bash

    # load or update a path index into the "primary" database
    lmdb-pathindex load --env /archive/pathindex.lmdb --db primary /archive/warc-paths.txt

    # only show what would change: added, updated, unchanged and dropped entries
    lmdb-pathindex load --dry-run --env /archive/pathindex.lmdb --db primary /archive/warc-paths.txt

    # recreate the "mirror" database from all the .txt files of a directory
    lmdb-pathindex load --drop --pattern '.*\.txt' --env /archive/pathindex.lmdb --db mirror /archive/mirror-paths/

    # the number of entries of each database
    lmdb-pathindex stats --env /archive/pathindex.lmdb


* The key is the WARC filename, the value its paths or URLs, tab-separated. The lines are parsed like the path index file: the paths of consecutive lines
  of the same WARC file are joined, and are tried in order. The path index files must be sorted, like for the path index lookup; ``load`` counts the unsorted lines.

* An environment can have several named databases (up to 64), eg. one per path index. Each one is an independent ``archive_paths`` entry, tried in order.
  A missing environment or database is logged and skipped, and opened again after 60 seconds.

* Loading adds the new WARC files and replaces the paths of the existing ones, keeping the other WARC files of the database.
  ``--drop`` empties the database first. Each run is a single write transaction: pywb keeps reading the previous version of the database
  until the load is committed, also with ``--drop``, and a failed load does not change it. The other databases of the environment are not changed.

* pywb opens the environment read-only, on the first lookup of each process (eg. each uWSGI worker), as LMDB can't be used across ``fork()``.
  It still needs write access to the ``lock.mdb`` file, where LMDB keeps track of its readers.

* ``--map-size`` (default: 64 GiB) is the maximum size of the environment. It only reserves address space, the file grows with the data.
  As LMDB keeps the previous version of the pages while they can be read, reloading a whole database can make the file grow up to about 3 times
  the size of the data, then the free pages are reused. ``mdb_copy -c`` writes a compacted copy.

On a benchmark with a path index of 14.6 million WARC files (2.3 GiB, plus a second path index of the same size as the next ``archive_paths`` entry),
with the files in the page cache, an LMDB lookup took 4 to 10 µs (median), 40 to 85 times faster than the path index file (172 to 798 µs),
and 8 to 21 times faster than the same paths in a Redis hash with ``RedisResolver`` (44 to 203 µs), with 1 to 16 worker processes.
With 16 workers, LMDB made 680,000 lookups/s, Redis 72,000 and the path index file 12,000.
Right after dropping the page cache, LMDB reads its pages from disk on the first lookups, and was slower than Redis with a single worker (99 µs against 63 µs),
but only 0.1 GiB of it was read into the page cache, against 2.5 GiB of the path index files.
Both path indexes took 5.2 GiB in LMDB, 15% more than the files (4.5 GiB), while Redis kept 6.1 GiB in memory.
Loading each path index took 19 to 24 s, against 125 s for Redis.


Proxy Mode Access
-----------------

A OpenWayback configuration may include many beans to support proxy mode, eg:

.. code:: xml

      <bean id="proxyreplaydispatcher" class="org.archive.wayback.replay.SelectorReplayDispatcher">
        ...
           <property name="renderer">
                <bean class="org.archive.wayback.proxy.HttpsRedirectAndLinksRewriteProxyHTMLMarkupReplayRenderer">
                  ...
                    <property name="uriConverter">
                        <bean class="org.archive.wayback.proxy.ProxyHttpsResultURIConverter"/>
                    </property>
                </bean>
            </propery>
      </bean>
      <bean name="proxy" class="org.archive.wayback.webapp.AccessPoint">
        <property name="internalPort" value="${proxy.port}"/>
        <property name="accessPointPath" value="${proxy.port}" />
        <property name="collection" ref="localcdxcollection" />
         ...
      </bean>


In pywb, the proxy mode can be enabled by adding to the main ``config.yaml`` the name of the collection
that should be served in proxy mode:

.. code:: yaml

      proxy:
        source_coll: wayback


There are some differences between OpenWayback and pywb proxy mode support.

In OpenWayback, proxy mode is configured using separate access points for different collections on different ports.
OpenWayback only supports HTTP proxy and attempts to rewrite HTTPS URLs to HTTP.

In pywb, proxy mode is enabled on the same port as regular access, and pywb supports HTTP and HTTPS proxy.
pywb does not attempt to rewrite HTTPS to HTTP, as most browsers disallow HTTP access as insecure for many sites.
pywb supports a default collection that is enabled for proxy mode, and a default timestamp accessed by the proxy mode.
(Switching the collection and date accessed is possible but not currently supported without extensions to pywb).

To support HTTPS access, pywb provides a certificate authority that can be trusted by a browser to rewrite HTTPS content.

See :ref:`https-proxy` for all of the options of pywb proxy mode configuration.

