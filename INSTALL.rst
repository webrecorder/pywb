Installation
============

This section covers more detailed installation info for pywb.

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

The pywb tool suite currently includes two runnable applications, installed
as command-line scripts via setuptools

-  ``wayback`` or ``python -m pywb.apps.wayback`` -- start the full wayback on port
   8080

-  ``cdx-server`` or ``python -m pywb.apps.cdx_server`` -- start standalone cdx server on
   port 8090
   
-  ``cdx-indexer`` or ``python -m pywb.warc.archiveindexer`` -- create .cdx indexs for
one more more archive files.

Step-By-Step Installation
~~~~~~~~~~~~~~~~~~~~~~~~~

To start a pywb with sample data:

1. Clone this repo

2. Install with ``python setup.py install``

3. Run ``wayback`` (shorthand for ``python -m pywb.apps.wayback``) to start the pywb wayback server with reference WSGI implementation.

OR run ``run-uwsgi.sh`` or ``run-gunicorn.sh`` to start with uWSGI or gunicorn (see below for more info).

4. Test pywb in your browser! (pywb is set to run on port 8080 by
   default).

If everything worked, the following pages should be loading (served from
*sample\_archive* dir):

+------------------------+----------------------------------------+--------------------------------------------+
| Original Url           | Latest Capture                         | List of All Captures                       | 
+========================+========================================+============================================+
| ``http://example.com`` | http://localhost:8080/pywb/example.com | http://localhost:8080/pywb/\*/example.com  |
+------------------------+----------------------------------------+--------------------------------------------+
| ``http://iana.org``    | http://localhost:8080/pywb/iana.org    | http://localhost:8080/pywb/\*/iana.org     |
+------------------------+----------------------------------------+--------------------------------------------+

uWSGI and gunicorn startup scripts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

pywb includes sample uWSGI and gunicorn scripts ``run-uwsgi.sh`` and
``run-gunicorn.sh`` which pip install uwsgi and gunicorn and attempt to launch
the wsgi app with those containers.

Please see `uWSGI
Installation <http://uwsgi-docs.readthedocs.org/en/latest/Install.html>`_
and `Gunicorn QuickStart <http://gunicorn.org/>`_
for more details on installing these containers.

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

The simplest `config.yaml <https://github.com/ikreymer/pywb/blob/master/config.yaml>`_ is roughly as follows:

::


    collections:
       pywb: ./sample_archive/cdx/


    archive_paths: ./sample_archive/warcs/

This sets up pywb with a single route for collection /pywb

(The the latest version of `config.yaml <https://github.com/ikreymer/pywb/blob/master/config.yaml>`_ contains
additional documentation and specifies all the optional properties, such
as ui filenames for Jinja2/html template files.)

For more advanced use, the pywb init path can be customized further:

-  The ``PYWB_CONFIG_FILE`` env can be used to set a different yaml
   file.

-  Custom init app (with or without yaml) can be created. See
   `wayback.py <https://github.com/ikreymer/pywb/blob/master/pywb/apps/wayback.py>`_ and
   `pywb\_init.py <https://github.com/ikreymer/pywb/blob/master/pywb/core/pywb_init.py>`_ for examples of existing
   initialization paths.
