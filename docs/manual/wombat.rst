.. _wombat:

######
Wombat
######

Wombat is pywb's client-side URL rewriting system that performs the rewrites through
targeted JavaScript overrides.

Historically, Wombat was included in and distributed by pywb as an three file `library`
that grew in size and complexity proportional to how the web has changed over time.

Starting in pywb 2.3.x Wombat was rewritten in order to factor out the client-side URL
rewriting library from the system used by pywb.

This was done in order to facilitate improved development experience and to introduce a thorough
testing suite that checks for the correctness of the overrides with respect to web standards.

The remaining portions of this documentation covers the development and testing of the `library`,
as well as, the creation of the system from library.

Before we continue, please note the following terminology:

``bundle``
  A single file that is the result of concatenating multiple source files into a single file

``bundle entry point``
  The root file that imports all additional functionality required to produce the resulting bundle


Components
==========

The Wombat client-side URL rewriting system is comprised of three files (bundles)

* ``wombat.js``
* ``wombatProxyMode.js``
* ``wombatWorkers.js``

These files are located in the static directory of pywb and are generated
as apart of the  libraries build step.

The library can be found in the ``wombat`` directory located int the root
of the projects repository (i.e. ``pywb/wombat``).

**Note**: We do not go into details of each file included in a bundle as those details
are out of the scope of this documentation and ask those interested to consult
the documentation included in each files source code.


**wombat.js**

This bundle is the primary bundle of Wombat as it is used in both non-proxy recording and replay.

The entry point for this bundle is `src/wbWombat.js`.

An representation of the bundles contents is shown below.

::

 wbWombat.js
  - wombat.js
    - funcMap.js
    - customStorage.js
    - wombatLocation.js
    - listeners.js
    - autoFetchWorker.js



**wombatProxyMode.js**

This bundle is an stripped down version of `wombat.js` that applies a minimal set of overrides
to the browsers JavaScript APIs in order to facilitate pywb's proxy recording mode

The entry point for this bundle is `src/wbWombatProxyMode.js`.

An representation of the bundles contents is shown below.

::

 wbWombatProxyMode.js
  - wombatLite.js
    - autoFetchWorkerProxyMode.js


**wombatWorkers.js**


This bundle is not a bundle per say but rather a flat file that applies the minimal set of
overrides necessary to ensure that JavaScript web and service worker's operate as expected in both
non-proxy recording and replay.


Development and Testing
========================

**Requirements**

Development and testing of Wombat requires that Node.js version >= 11 be installed

Testing requires that a version of Google Chrome (v73 or greater) be installed and not in use prior to running
the test suite


**Development**

The simplest way to begin developing is to execute the included ``bootstrap.sh``,
found in the root wombat directory.

``bootstrap.sh`` will

* install the dependencies necessary to build and test Wombat
* builds Wombat in production mode and places it in the `pywb/static` directory
* copy the bootstrap.min.css used by pywb
  into the test's assets directory
* build the required test utility bundles

After executing the boot strapping script the following ``npm scripts`` can be used

``build-prod``
  builds all bundles in production mode

``build-dev``
  builds all bundles in development mode

``build-dev-watch``
  builds all or selected bundles in development mode and rebuilds on changes (defaults to ``wombat.js``)

``build-dev-watch-proxy``
  builds ``wombatProxyMode.js`` in development mode and rebuilds on changes

``build-full-test``
  builds all bundles in development mode for testing as well as the internal testing util bundles

``build-test``
  builds all bundles in development mode for testing

``build-test-bundle``
  builds the internal testing util bundles

``test``
  executes the test suite

All commands except those for testing place the resulting bundles in the ``pywb/static`` directory

To control which bundles get built and watched for rebuilding using the ``build-dev-watch``
the following environment variables can be used (they simple need to exist)

* ALL: same as executing ``build-dev``
* PROXY: same as executing ``build-dev-watch-proxy``
* WORKER: only ``wombatProxyMode.js``


The bundler used by Wombat is ``rollup`` and the following configs are used

* ``rollup.config.prod.js``: Controls development bundling
* ``rollup.config.dev.js``: Controls production bundling
* ``rollup.config.test.js``: Controls test bundling

**Testing**

As previously mentioned, the test suite can be run by executing the ``test`` npm script.

The test suite is comprised of 568 tests split over nine files

* ``original-karma-tests.js``: The original Wombat test suite
* ``overrides-browser.js``: Tests overrides applied to the History, Location, etc APIs of the browser
* ``overrides-css.js``: Tests overrides applied to CSS APIs
* ``overrides-dom.js``: Tests overrides applied to DOM APIs
* ``overrides-http.js``: Tests overrides applied to HTTP APIs
* ``overrides-workers.js``: Tests overrides applied to worker APIs
* ``setup-after-initialization.js``: Tests the results of initialization of the system
* ``setup-before-initialization.js``: Tests correctness of the initial state of the browser before initialization
* ``setup-initialization.js``: Tests the ability of the system to become initializated

