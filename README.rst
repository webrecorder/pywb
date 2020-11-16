The Data Shed usage
====================

Support for record and replay to and from S3 has been added.

When recording, simply use wayback in record mode as normal but also set the AWS_S3_BUCKET and AWS_PROFILE environment variables.

When replaying, AWS_S3_BUCKET, AWS_PROFILE environment variables must be set. config.yaml can contain something like the following for explicit index and archive locations on S3:

.. code-block:: yaml

    collections:
        all: $all
        mycollection:
            index_paths: s3://bucketname/collections/mycollection/indexes/index.cdxj
            archive_paths: s3://bucketname/collections/mycollection/archive/

Alternatively, if the collection is a standard pywb structure as described `here <https://pywb.readthedocs.io/en/latest/manual/configuring.html#directory-structure>`_ then config.yaml can make use of :code:`collections_root` to simplify further:

.. code-block:: yaml

    collection_root: s3://bucketname/collections

pywb also supports environment variable resolution in yaml config files so the following config.yaml:

.. code-block:: yaml

    collections_root: ${PYWB_COLLECTIONS_ROOT}

will serve collections found in the root using this command:

.. code-block:: yaml

    PYWB_COLLECTIONS_ROOT=s3://bucketname/collections AWS_S3_BUCKET=bucketname AWS_PROFILE=who-sandbox wayback

The drawback of this method is that collections can't be browsed or searched at :code:`http://localhost:8080` but will be served at :code:`http://localhost:8080/mycollection/https://www.thedatashed.co.uk/`, so you have to know what url and collection you want to load beforehand.


Webrecorder pywb 2.4
====================

.. image:: https://raw.githubusercontent.com/webrecorder/pywb/master/pywb/static/pywb-logo.png

.. image:: https://travis-ci.org/webrecorder/pywb.svg?branch=master
      :target: https://travis-ci.org/webrecorder/pywb
.. image:: https://ci.appveyor.com/api/projects/status/qxnbunw65o929599/branch/master?svg=true
      :target: https://ci.appveyor.com/project/webrecorder/pywb/branch/master
.. image:: https://codecov.io/gh/webrecorder/pywb/branch/master/graph/badge.svg
      :target: https://codecov.io/gh/webrecorder/pywb

Web Archiving Tools for All
---------------------------

`View the full pywb documentation <https://pywb.readthedocs.org>`_

**pywb** is a Python (2 and 3) web archiving toolkit for replaying web archives large and small as accurately as possible.
The toolkit now also includes new features for creating high-fidelity web archives.

This toolset forms the foundation of Webrecorder project, but also provides a generic web archiving toolkit
that is used by other web archives, including the traditional "Wayback Machine" functionality.


New Features
^^^^^^^^^^^^

The 2.x release included a major overhaul of pywb and introduces many new features, including the following:

* Dynamic multi-collection configuration system with no-restart updates.

* New recording capability to create new web archives from the live web or other archives.

* Componentized architecture with standalone Warcserver, Recorder and Rewriter components.

* Support for Memento API aggregation and fallback chains for querying multiple remote and local archival sources.

* HTTP/S Proxy Mode with customizable certificate authority for proxy mode recording and replay.

* Flexible rewriting system with pluggable rewriters for different content-types.

* Standalone, modular `client-side rewriting system (wombat.js) <https://github.com/webrecorder/wombat>`_ to handle most modern web sites.

* Improved 'calendar' query UI with incremental loading, grouping results by year and month, and updated replay banner.

* New in 2.4: Extensible UI customizations system for modifying all aspects of the UI.

* New in 2.4: Robust access control system for blocking or excluding URLs, by prefix or by exact match.


Please see the `full documentation <https://pywb.readthedocs.org>`_ for more detailed info on all these features.


Installation
------------

To run and install locally you can:

* Install with ``python setup.py install``

* Run tests with ``python setup.py test``

* Run Wayback with ``wayback`` (see docs for info on how to setup collections)

* Build docs locally with:  ``cd docs; make html``. (The docs will be built in ``./_build/html/index.html``)


Consult the local or `online docs <https://pywb.readthedocs.org>`_ for latest usage and configuration details.


Contributions & Bug Reports
---------------------------

Users are encouraged to fork and contribute to this project to keep improving web archiving tools.

If you are interested in contributing, especially to any of these areas, please let us know!

Otherwise, please take a look at `list of current issues <https://github.com/webrecorder/pywb/issues>`_ and feel free to open new ones about any aspect of pywb, including the new documentation.


