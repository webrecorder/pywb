.. _cli-apps:

Command-Line Apps
=================

After installing pywb tool-suite, the following command-line apps are made available (in the Python binary directory or current environment):

* :ref:`cli-cdx-indexer`

* :ref:`cli-wb-manager`

* :ref:`cli-warcserver`

* :ref:`cli-wayback`

* :ref:`cli-live-rewrite-server`


All server tools have a different default port, which can be override via the ``-p <port>`` command-line option.

.. _cli-cdx-indexer:

``cdx-indexer``
---------------

The CDX Indexer provides a way to create a CDX(J) file from a WARC/ARC. The tool supports both classic-CDX and new CDXJ formats.

The indexer also provides options for including all WARC records, and merging data from POST request (and other HTTP records).

See ``cdx-indexer -h`` for a list of options.

Note: In a future pywb release, this tool will be removed in favor of the standalone `cdxj-indexer <https://github.com/webrecorder/cdxj-indexer>`_ app, which will have
additional indexing options.


.. _cli-wb-manager:

``wb-manager``
--------------

The wb-manager command-line tool is used to to configure the ``collections`` directory structure and its contents, which pywb uses to automatically read collections.

The tool can be used while ``wayback`` is running, and pywb will detect many changes automatically.

It can be used to:

* Create a new collection --  ``wb-manager init <coll>``
* Add WARCs to collection -- ``wb-manager add <coll> <warc>``
* Unpack WACZs to add their WARCs and indices to collection -- ``wb-manager add --unpack-wacz <coll> <wacz>``
* Add override templates
* Add and remove metadata to a collections ``metadata.yaml``
* List all collections
* Reindex a collection
* Migrate old CDX to CDXJ style indexes.

For more details, run ``wb-manager -h``.


.. _cli-warcserver:

``warcserver``
--------------

The :ref:`warcserver` is a standalone server component that adheres to the :ref:`warcserver-api`.

The server runs on port ``8070`` by default serving both index and content.

The CDX Server is a subset of the Warcserver and queries using the :ref:`cdx-server-api` are included::

  http://localhost:8070/<coll>/index?url=http://example.com/

No rewriting or recording is performed by the Warcserver, but all collections from ``config.yaml`` are loaded.


.. _cli-wayback:

``wayback`` (``pywb``)
------------------------

The main pywb application is installed as the ``wayback`` application. (The ``pywb`` name is the same application, may become the primary name in future versions).

The app will start on port ``8080`` by default, and configuration is read from ``config.yaml``

See :ref:`configuring-pywb` for a detailed overview of configuration options and customizations.


.. _cli-live-rewrite-server:

``live-rewrite-server``
-----------------------

This cli is a shortcut for ``wayback``, but configured to run with only the :ref:`live-web`.

The live rewrite server runs on port ``8090`` and rewrites content from live web, useful for testing.

This app is almost equivalent to ``wayback --live``, except no other collections from ``config.yaml`` are used.
