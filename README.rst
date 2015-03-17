PyWb 0.9.0 Beta
===============

.. image:: https://travis-ci.org/ikreymer/pywb.svg?branch=0.9.0b
      :target: https://travis-ci.org/ikreymer/pywb
.. image:: https://coveralls.io/repos/ikreymer/pywb/badge.svg?branch=0.9.0b
      :target: https://coveralls.io/r/ikreymer/pywb?branch=0.9.0b
.. image:: https://img.shields.io/gratipay/ikreymer.svg
      :target: https://www.gratipay.com/ikreymer/

pywb is a python implementation of web archival replay tools, sometimes also known as 'Wayback Machine'.

pywb allows high-quality replay (browsing) of archived web data stored in standardized `ARC <http://en.wikipedia.org/wiki/ARC_(file_format)>`_ and `WARC <http://en.wikipedia.org/wiki/Web_ARChive>`_.

The replay system is designed to accurately replay complex dynamic sites, including ``video and audio content <https://github.com/ikreymer/pywb/wiki/Video-Replay-and-Recording>``_ and sites
with complex JavaScript.

The software can run as a traditional web application or an HTTP or HTTPS proxy server, and has been tested on Linux, OS X and Windows platforms.

pywb is also fully compliant with the `Memento <http://mementoweb.org/>`_ protocol (`RFC-7089 <http://tools.ietf.org/html/rfc7089>`_).


Getting Started -- Run your own Wayback Machine
-----------------------------------------------

With release 0.9.0, pywb provides new simplified, directory-based init system to create and
run your own Wayback Machine directly from archive collections on disk.

A new utility, ``wayback-manager`` performs the most common collection management tasks from the command line.

0. Ensure that Python 2.6 or 2.7 is installed on your machine (Python 2.7.3+ strongly recommended).
   
1. (Optional) For best results, setup a clean environment with virtualenv: ``virtualenv /tmp/pywb-env; source /tmp/pywb-env/bin/activate``

2. ``pip install pywb==0.9.0b1``

3. Create a new directory for your archive, eg: ``mkdir ~/myarchive; cd ~/myarchive``

4. Init a collection: ``wayback-manager init my_coll``

5. (Optional) If you do not have any archive files, (WARCs or ARCs), you may create one by using the free
   https://webrecorder.io service. For example, you may visit https://webrecorder.io/record/http://example.com, then (after a few seconds)
   click "Download -> Web Archive (WARC)" to get the WARC file (.warc.gz)
   
6. If you have any existing archive files (WARCs or ARCs), add them to your collection with: ``wayback-manager add /path/to/mywarc.warc.gz``

7. Run ``wayback``

8. Point your browser to ``http://localhost:8080/my_coll/<url>/`` where ``<url>`` is a url in your WARC file. 

   (If you just recorded ``http://example.com/``, you should be able to view ``http://localhost:8080/my_coll/http://example.com/``)

9. If all worked well, you should see replay of ``<url>``.

Congrats, you are now running your own Wayback Machine!

A more `detailed tutorial is available on the wiki <https://github.com/ikreymer/pywb/wiki/Auto-Configuration-and-Wayback-Collections-Manager>`_.

Legacy `installation instructions <https://github.com/ikreymer/pywb/blob/0.9.0b/INSTALL.rst>`_ contains additional
installation and testing examples, using a ``config.yaml`` file. These instructions are from previous releases but
still apply for pywb 0.9.0.


Running Samples / Other Projects
---------------------------------

To run the bundled samples  (also used by test suite), you'll need to clone pywb locally:

1. ``git clone -b 0.9.0b https://github.com/ikreymer/pywb.git``

2. ``python setup.py install``

3. ``wayback`` to run samples

4.  Browse to http://localhost:8080/pywb/\*/example.com to see capture of http://example.com

Additional (older) samples can be found in the `pywb-samples <https://github.com/ikreymer/pywb-samples>`_ repository.

You may also check a listing of `public projects using with pywb <https://github.com/ikreymer/pywb/wiki/Public-Projects-using-pywb>`_


Desktop Web Archive Player
""""""""""""""""""""""""""

There is now alos a downloadable point-and-click `Web Archive Player <https://github.com/ikreymer/webarchiveplayer>`_ which provides
a native OS X and Windows application for browsing web archives, built using pywb.

You can use this tool to quickly check the contents of any WARC or ARC file through a standard point-and-click GUI interface, no
command line tools needed.


pywb Tools Overview
-----------------------------

In addition to the standard Wayback Machine, pywb tool suite includes a
number of useful command-line and web server tools. The tools should be available to run after
running ``python setup.py install``:

* ``live-rewrite-server`` -- a demo live rewriting web server which accepts requests using wayback machine url format at ``/rewrite/`` path, eg, ``/rewrite/http://example.com/`` and applies the same url rewriting rules as are used for archived content.
  This is useful for checking how live content will appear when archived before actually creating any archive files, or for recording data.
  The `webrecorder.io <https://webrecorder.io>`_ service is built using this tool.


* ``cdx-indexer`` -- a command-line tool for creating CDX indexs from WARC and ARC files. Supports SURT and
  non-SURT based cdx files and optional sorting. See ``cdx-indexer -h`` for all options.
  for all options.


* ``cdx-server`` -- a CDX API only server which returns a responses about CDX captures in bulk.
  Includes most of the features of the `original cdx server implementation <https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server>`_,
  updated documentation coming soon.

* ``proxy-cert-auth`` -- a utility to support proxy mode. It can be used in CA root certificate, or per-host certificate with an existing root cert.


* ``wayback`` -- The Wayback Machine application itself.


*  ``wayback-manager`` -- A command-line utility for managing collections, adding WARC/ARC files, metadata and UI templates.
   See ``wayback-manager --help`` for an up-to-date listing of commands and options.


Latest Changes
--------------

See `CHANGES.rst <https://github.com/ikreymer/pywb/blob/0.9.0b/CHANGES.rst>`_ for an up-to-date changelist.


Running as Rewriting Live Web Proxy
-----------------------------------

In addition to replaying archived web content, pywb can serve as a rewriting proxy to the live web. This allows pywb
to server live content, and inject customize web pages on the fly. This allow for a variety of use cases beyond archive replay.

For example, the `pywb-webrecorder <https://github.com/ikreymer/pywb-webrecorder>`_ demonstrates a way to use pywb live web rewriting
together with a recording proxy (warcprox) to record content while browsing.

The `via.hypothes.is <via.hypothes.is>`_ project uses pywb to inject annotations into any live web page.

Running in HTTP/HTTPS Proxy Mode
--------------------------------

pywb can also be used as an actual HTTP and/or HTTPS proxy server. See `pywb Proxy Mode Usage <https://github.com/ikreymer/pywb/wiki/Pywb-Proxy-Mode-Usage>`_ for more details
on configuring proxy mode.

To run as an HTTPS proxy server, pywb provides a facility for generating a custom self-signed root certificate, which can be used to replay HTTPS content from the archive.
(The certificate should be used with caution within a controlled setting).
Using these features requiring an extra dependency: the pyopenssl library must be installed via ``pip install pyopenssl``

For more info, see ``Proxy Mode Usage <https://github.com/ikreymer/pywb/wiki/Pywb-Proxy-Mode-Usage>``_

The `pywb-proxy-demo <https://github.com/ikreymer/pywb-proxy-demo>`_ project also contains a working configuration of proxy mode deployment.


WSGI Container
---------------

The default ``wayback`` application starts pywb in a single-threaded single-process reference WSGI container.

For production use, running in a different container, such as `uWSGI <https://uwsgi-docs.readthedocs.org/en/latest/>`_ is strongly recommended.

For example, the ``uwsgi.ini and ``run-uwsgi.sh`` scripts in this repo provides examples of running pywb with uWSGI.

The module ``pywb.apps.wayback`` may be used as the entry point for WSGI.

pywb should run in any standards (PEP-333 and PEP-3333) compatible WSGI container.


Custom UI and User Metadata
"""""""""""""""""""""""""""

pywb makes it easy to customize most aspects of the UI around archived content, including a custom banner insert, query calendar, search and home pages,
via HTML Jinja2 templates.

You can see a list of all available UI templates by running: ``wayback-manager template --list``

To copy a default template to the file system (for modification), you can run ``wayback-manager template <coll> --add <template_name>``

pywb now also supports custom user metadata for each collection. The metadata may be specified in the ``metadata.yaml`` in each collection's directory.

The metadata is accessible to all UI templates and may be displayed to the user as needed.

See the `Wayback Manager Tutorial <https://github.com/ikreymer/pywb/wiki/Auto-Configuration-and-Wayback-Collections-Manager>`_ and the 
and `UI Customization <https://github.com/ikreymer/pywb/wiki/UI-Customization>`_ page for more details.


About Wayback Machine
---------------------

pywb is compatible with the standard `Wayback Machine <http://en.wikipedia.org/wiki/Wayback_Machine>`_ url format:

Replay: ``http://<host>/<collection>/<timestamp>/<original url>``

- ex: http://pywb.herokuapp.com/pywb/20140127171238/http://www.iana.org

- ex: http://web.archive.org/web/20150316213720/http://www.example.com/

Query Listing: ``http://<host>/<collection>/*/<original url>``

- ex: http://pywb.herokuapp.com/pywb/*/http://iana.org/

- ex: http://web.archive.org/web/*/http://www.example.com/


Additional Reference
--------------------

-  The `wiki <https://github.com/ikreymer/pywb/wiki>`_ will have
   additional technical documentation about various aspects of pywb
   
-  The sample config.yaml file, although not required, will provide a listing of various advanced configuration options:
   `config.yaml <https://github.com/ikreymer/pywb/blob/0.9.0b/config.yaml>`_

Contributions & Bug Reports
---------------------------

Users are encouraged to fork and contribute to this project to improve any and all aspects of web archival
replay and web proxy services.

Please take a look at list of current
`issues <https://github.com/ikreymer/pywb/issues?state=open>`_ and feel
free to open new ones.

.. image:: https://cdn.rawgit.com/gratipay/gratipay-badge/2.0.1/dist/gratipay.png
      :target: https://www.gratipay.com/ikreymer/
