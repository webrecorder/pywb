PyWb 0.33.2
===========

.. image:: https://travis-ci.org/ikreymer/pywb.svg?branch=master
      :target: https://travis-ci.org/ikreymer/pywb
.. image:: https://coveralls.io/repos/ikreymer/pywb/badge.svg?branch=master
      :target: https://coveralls.io/r/ikreymer/pywb?branch=master

**pywb** is a Python (2 and 3) implementation of web archival replay tools, sometimes also known as 'Wayback Machine'.

**pywb** allows high-quality replay (browsing) of archived web data stored in standardized `ARC <http://en.wikipedia.org/wiki/ARC_(file_format)>`_ and `WARC <http://en.wikipedia.org/wiki/Web_ARChive>`_,
and it can also serve as a customizable rewriting proxy to live web content.

The replay system is designed to accurately replay complex dynamic sites, including `video and audio content <https://github.com/ikreymer/pywb/wiki/Video-Replay-and-Recording>`_ and sites
with complex JavaScript.

Additionally, **pywb** includes an extensive `index query api <https://github.com/ikreymer/pywb/wiki/CDX-Server-API>`_ for querying information about archived content.

The software can run as a traditional web application or an HTTP or HTTPS proxy server, and has been tested on Linux, OS X and Windows platforms.

**pywb** is fully compliant with the `Memento <http://mementoweb.org/>`_ protocol (`RFC-7089 <http://tools.ietf.org/html/rfc7089>`_).

**pywb** supports Python 2.6+ and Python 3.3+


Getting Started -- Run your own Web Archive
-------------------------------------------

With release 0.9.0, **pywb** provides new simplified, directory-based init system to create and
run your own web archive replay system (wayback machine) directly from archive collections on disk.

A new utility, ``wb-manager`` performs the most common collection management tasks from the command line.


1. Archive a Web Page
"""""""""""""""""""""

If you do not have any web archive files (WARCS), you can create easily create one from any page by using the free
https://webrecorder.io/ service

For example, you may visit https://webrecorder.io/record/http://example.com, then (after a few seconds),
click *Download -> Web Archive (WARC)* to get the WARC file (.warc.gz)

Everything you have seen in your browser during the recording session was archived.


2. Create a new Collection
""""""""""""""""""""""""""

Each collections contains an arbitrary amount of WARC files.

Once you have at least one WARC/ARC file, you can set up a quick collection as follows, including installing
**pywb**:

::

      pip install pywb
      wb-manager init my_coll
      wb-manager add my_coll <path/to/warc>
      wayback


Point your browser to ``http://localhost:8080/my_coll/<url>/`` where ``<url>`` is a url you recorded before into your WARC/ARC file. (If you just recorded ``http://example.com/``, you should be able to view ``http://localhost:8080/my_coll/http://example.com/``)

If all worked well, you should see your archived version of ``<url>``. Congrats, you are now running your own web archive!


`A more detailed tutorial is available on the wiki <https://github.com/ikreymer/pywb/wiki/Auto-Configuration-and-Web-Archive-Collections-Manager>`_


Using Existing Web Archive Collections
--------------------------------------

Existing archives of WARCs/ARCs files can be used with pywb with minimal amount of setup. By using ``wb-manager add``,
WARC/ARC files will automatically be placed in the collection archive directory and indexed.

If you have a large number of existing CDX index files, pywb will be able to read them as well without having to reindex.
It is recommended that any index files be converted to the latest JSON based format, which can be done by running:
``wb-manager cdx-convert <path/to/cdx>``

To setup a collection with existing ARC/WARCs and CDX index files, you can:

1. Run ``wb-manager init <coll name>``. This will initialize all the required collection directories.
2. Copy any archive files (WARCs and ARCs) to ``collections/<coll name>/archive/``
3. Copy any existing cdx indexes to ``collections/<coll name>/indexes/``
4. Run ``wb-manager cdx-convert collections/<coll name>/indexes/``. This step is optional but strongly recommended, as it will
   ensure that the CDX indexes are in a consistent format.

This will fully migrate your archive and indexes the collection. Any new WARCs added with ``wb-manager add`` will be indexed and added to the existing collection.
You may use the auto-indexing features (explained below) to add new content to the existing collection.

`Legacy installation instructions <https://github.com/ikreymer/pywb/blob/master/INSTALL.rst>`_ contain additional
information and testing examples, and use a custom ``config.yaml`` file. These instructions are from previous releases but
still compatible with pywb 0.9.x.


Custom UI and User Metadata
---------------------------

**pywb** makes it easy to customize most aspects of the UI around archived content, including a custom banner insert, query calendar, search and home pages,
via HTML Jinja2 templates.

You can see a list of all available UI templates by running: ``wb-manager template --list``

To copy a default template to the file system (for modification), you can run ``wb-manager template --add <template_name> <collection>``

**pywb** now supports custom user metadata for each collection. The metadata may be specified in the ``metadata.yaml`` in each collection's directory.

The metadata is accessible to all UI templates and may be displayed to the user as needed.

See the `Collections Manager Tutorial <https://github.com/ikreymer/pywb/wiki/Auto-Configuration-and-Web-Archive-Collections-Manager>`_ and the
and `UI Customization <https://github.com/ikreymer/pywb/wiki/UI-Customization>`_ page for more details.


Automatic Indexing
------------------

**pywb** now also includes support for automatic indexing of any web archive files (WARC or ARC).

Whenever a WARC/ARC file is added or changed, pywb will update the internal index automatically and make the archived content
instantly available for replay, without manual intervention or restart. (Of course, indexing will take some time if adding
many gigabytes of data all at once, but is quite useful for smaller archive updates).

To enable auto-indexing, you can run the ``wayback -a`` when running command line, or run
``wb-manager autoindex <path/to/coll>`` as a seperate program.


Samples and Tests
-------------------------

To run with the bundled sample and test suite, you'll need to clone pywb locally:

1. ``git clone https://github.com/ikreymer/pywb.git; cd pywb``

2. ``python setup.py install``

3. ``wayback`` to run samples

4.  Browse to http://localhost:8080/pywb/\*/example.com to see capture of http://example.com

To run tests on your system, you may run ``python setup.py test``

(The HTTPS proxy tests require the optional ``certauth`` package and are skipped if the package is not installed)


Additional Samples and Other Projects
""""""""""""""""""""""""""""""""""""""

Additional (older) samples can be found in the `pywb-samples <https://github.com/ikreymer/pywb-samples>`_ repository.

For additional reference on how pywb is being used, you may check some of the `public projects using with pywb <https://github.com/ikreymer/pywb/wiki/Public-Projects-using-pywb>`_


Desktop Web Archive Player
--------------------------

There is now also a downloadable point-and-click `Web Archive Player <https://github.com/ikreymer/webarchiveplayer>`_ which provides
a native OS X and Windows desktop client application for browsing web archives, built using **pywb**.

You can use this tool to quickly check the contents of any WARC or ARC file through a simple point-and-click GUI interface, no command line tools needed.


pywb Tools Overview
-------------------

In addition to the standard Wayback Machine, **pywb** tool suite includes a
number of useful command-line and web server tools. The tools should be available to use after installing with
``pip install pywb``:


* ``wayback`` -- The Wayback Machine application itself.


*  ``wb-manager`` -- A command-line utility for managing collections, adding WARC/ARC files, metadata and UI templates.
   See ``wb-manager --help`` for an up-to-date listing of commands and options.


* ``live-rewrite-server`` -- a demo live rewriting web server which accepts requests using wayback machine url format at ``/live/`` path, eg, ``/live/http://example.com/`` and applies the same url rewriting rules as are used for archived content.
  This is useful for checking how live content will appear when archived before actually creating any archive files, or for recording data.
  The `webrecorder.io <https://webrecorder.io>`_ service extends upon this functionality.


* ``cdx-indexer`` -- a command-line tool for manually creating CDX indexes from WARC and ARC files. Supports SURT and
  non-SURT based cdx files, optional sorting, and several formats. See ``cdx-indexer -h`` for all options. Using ``wb-manager`` is recommended
  for higher-level collection file management, but this tool can be used for any custom indexing needs.


* ``cdx-server`` -- a CDX API only server which returns a responses about CDX captures in bulk. See `CDX Server API <https://github.com/ikreymer/pywb/wiki/CDX-Server-API>`_
  for an updated documentation on the latest query api.


Latest Changes
--------------

See `CHANGES.rst <https://github.com/ikreymer/pywb/blob/master/CHANGES.rst>`_ for an up-to-date changelist.


Running as Rewriting Live Web Proxy
-----------------------------------

In addition to replaying archived web content, pywb can serve as a rewriting proxy to the live web. This allows **pywb**
to serve live content, and inject customized code into any web page on the fly. This allow for a variety of use cases beyond archive replay.

For example, the `pywb-webrecorder <https://github.com/ikreymer/pywb-webrecorder>`_ demonstrates a way to use pywb live web rewriting
together with a recording proxy (warcprox) to record content while browsing.

The `via.hypothes.is <https://via.hypothes.is>`_ project provides an example of using pywb to inject annotations into any live web page.


Running in HTTP/HTTPS Proxy Mode
--------------------------------

**pywb** can also be used as an actual HTTP and/or HTTPS proxy server. See `pywb Proxy Mode Usage <https://github.com/ikreymer/pywb/wiki/Pywb-Proxy-Mode-Usage>`_ for more details
on configuring proxy mode.

To run as an HTTPS proxy server, pywb uses the `certauth <https://github.com/ikreymer/certauth>`_ tool for generating a custom self-signed root certificate, which can be used to replay HTTPS content from the archive. (The certificate should be used with caution within a controlled setting).

Using these features requiring an extra dependency: installing *certauth* with ``pip install certauth``. (This will also install the ``pyOpenSSL`` package which is used to handle the
ssl functionality).

Collection and Timestamp Selection In Proxy Mode
""""""""""""""""""""""""""""""""""""""""""""""""

When running in proxy mode, the current collection and current timestamp are not included in the page url and need to be set separeately. pywb provides several options for 'resolving' the collection and timestamp:

- *By Proxy Auth*: Proxy Authorization settings are used to select a (fixed) collection and Memento API can be used to pick the timestamp.
  
- *By IP*: Settings for current collection and timestamp can be set per-IP using a seperate HTTP request to the proxy. Useful for fixed-IP deployments, such as when running in Docker.
  
- *By Cookie*: The most complex but dynamic option, this allows a user to switch collection and current timestamp through cookies that are propagated across domains.
  
For more info, see `Proxy Mode Usage <https://github.com/ikreymer/pywb/wiki/Pywb-Proxy-Mode-Usage>`_.

The `pywb-proxy-demo <https://github.com/ikreymer/pywb-proxy-demo>`_ project also contains a working configuration of proxy mode deployment.


Running with any WSGI Container
-------------------------------

The command-line ``wayback`` utility starts pywb using the standard Python library `WSGIRef <https://docs.python.org/2/library/wsgiref.html>`_ server. This should be sufficient for basic usage and testing, but is not recommended for production. In the future, a different default option will be provided.

Since pywb conforms to the Python `WSGI <http://wsgi.readthedocs.org/en/latest/>`_ specification, it can be run with any standard WSGI container/server
and can be embedded in larger applications.

When running with a different container, specify ``pywb.apps.wayback`` as the WSGI application module.

For production deployments, `uWSGI <https://uwsgi-docs.readthedocs.org/en/latest/>`_ with gevent is the recommended container and the ``uwsgi.ini and ``run-uwsgi.sh`` 
scripts in this repo provides examples of running pywb with uWSGI.


Wayback Machine Compatibility
-----------------------------

**pywb** is compatible with the standard `Wayback Machine <http://en.wikipedia.org/wiki/Wayback_Machine>`_ url format, which was developed by the Internet Archive:

Replay: ``http://<host>/<collection>/<timestamp>/<original url>``

- ex: http://pywb.herokuapp.com/pywb/20140127171238/http://www.iana.org

- ex: http://web.archive.org/web/20150316213720/http://www.example.com/

Query Listing: ``http://<host>/<collection>/*/<original url>``

- ex: http://pywb.herokuapp.com/pywb/\*/http://iana.org/

- ex: http://web.archive.org/web/\*/http://www.example.com/


Additional Reference
--------------------

-  The `wiki <https://github.com/ikreymer/pywb/wiki>`_ will have
   additional technical documentation about various aspects of pywb

-  The sample ``config.yaml`` file, although not required, provides a listing of various advanced configuration options:
   `config.yaml <https://github.com/ikreymer/pywb/blob/master/config.yaml>`_


Contributions & Bug Reports
---------------------------

Users are encouraged to fork and contribute to this project to improve any and all aspects of web archival
replay and web proxy services.

Please take a look at list of current
`issues <https://github.com/ikreymer/pywb/issues?state=open>`_ and feel
free to open new ones.

