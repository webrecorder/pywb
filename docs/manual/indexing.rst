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

Faster Decompression
""""""""""""""""""""

Each ZipNum lookup decompresses at least two gzip blocks: the block found by the binary search, and the block before it, as the url may start there. With large blocks (for example 3000 lines of about 350 bytes, about 1 MB uncompressed), this is a large part of the cost of a lookup.

If the optional `isal <https://pypi.org/project/isal/>`_ package is installed, pywb uses it instead of ``zlib`` to decompress the ZipNum blocks. It is about 2.5 times faster, and no configuration is needed::

    pip install isal

It is included in the pywb Docker image. Smaller blocks (fewer lines per block when creating the index) also make each lookup decompress less data, at the cost of a larger secondary index.

.. _zipnum-lmdb:

LMDB Secondary Index
""""""""""""""""""""

Each ZipNum lookup does a binary search over the secondary index (``.idx``) file to find the blocks to read. pywb can instead read the ``.idx`` from an `LMDB <http://www.lmdb.tech/doc/>`_ database, loaded from the ``.idx`` file. It needs the optional ``lmdb`` package::

    pip install lmdb

It is included in the pywb Docker image.

The database is added with the ``lmdb`` option of a ``zipnum`` index, as ``lmdb:///path/to/environment?db=name``::

    collections:
      my-coll:
        index:
          type: zipnum
          path: /data/indexes/my-coll.idx
          lmdb: lmdb:///data/indexes/idx.lmdb?db=my-coll

* ``path`` is still needed: the ``.loc`` file next to it locates the shards, and the ``.idx`` file is used when the database isn't available.
* An LMDB environment (a directory with ``data.mdb`` and ``lock.mdb``) can have a named database for each ZipNum index.
* Use an environment only for ZipNum indexes, not the one of an LMDB path index: LMDB can't open the same environment twice in a process.
* Each concurrent lookup (eg. of each uWSGI worker or gevent greenlet) uses an LMDB reader slot, and an environment has 126 by default. A lookup that finds no free slot fails like any other lookup, so that process uses the ``.idx`` file until the retry.
* The environment is opened read only on the first lookup of each process, eg. of each uWSGI worker. pywb needs write access to its ``lock.mdb``.
* If the environment or the database is missing, or a lookup fails, a warning is logged and the ``.idx`` file is used. The database is tried again after 60 seconds.

The ``lmdb-zipnum-idx`` command loads an ``.idx`` file into a named database, creating the environment if needed::

    # load the .idx of a ZipNum index into a new database
    lmdb-zipnum-idx load --env /data/indexes/idx.lmdb --db my-coll /data/indexes/my-coll.idx

    # replace it, after the ZipNum index is rebuilt
    lmdb-zipnum-idx load --drop --env /data/indexes/idx.lmdb --db my-coll /data/indexes/my-coll.idx

    # validate the .idx and show what would change, without writing
    lmdb-zipnum-idx load --dry-run --drop --env /data/indexes/idx.lmdb --db my-coll /data/indexes/my-coll.idx

    # number of entries of each database
    lmdb-zipnum-idx stats --env /data/indexes/idx.lmdb

* The database has the offsets of the blocks in the shards, so it must be loaded from the ``.idx`` of the same shards. When the ZipNum index is rebuilt, reload it with ``--drop``: a database that has entries is only replaced as a whole.
* Each load is a single write transaction: pywb keeps reading the previous version until it is committed, and a failed load changes nothing.
* The ``.idx`` is validated before it is committed: each line must have the ``urlkey timestamp``, part, offset, length and line number fields separated by tabs, the line number must be the 1-based number of the line, and the lines must be sorted by their first field.
* ``--map-size`` is the maximum size of the environment, in GiB (default: 64). Only the used pages take disk space. Repeated ``--drop`` loads can grow ``data.mdb`` up to about 3 times the size of the database, then its free pages are reused; ``mdb_copy -c`` writes a compacted copy.

Each ``.idx`` line is an LMDB entry. The key is the first field of the line (``urlkey timestamp``), cut to its first 500 bytes as LMDB keys have at most 511, then a tab and the 8 byte big-endian line number, which keeps the order of the file and makes the keys of consecutive blocks with the same first field unique. The value is the rest of the line. LMDB sorts the keys bytewise, like the ``.idx`` file, so a lookup positions a cursor on the first line ``>=`` the query key and also reads the line before it, like the binary search. The pages, the blocks and the results are the same as with the ``.idx`` file.

**When to use it.** In our tests, the LMDB secondary index is only beneficial for block sizes smaller than 3000 lines:

* LMDB lookups are faster at any size, and barely grow with the size of the ``.idx``, while the lookups in the ``.idx`` file do. On a 10.6 GiB ``.idx``, an ``.idx`` file lookup took 95 to 388 µs (median, warm page cache, 1 to 16 worker processes), and an LMDB lookup 17 to 61 µs.
* With 3000 lines per block, the ``.idx`` lookup is 0.1 to 0.5% of the time of a query: decompressing and parsing the blocks takes the rest, and LMDB makes no measurable difference.
* With 500 lines per block, the ``.idx`` is 6 times bigger and its lookup is about 15 to 20% of the time of an exact url query, which LMDB makes 5 to 6 times faster.
* The database is 1.24 to 1.28 times the size of the ``.idx`` file, and a 10 GiB ``.idx`` loads in about a minute.

The benchmark and the full results are in `arquivo/pywb-arquivo#53 <https://github.com/arquivo/pywb-arquivo/pull/53>`_, for `arquivo/pwa-technologies#1675 <https://github.com/arquivo/pwa-technologies/issues/1675>`_.


