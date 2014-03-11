PyWb 0.2.0
=============

.. image:: https://travis-ci.org/ikreymer/pywb.png?branch=master  :target: https://travis-ci.org/ikreymer/pywb
.. image:: https://coveralls.io/repos/ikreymer/pywb/badge.png?branch=master  :target: https://coveralls.io/r/ikreymer/pywb?branch=master

pywb is a new Python implementation of the Wayback Machine software and
tools.

At its core, it provides a web app which 'replays' archived web data
stored in ARC and WARC files and provides metadata about the archived
captures.

Latest Changes
~~~~~~~~~~~~~~

The basic feature set of web replay is nearly complete.

pywb now features new `domain-specific rules <pywb/rules.yaml>`_ which
are applied to certain difficult and dynamic content in order to make
web replay work.

This rules set will be under constant iteration to deal with new
challenges as the web evoles.

Wayback Machine
~~~~~~~~~~~~~~~

pywb is compatible with the standard Wayback Machine url format:

``http://<host>/<collection>/<timestamp>/<original url>``

Ex: The `Internet Archive Wayback Machine <https//archive.org/web/>`_
has urls of the form:

``http://web.archive.org/web/20131015120316/http://archive.org/``

A listing of archived content, often in calendar form, is available when
a ``*`` is used instead of timestamp.

The Wayback Machine uses an html parser to rewrite relative and absolute
links, as well as absolute links found in javascript, css and some xml.

pywb provides these features as a starting point.

Requirements
~~~~~~~~~~~~

pywb has tested in python 2.6, 2.7 and pypy.

It runs best in python 2.7 currently.

pywb tool suite provides several WSGI applications, which have been
tested under *wsgiref* and *uWSGI*.

For best results, the *uWSGI* container is recommended.

Support for Python 3 is planned.

Sample Data
~~~~~~~~~~~

pywb comes with a a set of sample archived content, also used by the
test suite.

The data can be found in ``sample_archive`` and contains ``warc`` and
``cdx`` files.

The sample archive contains recent captures from ``http://example.com``
and ``http://iana.org``

Runnable Apps
~~~~~~~~~~~~~

The pywb tool suite currently includes two runnable applications in the
``pywb.apps`` package.

-  ``python -m pywb.apps.wayback`` -- start the full wayback on port
   8080

-  ``python -m pywb.apps.cdx_server`` -- start standalone cdx server on
   port 8090

Step-By-Step Installation
~~~~~~~~~~~~~~~~~~~~~~~~~

To start a pywb with sample data:

1. Clone this repo

2. Install with ``python setup.py install``

3. Run pywb via ``python -m pywb.apps.wayback`` to start the server in
   implementation.

OR run ``run-uwsgi.sh`` to start with uWSGI (see below for more info).

4. Test pywb in your browser! (pywb is set to run on port 8080 by
   default).

If everything worked, the following pages should be loading (served from
*sample\_archive* dir):

\| Original Url \| Latest Capture \| List of All Captures \| \|
------------- \| ------------- \| ----------------------- \| \|
``http://example.com`` \|
`http://localhost:8080/pywb/example.com <http://localhost:8080/pywb/example.com>`_
\|
[http://localhost:8080/pywb/*/example.com](http://localhost:8080/pywb/*/example.com)
\| \| ``http://iana.org`` \|
`http://localhost:8080/pywb/iana.org <http://localhost:8080/pywb/iana.org>`_
\|
[http://localhost:8080/pywb/*/iana.org](http://localhost:8080/pywb/*/iana.org)
\|

uWSGI startup script
^^^^^^^^^^^^^^^^^^^^

A sample uWSGI start up script, ``run-uwsgi.sh`` which assumes a default
uWSGI installation is provided as well.

Currently, uWSGI is not installed automatically with this distribution,
but it is recommended for production environments.

Please see `uWSGI
Installation <http://uwsgi-docs.readthedocs.org/en/latest/Install.html>`_
for more details on installing uWSGI.

Vagrant
~~~~~~~

pywb comes with a Vagrantfile to help you set up a VM quickly for
testing and deploy pywb with uWSGI.

If you have `Vagrant <http://www.vagrantup.com/>`_ and
`VirtualBox <https://www.virtualbox.org/>`_ installed, then you can
start a test instance of pywb like so:

::

    git clone https://github.com/ikreymer/pywb.git
    cd pywb
    vagrant up

After pywb and all its dependencies are installed, the uWSGI server will
startup

::

    spawned uWSGI worker 1 (and the only) (pid: 123, cores: 1)

At this point, you can open a web browser and navigate to the examples
above for testing.

Test Suite
~~~~~~~~~~

Currently pywb includes a full (and growing) suite of unit doctest and
integration tests.

Top level integration tests can be found in the ``tests/`` directory,
and each subpackage also contains doctests and unit tests.

The full set of tests can be run by executing:

``python setup.py test``

which will run the tests using py.test.

The py.test coverage plugin is used to keep track of test coverage.

Sample Setup
~~~~~~~~~~~~

pywb is configurable via yaml.

The simplest `config.yaml <config.yaml>`_ is roughly as follows:

::


    collections:
       pywb: ./sample_archive/cdx/


    archive_paths: ./sample_archive/warcs/

This sets up pywb with a single route for collection /pywb

(The the latest version of `config.yaml <config.yaml>`_ contains
additional documentation and specifies all the optional properties, such
as ui filenames for Jinja2/html template files.)

For more advanced use, the pywb init path can be customized further:

-  The ``PYWB_CONFIG_FILE`` env can be used to set a different yaml
   file.

-  Custom init app (with or without yaml) can be created. See
   `wayback.py <pywb/apps/wayback.py>`_ and
   `pywb\_init.py <pywb/core/pywb_init.py>`_ for examples of existing
   initialization paths.

Configuring PyWb With Archived Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Please see the `PyWb
Configuration <https://github.com/ikreymer/pywb/wiki/Pywb-Configuration>`_
for latest instructions on how to setup pywb to run with your existing
WARC/ARC collections.

Additional Documentation
~~~~~~~~~~~~~~~~~~~~~~~~

-  For additional/up-to-date configuration details, consult the current
   `config.yaml <config.yaml>`_

-  The `wiki <https://github.com/ikreymer/pywb/wiki>`_ will have
   additional technical documentation about various aspects of pywb

Contributions
~~~~~~~~~~~~~

You are encouraged to fork and contribute to this project to improve web
archiving replay

Please take a look at list of current
`issues <https://github.com/ikreymer/pywb/issues?state=open>`_ and feel
free to open new ones
