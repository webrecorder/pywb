PyWb 0.8.2
==========

.. image:: https://travis-ci.org/ikreymer/pywb.png?branch=master
      :target: https://travis-ci.org/ikreymer/pywb
.. image:: https://coveralls.io/repos/ikreymer/pywb/badge.png?branch=master
      :target: https://coveralls.io/r/ikreymer/pywb?branch=master
.. image:: https://img.shields.io/gratipay/ikreymer.svg
      :target: https://www.gratipay.com/ikreymer/

pywb is a python implementation of web archival replay tools, sometimes also known as 'Wayback Machine'.

pywb allows high-quality replay (browsing) of archived web data stored in standardized `ARC <http://en.wikipedia.org/wiki/ARC_(file_format)>`_ and `WARC <http://en.wikipedia.org/wiki/Web_ARChive>`_.
The replay system is designed to accurately replay complex dynamic sites, including video and audio content.

pywb can be used as a traditional web application or an HTTP or HTTPS proxy server, and has been tested on Linux, OS X and Windows platforms.

pywb is also fully compliant with the `Memento <http://mementoweb.org/>`_ protocol (`RFC-7089 <http://tools.ietf.org/html/rfc7089>`_).


Public Projects Using Pywb
---------------------------

Several organizations run public services which use pywb that you may explore directly:

* `Webenact <http://webenact.rhizome.org/excellences-and-perfections/>`_ from `rhizome.org <https://rhizome.org>`_, features artist focused social media reenactments. (Featured in `NYTimes Bits Blog <http://bits.blogs.nytimes.com/2014/10/19/a-new-tool-to-preserve-moments-on-the-internet>`_)

* `Perma.cc <https://perma.cc>`_ embeds pywb as part of a larger `open source application <https://github.com/harvard-lil/perma>`_ to provide web archive replay for law libraries.

* `Hypothes.is Annotations <https://via.hypothes.is>`_ uses the live rewrite feature to add `Hypothes.is <https://hypothes.is>`_ annotation editor into any page or PDF (https://github.com/hypothesis/via)

* `WebRecorder.io <https://webrecorder.io>`_ uses pywb and builds upon pywb-webrecorder to create a hosted web recording and replay system.


Desktop Web Archive Player
""""""""""""""""""""""""""

There is now a downloadable point-and-click `Web Archive Player <https://github.com/ikreymer/webarchiveplayer>`_ which provides
a native OS X and Windows application for browsing web archives, built using pywb. 
You can use this tool to quickly check the contents of any WARC or ARC file with no configuration and installation.


Usage Examples
-----------------------------

This README contains a basic overview of using pywb. After reading this intro, consider also taking a look at these seperate projects:

* `pywb-webrecorder <https://github.com/ikreymer/pywb-webrecorder>`_ demonstrates a way to use pywb and warcprox to record web content while browsing.

* `pywb-samples <https://github.com/ikreymer/pywb-samples>`_ provides additional archive samples with difficult-to-replay content.

* `pywb-proxy-demo <https://github.com/ikreymer/pywb-proxy-demo>`_ showcases the revamped HTTP/S proxy replay system (available from pywb 0.6.0)


pywb Tools Overview
-----------------------------

In addition to the standard wayback machine (explained further below), pywb tool suite includes a
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


* ``wayback`` -- The full Wayback Machine application, further explained below.


Latest Changes
--------------

See `CHANGES.rst <https://github.com/ikreymer/pywb/blob/master/CHANGES.rst>`_ for up-to-date changelist.

For latest on video archiving, see `Video Replay and Recording <https://github.com/ikreymer/pywb/wiki/Video-Replay-and-Recording>`_


Quick Install & Run Samples
---------------------------

1. ``git clone https://github.com/ikreymer/pywb.git``

2. ``python setup.py install``

3. ``wayback`` to run samples

4.  Browse to http://localhost:8080/pywb/\*/example.com to see capture of http://example.com


(The `installation page <https://github.com/ikreymer/pywb/blob/master/INSTALL.rst>`_ contains additional
installation and testing examples.)

Running in Proxy Mode
---------------------

pywb can also be used as an HTTP and/or HTTPS proxy server. See `pywb Proxy Mode Usage <https://github.com/ikreymer/pywb/wiki/Pywb-Proxy-Mode-Usage>`_ for more details
on configuring proxy mode.
The `pywb-proxy-demo <https://github.com/ikreymer/pywb-proxy-demo>`_ project also contains a working configuration of proxy mode deployment.


Configure with Archived Content
-------------------------------

If you have existing WARC or ARC files (.warc, .warc.gz, .arc, .arc.gz), you should be able to view
their contents in pywb after creating sorted .cdx index files of their contents.
This process can be done by running the ``cdx-indexer`` script and only needs to be done once.

(See the note below if you already have .cdx files for your archives)


Given an archive of warcs at ``myarchive/warcs``

1. Create a dir for indexes, .eg. ``myarchive/cdx``

2. Run ``cdx-indexer --sort myarchive/cdx myarchive/warcs`` to generate .cdx files for each
   warc/arc file in ``myarchive/warcs``

3. Edit **config.yaml** to contain the following. You may replace ``pywb`` with
   a name of your choice -- it will be the path to your collection. (Multiple collections can be added
   for different sets of .cdx files as well)

::

    collections:
       pywb: ./my_archive/cdx/


    archive_paths: ./my_archive/warcs/


4. Run ``wayback`` to start session.
   If your archives contain ``http://my-archive-page.example.com``, all captures should be accessible
   by browsing to http://localhost:8080/pywb/\*/my-archived-page.example.com

   (You can also use ``run-uwsgi.sh`` or ``run-gunicorn.sh`` to launch using those WSGI containers)


See `INSTALL.rst <https://github.com/ikreymer/pywb/blob/master/INSTALL.rst>`_ for additional installation info.


Use existing .cdx index files
"""""""""""""""""""""""""""""

If you already have .cdx files for your archive, you can skip the first two steps above.

pywb recommends using `SURT <http://crawler.archive.org/articles/user_manual/glossary.html#surt>`_ (Sort-friendly URI Reordering Transform)
sorted urls and the ``cdx-indexer`` automatically generates indexs in this format.

However, pywb is compatible with regular url keyed indexes also.
If you would like to use non-SURT ordered .cdx files, simply add this field to the config:

::

      surt_ordered: false

UI Customization
"""""""""""""""""""""

pywb makes it easy to customize most aspects of the UI around archived content, including a custom banner insert, query calendar, search and home pages, via HTML Jinja2 templates.
See the config file for comment examples or read more about
`UI Customization <https://github.com/ikreymer/pywb/wiki/UI-Customization>`_.

About Wayback Machine
---------------------

pywb is compatible with the standard `Wayback Machine <http://en.wikipedia.org/wiki/Wayback_Machine>`_ url format:

``http://<host>/<collection>/<timestamp>/<original url>``

Some examples of this url from other wayback machines (not implemented via pywb):

``http://web.archive.org/web/20140312103519/http://www.example.com``
``http://www.webarchive.org.uk/wayback/archive/20100513010014/http://www.example.com/``


A listing of archived content, often in calendar form, is available when
a ``*`` is used instead of timestamp.

The Wayback Machine often uses an html parser to rewrite relative and absolute
links, as well as absolute links found in javascript, css and some xml.

pywb provides these features as a starting point.


Additional Documentation
------------------------

-  For additional/up-to-date configuration details, consult the current
   `config.yaml <https://github.com/ikreymer/pywb/blob/master/config.yaml>`_

-  The `wiki <https://github.com/ikreymer/pywb/wiki>`_ will have
   additional technical documentation about various aspects of pywb

Contributions
-------------

You are encouraged to fork and contribute to this project to improve web
archiving replay!

Please take a look at list of current
`issues <https://github.com/ikreymer/pywb/issues?state=open>`_ and feel
free to open new ones.

.. image:: https://cdn.rawgit.com/gratipay/gratipay-badge/2.0.1/dist/gratipay.png
      :target: https://www.gratipay.com/ikreymer/
