Using OutbackCDX with pywb
==========================

The recommended setup is to run `OutbackCDX <https://github.com/nla/outbackcdx>`_ alongside pywb.
OutbackCDX provides an index (CDX) server and can efficient store and lookup web archive data by URL.


Adding CDX to OutbackCDX
------------------------

To setup OutbackCDX, please follow the instructions on the `OutbackCDX README <https://github.com/nla/outbackcdx>`_

Since pywb also uses the default port 8080, be sure to use a different port for OutbackCDX, eg. ``java -jar outbackcdx*.jar -p 8084``.

To add indices to OutbackCDX, index the WARCs using ``cdx-indexer`` command-line tool and then POST to OutbackCDX.

For example, assuming OutbackCDX is running on port 8084:

.. code:: console

    cdx-indexer /path/to/mywarcs/my.warc.gz > ./index.cdx
    curl -X POST --data-binary @index.cdx http://localhost:8084/mycoll

The contents of the index are added to the ``mycoll`` index, which can correspond to the web archive collection ``mycoll``.
The index is created automatically if it does not exist.

The above can be repeated for each WARC file, or for the entire collection if small (by using a wildcard, eg. ``cdx-indexer /path/to/mywarcs/*.warc.gz > ./index.cdx``). If the CDX index is too big, OutbackCDX may fail and ingesting an index per-WARC is recommended.

See the `OutbackCDX Docs <https://github.com/nla/outbackcdx#loading-records>`_


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


