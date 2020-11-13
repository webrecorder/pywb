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

