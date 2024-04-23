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

* Significantly improved :ref:`wombat` to handle most modern web sites.

* Improved 'calendar' query UI with incremental loading, grouping results by year and month, and updated replay banner.

* New in 2.4: Extensible :ref:`ui-customizations` for modifying all aspects of the UI.

* New in 2.4: Robust :ref:`access-control` system for blocking or excluding URLs, by prefix or by exact match.


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


.. _getting-started-docker:

Getting Started Using Docker
----------------------------

pywb also comes with an official production-ready Dockerfile, and several automatically built Docker images.

The following Docker image tags are updated automatically with pywb updates on github:

* ``webrecorder/pywb`` corresponds to the latest release of pywb and the ``master`` branch on github.
* ``webrecorder/pywb:develop`` -- corresponds to the ``develop`` branch of pywb on github and contains the latest development work.
* ``webrecorder/pywb:<VERSION>`` -- Starting with pywb 2.2, each incremental release will correspond to a Docker image with tag ``<VERSION>``

Using a specific version, eg. ``webrecorder/pywb:<VERSION>`` release is recommended for production. Versioned Docker images are available for pywb releases >= 2.2.

All releases of pywb are listed in the `Python Package Index for pywb <https://pypi.org/project/pywb/#history>`_

All of the currently available Docker image tags are `listed on Docker hub <https://hub.docker.com/r/webrecorder/pywb/tags>`_

For the below examples, the latest ``webrecorder/pywb`` image is used.

To add WARCs in Docker, the source directory should be added as a volume.

By default, pywb runs out of the ``/webarchive`` directory, which should generally be mounted as a volume to store the data on the host
outside the container. pywb will not change permissions of the data mounted at ``/webarchive`` and will instead attempt to run as same user
that owns the directory.

For example, give a WARC at ``/path/to/my_warc.warc.gz`` and a pywb data directory of ``/pywb-data``, the following will
add the WARC to a new collection and start pywb:

.. code:: console

      docker pull webrecorder/pywb
      docker run -e INIT_COLLECTION=my-web-archive -v /pywb-data:/webarchive \
         -v /path/to:/source webrecorder/pywb wb-manager add my-web-archive /source/my_warc.warc.gz
      docker run -p 8080:8080 -v /pywb-data/:/webarchive webrecorder/pywb wayback

This example is equivalent to the non-Docker example above.

Setting ``INIT_COLLECTION=my-web-archive`` results in automatic collection initializiation via ``wb-manager init my-web-archive``.

The ``wayback`` command is launched on port 8080 and mapped to the same on the local host.

If the ``wayback`` command is not specified, the Docker container launches with the ``uwsgi`` server recommended for production deployment.
See :ref:`deployment` for more info.


Using Existing Web Archive Collections
--------------------------------------

Existing archives of WARCs/ARCs files can be used with pywb with minimal amount of setup. By using ``wb-manager add``,
WARC/ARC files will automatically be placed in the collection archive directory and indexed.

In pywb 2.8.0 and later, preliminary support for WACZ files is also added with ``wb-manager add --unpack-wacz``. This will unpack the provided WACZ file, adding its WARCs and indices to the collection.

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

Using ArchiveWeb.page
^^^^^^^^^^^^^^^^^^^^^

If you do not have a web archive to test, one easy way to create one is to use the `ArchiveWeb.page <https://archiveweb.page>`_ browser extension for Chrome and other Chromium-based browsers such as Brave Browser. ArchiveWeb.page records pages visited during an archiving session in the browser, and provides means of both replaying and downloading the archived items created.

Follow the instructions in `How To Create Web Archives with ArchiveWeb.page <https://archiveweb.page/en/usage/>`_. After recording, press **Stop** and then `download your collection <https://archiveweb.page/en/download/>`_ to receive a WARC (`.warc.gz`) file. If you choose to download your collection in the WACZ format, the WARC files can be found inside the zipped WACZ in the ``archive/`` directory.

You can then use your WARCs to work with pywb.


Using pywb Recorder
^^^^^^^^^^^^^^^^^^^

Recording functionality is also part of :mod:`pywb`. If you want to create a WARC locally, this can be
done by directly recording into your pywb collection:

1. Create a collection: ``wb-manager init my-web-archive`` (if you haven't already created a web archive collection)
2. Run: ``wayback --record --live -a --auto-interval 10``
3. Point your browser to ``http://localhost:8080/my-web-archive/record/<url>``

For example, to record ``http://example.com/``, visit ``http://localhost:8080/my-web-archive/record/http://example.com/``

In this configuration, the indexing happens every 10 seconds.. After 10 seconds, the recorded url will be accessible for replay, eg:
``http://localhost:8080/my-web-archive/http://example.com/``


Using Browsertrix
^^^^^^^^^^^^^^^^^

For a more automated browser-based web archiving experience, `Browsertrix <https://browsertrix.com/>`_ provides a web interface for configuring, scheduling, running, reviewing, and curating crawls of web content. Crawl activity is shown in a live screencast of the browsers used for crawling and all web archives created in Browsertrix can be easily downloaded from the application in the WACZ format.

`Browsertrix Crawler <https://crawler.docs.browsertrix.com/>`_, which provides the underlying crawling functionality of Browsertrix, can also be run standalone in a Docker container on your local computer.


HTTP/S Proxy Mode Access
------------------------

It is also possible to access any pywb collection via HTTP/S proxy mode, providing possibly better replay
without client-side url rewriting.

At this time, a single collection for proxy mode access can be specified with the ``--proxy`` flag.

For example, ``wayback --proxy my-web-archive`` will start pywb and enable proxy mode access.

You can then configure a browser to Proxy Settings host port to: ``localhost:8080`` and then loading any url, eg. ``http://example.com/`` should
load the latest copy from the ``my-web-archive`` collection.

See :ref:`https-proxy` section for additional configuration details.


.. _deployment:

Deployment
----------

For testing, development and small production loads, the default ``wayback`` command line may be sufficient.
pywb uses the gevent coroutine library, and the default app will support many concurrent connections in a single process.

For larger scale production deployments, running with `uwsgi <http://uwsgi-docs.readthedocs.io/>`_ server application is recommended. The ``uwsgi.ini`` script provided can be used to launch pywb with uwsgi. uwsgi can be scaled to multiple processes to support the necessary workload, and pywb must be run with the `Gevent Loop Engine <http://uwsgi-docs.readthedocs.io/en/latest/Gevent.html>`_. Nginx or Apache can be used as an additional frontend for uwsgi.

It is recommended to install uwsgi and its dependencies in a Python virtual environment (virtualenv). Consult the uwsgi documentation for `virtualenv support <https://uwsgi-docs.readthedocs.io/en/latest/Python.html#virtualenv-support>`_ for details on how to specify the virtualenv to uwsgi.

Installation of uswgi in a virtualenv will avoid known issues with installing uwsgi in some Debian-based OSes with Python 3.9+. As an example, in Ubuntu 22.04 with Python 3.10, it is recommended to install uwsgi like so: ::

    sudo apt install -y python3-pip \
        python3-dev \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-setuptools \
        python3-venv
    python3 -m venv pywbenv
    source pywbenv/bin/activate
    pip install wheel uwsgi pywb

Although uwsgi does not provide a way to specify command line, all command line options can alternatively be configured via ``config.yaml``. See :ref:`configuring-pywb` for more info on available configuration options.

Docker Deployment
^^^^^^^^^^^^^^^^^

The default pywb Docker image uses the production ready ``uwsgi`` server by default.

The following will run pywb in Docker directly on port 80:


.. code:: console

      docker run -p 80:8080 -v /webarchive-data/:/webarchive webrecorder/pywb

To run pywb in Docker behind a local nginx (as shown below), port 8081 should also be mapped:

.. code:: console

      docker run -p 8081:8081 -v /webarchive-data/:/webarchive webrecorder/pywb


See :ref:`getting-started-docker` for more info on using pywb with Docker.


.. _nginx-deploy:

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


.. _apache-deploy:

Sample Apache Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The recommended Apache configuration is to use pywb with ``mod_proxy`` and ``mod_proxy_uwsgi``.

To enable these, ensure that your httpd.conf includes:

.. code:: apache

  LoadModule proxy_module modules/mod_proxy.so
  LoadModule proxy_uwsgi_module modules/mod_proxy_uwsgi.so



Then, in your config, simply include:

.. code:: apache

    <VirtualHost *:80>
      ProxyPass / uwsgi://pywb:8081/
    </VirtualHost>

The configuration assumes uwsgi is started with ``uwsgi uwsgi.ini``


.. _config-acl-header:

Configuring Access Control Header
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :ref:`access-control` system allows users to be granted different access settings based on the value of an ACL header, ``X-pywb-ACL-user``.

The header can be set via Nginx or Apache to grant custom access priviliges based on IP address, password, or other combination of rules.

For example, to set the value of the header to ``staff`` if the IP of the request is from designated local IP ranges (127.0.0.1, 192.168.1.0/24), the following settings can be added to the configs:

For Nginx::

  geo $acl_user {
    # ensure user is set to empty by default
    default           "";

    # optional: add IP ranges to allow privileged access
    127.0.0.1         "staff";
    192.168.0.0/24    "staff";
  }

  ...
  location /wayback/ {
    ...
    uwsgi_param HTTP_X_PYWB_ACL_USER $acl_user;
  }


For Apache::

    <If "-R '192.168.1.0/24' || -R '127.0.0.1'">
      RequestHeader set X-Pywb-ACL-User staff
    </If>
    # ensure header is cleared if no match
    <Else>
      RequestHeader set X-Pywb-ACL-User ""
    </Else>

}




Running on Subdirectory Path
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run pywb on a subdirectory, rather than at the root of the web server, the recommended configuration is to adjust the ``uwsgi.ini`` to include the subdirectory:
For example, to deploy pywb under the ``/wayback`` subdirectory, the ``uwsgi.ini`` can be configured as follows:

.. code:: ini

    mount = /wayback=./pywb/apps/wayback.py
    manage-script-name = true


.. _example-deploy:

Deployment Examples
^^^^^^^^^^^^^^^^^^^

The ``sample-deploy`` directory includes working Docker Compose examples for deploying pywb with Nginx and Apache on the ``/wayback`` subdirectory.

See:
 - `Docker Compose Nginx <https://github.com/webrecorder/pywb/blob/main/sample-deploy/docker-compose-nginx.yaml>`_ for sample Nginx config.
 - `Docker Compose Apache <https://github.com/webrecorder/pywb/blob/main/sample-deploy/docker-compose-apache.yaml>`_ for sample Apache config.
 - `uwsgi_subdir.ini <https://github.com/webrecorder/pywb/blob/main/sample-deploy/uwsgi_subdir.ini>`_ for example subdirectory uwsgi config.

