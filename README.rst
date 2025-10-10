Webrecorder pywb 2.9
====================

.. image:: https://raw.githubusercontent.com/webrecorder/pywb/main/pywb/static/pywb-logo.png

.. image:: https://github.com/webrecorder/pywb/workflows/CI/badge.svg
      :target: https://github.com/webrecorder/pywb/actions
.. image:: https://codecov.io/gh/webrecorder/pywb/branch/main/graph/badge.svg
      :target: https://codecov.io/gh/webrecorder/pywb

Web Archiving Tools for All
---------------------------

`View the full pywb documentation <https://pywb.readthedocs.org>`_

**pywb** is a Python 3 web archiving toolkit for replaying web archives large and small as accurately as possible.
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

* Extensible UI customizations system for modifying all aspects of the UI.

* Robust access control system for blocking or excluding URLs, by prefix or by exact match.

* New in 2.6: Access Control embargo and http-header control access settings.

* New in 2.6: Support for localization and multi-language deployment.

* New in 2.7: New banner/calendar UI written in `Vue <https://vuejs.org/>`_, with interactive timeline and easier theming of colors and logo via ``config.yaml``.

* New in 2.9: Client-side replay is added as an option and can be enabled via ``config.yaml``


Please see the `full documentation <https://pywb.readthedocs.org>`_ for more detailed info on all these features.


Installation for Deployment
---------------------------

On Linux-based systems, first verify that ``python3-dev`` is installed. If it is not, install it with your package manager. E.g. on a Debian-based system, use:

``sudo apt install python3-dev``

To install pywb for usage, you can use:

``pip install pywb``

Note: depending on your Python installation, you may have to use `pip3` instead of `pip`.


Installation from local copy
----------------------------

``git clone https://github.com/webrecorder/pywb``

To install from a locally cloned copy, install with ``pip install -e .`` or ``python setup.py install``.

To run tests, we recommend installing ``pip install tox tox-current-env`` and then running ``tox --current-env`` to test in your current Python environment.

To Build docs locally, run:  ``cd docs; make html``. (The docs will be built in ``./_build/html/index.html``)


Running
-------

After installation, you can run ``pywb`` or ``wayback``.

Consult the local or `online docs <https://pywb.readthedocs.org>`_ for latest usage and configuration details.


Documentation
-------------

The pywb documentation is extensive. Some links to a few key guides:

* `Getting Started Guide <https://pywb.readthedocs.io/en/latest/manual/usage.html#getting-started>`_

* `Embargo and Access Control Guide <https://pywb.readthedocs.io/en/latest/manual/access-control.html>`_

* `Localization and Multi-Language Guide <https://pywb.readthedocs.io/en/latest/manual/localization.html>`_

* `Deployment Guide <https://pywb.readthedocs.io/en/latest/manual/usage.html#deployment>`_

* `OpenWayback Transition Guide <https://pywb.readthedocs.io/en/latest/manual/owb-transition.html>`_


Contributions & Bug Reports
---------------------------

Users are encouraged to fork and contribute to this project to keep improving web archiving tools. Please consult the `contributing guide <CONTRIBUTING.md>`_ for information on how to contribute to pywb.
