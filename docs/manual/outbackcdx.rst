.. _using-outback:


Using OutbackCDX with pywb
==========================

The recommended setup is to run `OutbackCDX <https://github.com/nla/outbackcdx>`_ alongside pywb.
OutbackCDX provides an index (CDX) server and can efficiently store and look up web archive data by URL.


Adding CDX to OutbackCDX
------------------------

To set up OutbackCDX, please follow the instructions on the `OutbackCDX README <https://github.com/nla/outbackcdx>`_.

Since pywb also uses the default port 8080, be sure to use a different port for OutbackCDX, eg. ``java -jar outbackcdx*.jar -p 8084``.

OutbackCDX can generally ingest existing CDX used in OpenWayback simply by POSTing to OutbackCDX at a new index endpoint.

For example, assuming OutbackCDX is running on port 8084, to add CDX for ``index1.cdx``, ``index2.cdx``, run:

.. code:: console

    curl -X POST --data-binary @index1.cdx http://localhost:8084/mycoll
    curl -X POST --data-binary @index2.cdx http://localhost:8084/mycoll

The contents of each CDX file are added to the ``mycoll`` OutbackCDX index, which can correspond to the web archive collection ``mycoll``.
The index is created automatically if it does not exist.

See the `OutbackCDX Docs <https://github.com/nla/outbackcdx#loading-records>`_ for more info on ingesting CDX.


(Re)generating CDX from WARCs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are some exceptions where it may be useful to re-generate the CDX with pywb for existing WARCs:

- If your CDX is 9-field and does not include the compressed length, regnerating the CDX will result in more efficient HTTP range requests
- If you want to replay pages with POST requests, pywb generated CDX will soon be supported in OutbackCDX (see: `Issue #585 <https://github.com/webrecorder/pywb/issues/585>`_, `Issue #91 <https://github.com/nla/outbackcdx/pull/91>`_ )


To generate the CDX, run the ``cdx-indexer`` command (with ``-p`` flag for POST request handling) for each WARC or set of WARCs you wish to index:

.. code:: console

    cdx-indexer /path/to/mywarcs/my.warc.gz > ./index1.cdx
    cdx-indexer /path/to/all_warcs/*warc.gz > ./index2.cdx


Then, run the POST command as shown above to ingest to OutbackCDX.

The above can be repeated for each WARC file, or for a set of WARCs using the ``*.warc.gz`` wildcard.

If a CDX index is too big, OutbackCDX may fail and ingesting an index per-WARC may be needed.


Configure pywb with OutbackCDX
------------------------------

The ``config.yaml`` should be configured to point to OutbackCDX.

Assuming a collection named ``mycoll``, the ``config.yaml`` can be configured as follows to use OutbackCDX


.. code:: yaml

  collections:
    mycoll:
      index_paths: cdx+http://localhost:8084/mycoll
      archive_paths: /path/to/mywarcs/


The ``archive_paths`` can be configured to point to a directory of WARCs or a path index.

