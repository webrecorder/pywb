Webrecorder pywb 2.0
====================

.. image:: https://travis-ci.org/ikreymer/pywb.svg?branch=master
      :target: https://travis-ci.org/ikreymer/pywb
.. image:: https://coveralls.io/repos/ikreymer/pywb/badge.svg?branch=master
      :target: https://coveralls.io/r/ikreymer/pywb?branch=master

Web Archiving Tools for All
---------------------------

`View the full pywb 2.0 documentation here <https://pywb.readthedocs.org>`_

**pywb** is a Python (2 and 3) web archiving toolkit for replaying web archives large and small as accurately as possible.
The toolkit now also includes new features for creating high-fidelity web archives.

This toolset forms the foundation of Webrecorder project, but also provides a generic web archiving toolkit
that is used by other web archives, including the traditional "Wayback Machine" functionality.


New Features
^^^^^^^^^^^^

The 2.0 release includes a major overhaul of pywb and introduces the following new features, including:

* Dynamic multi-collection configuration system with no-restart updates.

* New recording capability to create new web archives from the live web or other archives.

* Componentized architecture with standalone Warcserver, Recorder and Rewriter components.

* Support for advanced "memento aggregation" and fallback chains for querying multiple remote and local archival sources.

* HTTP/S Proxy Mode with customizable Certificate Authority for proxy mode recording and replay.

* Flexible rewriting system with pluggable rewriters for different content-types.

* Significantly improved client-side rewriting to handle most modern web sites.

* Improved 'calendar' query UI, groping results by year and month, and updated replay banner.


Please see the `full documentation <https://pywb.readthedocs.org>`_ for more detailed info on all these features.


Work in Progress / Coming Soon
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A few key features are high on list of priorities, but have not yet been implemented, including:

* Url Exclusion System

* New Default UI (calendar and banner)

If you are intersted in contributing, especially to any of these areas, please let us know!


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

Please take a look at list of current issues and feel free to open new ones about any aspect of pywb, including the new documentation.

