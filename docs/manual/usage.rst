Usage
=====


New Features
------------

The 2.0 release of :mod:`pywb` is a significant overhaul from the previous iteration,
and introduces many new features, including:

* Dynamic multi-collection configuration system with no-restart updates.

* New :ref:`recording-mode` capability to create new web archives from the live web or from other archives.

* Componentized architecture with standalone :ref:`warcserver`, :ref:`recorder` and :ref:`rewriter` components.

* Support for :ref:`memento-api` aggregation and fallback chains for querying multiple remote and local archival sources.

* :ref:`https-proxy` with customizable certificate authority for proxy mode recording and replay.

* Flexible rewriting system with pluggable rewriters for different content-types.

* Significantly improved client-side rewriting to handle most modern web sites.

* Improved 'calendar' query UI, grouping results by year and month, and updated replay banner.


Getting Started
---------------

At its core, pywb includes a fully featured web archive replay system, sometimes known as 'wayback machine', to provide the ability to replay, or view, archived web content in the browser.

If you have existing web archive (WARC or legacy ARC) files, here's how to make them accessible using :mod:`pywb`

(If not, see :ref:`creating-warc` for instructions on how to easily create a WARC file right away)

By default, pywb provides directory-based collections system to run your own web archive directly from archive collections on disk.

pywb ships with several :ref:`cli-apps`. The following two are useful to get started:

* :ref:`cli-wb-manager` is a command line tool for managing common collection operations.
* :ref:`cli-wayback` starts a web server that provides the access to web archives.

(For more details, run ``wb-manager -h`` and ``wayback -h``)

For example, to install pywb and create a new collection "my-web-archive" in ``./collections/my-web-archive``.

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

By default ``wb-manager``, places new collections in ``collections/<coll name>`` subdirectory in the current working directory. To specify a different root directory, the ``wb-manager -d <dir>``. Other options can be set in the config file.

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

After recording, you can click **Stop** and then click `Download Collection` to receive a WARC (`.warc.gz`) file.

You can then use this with work with pywb.


Using pywb Recorder
^^^^^^^^^^^^^^^^^^^

The core recording functionality in Webrecorder is also part of :mod:`pywb`. If you want to create a WARC locally, this can be
done by directly recording into your pywb collection:

1. Create a collection: ``wb-manager init my-web-archive`` (if you haven't already created a web archive collection)
2. Run: ``wayback --record --live -a --auto-interval 10``
3. Point your browser to ``http://localhost:8080/my-web-archive/record/<url>``

For example, to record ``http://example.com/``, visit ``http://localhost:8080/my-web-archive/record/<url>``

In this configuration, the indexing happens every 10 seconds.. After 10 seconds, the recorded url will be accessible for replay, eg:
``http://localhost:8080/my-web-archive/http://example.com/``


HTTP/S Proxy Mode Access
------------------------

It is also possible to access any pywb collection via HTTP/S proxy mode, providing possibly better replay
without client-side url rewriting.

At this time, a single collection for proxy mode access can be specified with the ``--proxy`` flag.

For example, ``wayback --proxy my-web-archive`` will start pywb and enable proxy mode access.

You can then configure a browser to Proxy Settings host port to: ``localhost:8080`` and then loading any url, eg. ``http://example.com/`` should
load the latest copy from the ``my-web-archive`` collection.

See :ref:`https-proxy` section for additional configuration details.


Deployment
----------

For testing, development and small production loads, the default ``wayback`` command line may be sufficient.
pywb uses the gevent coroutine library, and the default app will support many concurrent connections in a single process.

For larger scale production deployments, running with `uwsgi <http://uwsgi-docs.readthedocs.io/>`_ server application is recommended. The ``uwsgi.ini`` script provided can be used to launch pywb with uwsgi. uwsgi can be scaled to multiple processes to support the necessary workload, and pywb must be run with the `Gevent Loop Engine <http://uwsgi-docs.readthedocs.io/en/latest/Gevent.html>`_. Nginx or Apache can be used as an additional frontend for uwsgi.

Although uwsgi does not provide a way to specify command line, all command line options can alternatively be configured via ``config.yaml``. See :ref:`configuring-pywb` for more info on available configuration options.


Sample Nginx Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

The following nginx configuration snippet can be used to deploy pywb with uwsgi and nginx.

The configuration assumes pywb is running the uwsgi protocol on port 8081, as is the default
when running ``uwsgi uwsgi.ini``.

The ``location /static`` block allows nginx to serve static files, and is an optional optimization.

This configuration can be updated to use HTTPS and run on 443, the ``UWSGI_SCHEME`` param ensures that pywb will use the correct scheme
when rewriting.

See the `Nginx Docs <https://nginx.org/en/docs/>`_ for a lot more details on how to configure Nginx.


.. code:: nginx

    server {
        listen 80;

        location /static {
            alias /path/to/pywb/static;
        }

        location / {
            uwsgi_pass localhost:8081;

            include uwsgi_params;
            uwsgi_param UWSGI_SCHEME $scheme;
        }
    }

Sample Apache Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following Apache configuration snippet can be used to deploy pywb *without* uwsgi. A configuration with uwsgi is also probably possible but this covers the simplest case of launching the `wayback` binary directly.

The configuration assumes pywb is running on port 8080 on localhost, but it could be on a different machine as well.

.. code:: apache

    <VirtualHost *:80>
         ServerName proxy.example.com
         Redirect / https://proxy.example.com/
         DocumentRoot /var/www/html/
    </VirtualHost>

    <VirtualHost *:443>
         ServerName proxy.example.com
         SSLEngine on
         DocumentRoot /var/www/html/
         ErrorDocument 404 /404.html
         ProxyPreserveHost On
         ProxyPass /.well-known/ !
         ProxyPass / http://localhost:8080/
         ProxyPassReverse / http://localhost:8080/
         RequestHeader set "X-Forwarded-Proto" expr=%{REQUEST_SCHEME}
    </VirtualHost>
