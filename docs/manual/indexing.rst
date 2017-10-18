Indexing
========

To provide access to the web archival data (local and remote), pywb uses indexes to represent each "capture" or "memento" in the archive. The WARC format itself does not provide a specific index, so an external index is needed.

Creating an Index
-----------------

When adding a WARC using ``wb-manager``, pywb automatically generates a :ref:`cdxj-index`

The index can also be created explicitly using ``cdx-indexer`` command line tool::

  cdx-indexer -j example2.warc.gz
  com,example)/ 20160225042329 {"offset":"363","status":"200","length":"1286","mime":"text/html","filename":"example2.warc.gz","url":"http://example.com/","digest":"37cf167c2672a4a64af901d9484e75eee0e2c98a"}
  
Note: the cdx-indexer tool is deprecated and will be replaced by the standalone `cdxj-indexer <https://github.com/webrecorder/cdxj-indexer>`_ package.


Index Formats
-------------

Classic CDX
^^^^^^^^^^^

Traditionally, an index for a web archive (WARC or ARC) file has been called a CDX file, probably from Capture/Crawl inDeX (CDX).

The CDX format originates with the Internet Archive and represents a plain-text space-delimited format, each line representing the information about a single capture. The CDX format could contain many different fields, and unfortunately, no standardized format existed.
The order of the fields typically includes a searchable url key and timestamp, to allow for binary sorting and search.
The 'url search key' is typically reversed and to allow for easier searching of subdomains, eg. ``example.com`` -> ``com,example,)/``

A classic CDX file might look like this::

  CDX N b a m s k r M S V g
  com,example)/ 20160225042329 http://example.com/ text/html 200 37cf167c2672a4a64af901d9484e75eee0e2c98a - - 1286 363 example2.warc.gz

A header is used to index the fields in the file, though typically a standard variation is used.

.. _cdxj-index:

CDXJ Format
^^^^^^^^^^^

The pywb system uses a more flexible version of the CDX, called CDXJ, which stores most of the fields in a JSON dictionary::

  com,example)/ 20160225042329 {"offset":"363","status":"200","length":"1286","mime":"text/html","filename":"example2.warc.gz","url":"http://example.com/","digest":"37cf167c2672a4a64af901d9484e75eee0e2c98a"}

The CDXJ format allows for more flexibility by allowing the index to contain a varying number of fields, while still allow the index to be sortable by a common key (url key + timestamp). This allows CDXJ indexes from different sources and different number of fields to be merged and sorted.

Using CDXJ indexes is recommended and pywb provides the ``wb-manager migrate-cdx`` tool for converting classic CDX to CDXJ.

In general, most discussions of CDX also apply to CDXJ indexes.

.. _zipnum:

ZipNum Sharded Index
^^^^^^^^^^^^^^^^^^^^

A CDX(J) file is generally accessed by doing a simple binary search through the file. This scales well to very large (GB+) CDXJ files. However, for very large archives (TB+ or PB+), binary search across a single file has its limits.

A more scalable alternative to a single CDX(J) file is gzip compressed chunked cluster of CDXJ, with a binary searchable index.
In this format, sometimes called the *ZipNum* or *Ziplines cluster* (for some X number of cdx lines zipped together), all actual CDXJ lines are gzipped compressed an concatenated together. To allow for random access, the lines are gzipped in groups of X lines (often 3000, but can be anything). This allows for the full index to be spread over N number of gzipped files, but has the overhead of requiring N lines to be read for each lookup. Generally, this overhead is negligible when looking up large indexes, and non-existent when doing a range query across many CDX lines.

The index can be split into an arbitrary number of shards, each containing a certain range of the url space. This allows the index to be created in parallel using MapReduce with a reduce task per shard. For each shard, there is an index file and a secondary index file. At the end, the secondary index is concatenated to form the final, binary searchable index.

The `webarchive-indexing <https://github.com/ikreymer/webarchive-indexing>`_ project provides tools for creating such an index, both locally and via MapReduce.

Single-Shard Index
""""""""""""""""""

A ZipNum index need not have multiple shards, and provides advantages even for smaller datasets. For example, in addition to less disk space from using compressed index, using the ZipNum index allows for the :ref:`pagination-api` to be available when using the cdx server for bulk querying.


