PyWb 0.2.2
=============

.. image:: https://travis-ci.org/ikreymer/pywb.png?branch=develop
      :target: https://travis-ci.org/ikreymer/pywb
         
.. image:: https://coveralls.io/repos/ikreymer/pywb/badge.png?branch=develop
      :target: https://coveralls.io/r/ikreymer/pywb?branch=develop

pywb is a python implementation of web archival replay tools, sometimes also known as 'Wayback Machine'.

The software includes wsgi apps and other tools which 'replay' archived web data
stored in standard `ARC <http://en.wikipedia.org/wiki/ARC_(file_format)>`_ and `WARC <http://en.wikipedia.org/wiki/Web_ARChive>`_ files and can provide additional information about the archived captures.


Quick Install & Run Samples
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. ``git clone https://github.com/ikreymer/pywb.git``

2. ``python setup.py install``

3. ``wayback`` to run samples

4.  Browse to http://localhost:8080/pywb/\*/example.com to see capture of http://example.com


(The `installation page <https://github.com/ikreymer/pywb/blob/develop/INSTALL.rst>`_ contains additional
installation and testing examples.)


Configure to Replay Archived Content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have existing WARC or ARC files (.warc, .warc.gz, .arc, .arc.gz), you should be able
to replay them in pywb after creating sorted indexs with the ``cdx-indexer`` script.


Given an archive of warcs at ``myarchive/warcs``

1. Create a dir for indexs, .eg. ``myarchive/cdx``

2. Run ``cdx-indexer --sort myarchive/cdx myarchive/warcs`` to generate .cdx files for each
   warc/arc file in ``myarchive/warcs``

3. Edit ``config.yaml`` to contain the following. You may replace ``pywb`` with
   a name of your choice -- it will be the path to your collection. (Multiple collections can be added
   for different sets of .cdx files as well)

::

    collections:
       pywb: ./my_archive/cdx/


    archive_paths: ./my_archive/warcs/


4. Run ``wayback`` to start session.
   If your archives contain ``http://my-archive-page.example.com``, all captures should be accessible
   by browsing to http://localhost:8080/pywb/\*/my-archived-page.example.com

   (You can also ./run-uwsgi.sh for running with those WSGI containers)


Use existing .cdx index files
"""""""""""""""""""""""""""""

If you already have .cdx files for your archive, you can skip the first two steps above.

pywb recommends using `SURT <http://crawler.archive.org/articles/user_manual/glossary.html#surt>`_ (Sort-friendly URI Reordering Transform)
sorted urls and the ``cdx-indexer`` automatically generates indexs in this format.

However, pywb is compatible with regular url keyed indexs.
If you would like to use non-SURT ordered .cdx files, simply add this field to the config:

::

      surt_ordered: false



Latest Changes
~~~~~~~~~~~~~~
See `CHANGES.rst <https://github.com/ikreymer/pywb/develop/CHANGES.rst>`_ for up-to-date changelist.



About Wayback
~~~~~~~~~~~~~

pywb is compatible with the standard Wayback Machine url format:

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
~~~~~~~~~~~~~~~~~~~~~~~~

-  For additional/up-to-date configuration details, consult the current
   `config.yaml <https://github.com/ikreymer/pywb/blob/develop/configs/config.yaml>`_

-  The `wiki <https://github.com/ikreymer/pywb/wiki>`_ will have
   additional technical documentation about various aspects of pywb

Contributions
~~~~~~~~~~~~~

You are encouraged to fork and contribute to this project to improve web
archiving replay!

Please take a look at list of current
`issues <https://github.com/ikreymer/pywb/issues?state=open>`_ and feel
free to open new ones.
