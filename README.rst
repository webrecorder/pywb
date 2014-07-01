PyWb 0.4.7
==========

.. image:: https://travis-ci.org/ikreymer/pywb.png?branch=master
      :target: https://travis-ci.org/ikreymer/pywb
         
.. image:: https://coveralls.io/repos/ikreymer/pywb/badge.png?branch=master
      :target: https://coveralls.io/r/ikreymer/pywb?branch=master

pywb is a python implementation of web archival replay tools, sometimes also known as 'Wayback Machine'.

pywb allows high-quality replay (browsing) of archived web data stored in standardized `ARC <http://en.wikipedia.org/wiki/ARC_(file_format)>`_ and `WARC <http://en.wikipedia.org/wiki/Web_ARChive>`_.

*For an example of deployed service using pywb, please see the https://webrecorder.io project*

pywb Tools
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


* ``wayback`` -- The full Wayback Machine application, further explained below.


Latest Changes
--------------

See `CHANGES.rst <https://github.com/ikreymer/pywb/blob/master/CHANGES.rst>`_ for up-to-date changelist.


Quick Install & Run Samples
---------------------------

1. ``git clone https://github.com/ikreymer/pywb.git``

2. ``python setup.py install``

3. ``wayback`` to run samples

4.  Browse to http://localhost:8080/pywb/\*/example.com to see capture of http://example.com


(The `installation page <https://github.com/ikreymer/pywb/blob/master/INSTALL.rst>`_ contains additional
installation and testing examples.)


Configure with Archived Content
-------------------------------

If you have existing WARC or ARC files (.warc, .warc.gz, .arc, .arc.gz), you should be able to view
their contents in pywb after creating sorted .cdx index files of their contents.
This process can be done by running the ``cdx-indexer`` script and only needs to be done once.

(See the note below if you already have .cdx files for your archives)


Given an archive of warcs at ``myarchive/warcs``

1. Create a dir for indexs, .eg. ``myarchive/cdx``

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
