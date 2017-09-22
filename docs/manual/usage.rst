Usage
=====


Getting Started
---------------

At its core, pywb includes a fully featured web archive replay system, sometimes known as 'wayback machine', to provide the ability to replay,
or view, archived web content in the browser.

If you have existing web archive (WARC or legacy ARC) files, here's how to make them accessible using :mod:`pywb`

(If not, see :ref:`creating-warc` for instructions on how to easily create a WARC file right away)

By default, pywb provides directory-based collections system to run your own web archive directly from archive collections on disk.

Two command line utilities are provided:

* ``wb-manager`` is a command line tool for managing common collection operations.
* ``wayback`` starts a web server that provides the access to web archives.

(For more details, run ``wb-manager -h`` and ``wayback -h``)

For example, to install pywb and create a new collection ``my-web-archive``

.. code:: console

      pip install pywb
      wb-manager init my-web-archive
      wb-manager add my-web-archive <path/to/my_warc.warc.gz>
      wayback

Point your browser to ``http://localhost:8080/my-web-archive/<url>/`` where ``<url>`` is a url you recorded before into your WARC/ARC file. 

If all worked well, you should see your archived version of ``<url>``. Congrats, you are now running your own web archive!



Using Existing Web Archive Collections
--------------------------------------

Existing archives of WARCs/ARCs files can be used with pywb with minimal amount of setup. By using ``wb-manager add``,
WARC/ARC files will automatically be placed in the collection archive directory and indexed.

If you have a large number of existing CDX index files, pywb will be able to read them as well after running through a simple conversion process.

It is recommended that any index files be converted to the latest CDXJ format, which can be done by running:
``wb-manager cdx-convert <path/to/cdx>``

To setup a collection with existing ARC/WARCs and CDX index files, you can:

1. Run ``wb-manager init <coll name>``. This will initialize all the required collection directories.
2. Copy any archive files (WARCs and ARCs) to ``collections/<coll name>/archive/``
3. Copy any existing cdx indexes to ``collections/<coll name>/indexes/``
4. Run ``wb-manager cdx-convert collections/<coll name>/indexes/``. This strongly recommended, as it will
   ensure that any legacy indexes are updated to the latest CDXJ format.

This will fully migrate your archive and indexes the collection.
Any new WARCs added with ``wb-manager add`` will be indexed and added to the existing collection.


Dynamic Collections and Automatic Indexing
------------------------------------------

Collections created via ``wb-manager init`` are fully dynamic, and new collections can be added without restarting pywb.

When adding WARCs with ``wb-manager add``, the indexes are also updated automatically. No restart is required, and the
content is instantly available for replay.

For more complex use cases, mod:`pywb` also includes a background indexer that checks the archives directory and automatically
updates the indexes, if any files have changed or were added. 

(Of course, indexing will take some time if adding a large amount of data all at once, but is quite useful for smaller archive updates).

To enable auto-indexing, run with ``wayback -a`` or ``wayback -a --auto-interval 30`` to adjust the frequency of auto-indexing (default is 30 seconds).


.. _creating-warc:

Creating a Web Archive
----------------------

Using Webrecorder
^^^^^^^^^^^^^^^^^

If you do not have a web archive to test, one easy way to create one is to use `Webrecorder <https://webrecorder.io>`_

After recording, you can click ``Stop`` and then click `Download Collection` to receive a WARC (`.warc.gz`) file.

You can then use this with work with pywb.


Using pywb Recorder
^^^^^^^^^^^^^^^^^^^

The core recording functinality in Webrecorder ia also part of :mod:`pywb`. If you want to create a WARC locally, this can be
done by directly recording into your pywb collection:

1. Edit ``config.yaml`` to add ``recorder: live``
2. Create a collection: ``wb-manager init my-web-archive`` (if you haven't already created a web archive collection)
3. Run: ``wayback --live -a --auto-interval 10``
4. Point your browser to ``http://localhost:8080/my-web-archive/record/<url>``

For example, to record ``http://example.com/``, visit ``http://localhost:8080/my-web-archive/record/<url>``

In this configuration, the indexing happens every 10 seconds.. After 10 seconds, the recorded url will be accessible for replay, eg:
``http://localhost:8080/my-web-archive/http://example.com/``

(Note: this recorder is still experimental)


