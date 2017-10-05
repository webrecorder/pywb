Configuring the Web Archive
===========================

pywb offers an extensible YAML based configuration format via a main ``config.yaml`` at the root of each web archive.

Framed vs Frameless Replay vs HTTPS proxy
-----------------------------------------

pywb supports several modes for serving archived web content.

With **framed replay**, the archived content is loaded into an iframe, and a top frame UI provides info and metadata.
In this mode, the top frame url is for example, ``http://my-archive.example.com/<coll name>/http://example.com/`` while
the actual content is served at ``http://my-archive.example.com/<coll name>/mp_/http://example.com/``


With **frameless replay**, the archived content is loaded directly, and a banner UI is injected into the page.

In this mode, the content is served directly at ``http://my-archive.example.com/<coll name>/http://example.com/``

(pywb can also supports HTTP/S **proxy mode** which requires additional setup. See :ref:`https-proxy` for more details).

For security reasons, we recommend running pywb in framed mode, because a malicious site
`could tamper with the banner <http://labs.rhizome.org/presentations/security.html#/13>`_

However, for certain situations, frameless replay made be appropriate.

To disable framed replay add:

``framed_replay: false`` to your config.yaml


Directory Structure
-------------------

The pywb system assumes the following default directory structure for a web archive::

    +-- config.yaml (optional)
    |
    +-- templates (optional)
    |
    +-- static (optional)
    |
    +-- collections
        |
        +-- <coll name>
            |
            +-- archives
            |     |
            |     +-- (WARC or ARC files here)
            |
            +-- indexes
            |     |
            |     +-- (CDXJ index files here)
            | 
            +-- templates
            |     |
            |     +-- (optional html templates here)
            |
            +-- static
                  |
                  +-- (optional custom static assets here)
              

If running with default settings, the ``config.yaml`` can be omitted.

It is possible to config these paths in the config.yaml
The following are some of the implicit default settings which can be customized::

  collections_root: collections
  archive_paths: archive
  index_paths: indexes

(For a complete list of defaults, see the ``pywb/default_config.yaml`` file for reference)

Index Paths
^^^^^^^^^^^

The ``index_paths`` key defines the subdirectory for index files (usually CDXJ) and determine the contents of each archive collection.

The index files usually contain a pointer to a WARC file, but not the absolute path.

Archive Paths
^^^^^^^^^^^^^

The ``archive_paths`` key indicates how pywb will resolve WARC files listed in the index.

For example, it is possible to configure multiple archive paths::

  archive_paths:
    - archive
    - http://remote-bakup.example.com/collections/

When resolving a ``example.warc.gz``, pywb will then check (in order):

 * First, ``collections/<coll name>/example.warc.gz``
 * Then, ``http://remote-backup.example.com/collections/<coll name>/example.warc.gz`` (if first lookup unsuccessful)


Custom Defined Collections
--------------------------

While pywb can detect automatically collections following the above directory structure,
it may be useful to declare custom collections explicitly.

In addition, several "special" collection definitions are possible.

All custom defined collections are placed under the ``collections`` key in ``config.yaml``


Live Web Collection
^^^^^^^^^^^^^^^^^^^

The live web collection proxies all data to the live web, and can be defined as follows::

  collections:
    live: $live

This configures the ``/live/`` route to point to the live web.

(As a shortcut, ``wayback --live`` adds this collection via cli w/o modifiying the config.yaml)

This collection can be useful for testing, or even more powerful, when combined with recording.


Auto "All" Aggregate Collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The aggregate all collections automatically aggregates data from all collections in the ``collections`` directory::

  collections:
    all: $all

Accessing ``/all/<url>`` will cause an aggregate lookup within the collections directory.

Note: It is not (yet) possible to exclude collections from the all collection, although "special" collections are not included.


Generic Collection Definitions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The collection definition syntax allows for explicitly setting the index, archive paths
and all other templates, per collection, for example::

  collections:
    custom:
       index: ./path/to/indexes
       resource: ./some/other/path/to/archive/
       query_html: ./path/to/templates/query.html

This configuration supports the full Warcserver config syntax, including
remote archives, aggregation and fallback sequences (link)

This format also makes it easier to move legacy collections that have unique path requirements.

Root Collection
^^^^^^^^^^^^^^^

It is also possible to define a "root" collection, for example, accessible at ``http://my-archive.example.com/<url>``
Such a collection must be defined explicitly using the ``$root`` as collection name::

  collections:
    $root:
       index: ./path/to/indexes
       resource: ./path/to/archive/

Note: When a root collection is set, no other collections are currently accessible, they are ignored.


Recording Mode
--------------

TODO

.. _https-proxy:

HTTP/S Proxy Mode
-----------------

TODO

UI Customizations
-----------------

pywb supports UI customizations, either for an entire archive,
or per-collection.

Static Files
^^^^^^^^^^^^

The replay server will automatically support static files placed under the following directories:

* Files under the root ``static`` directory can be accessed via ``http://my-archive.example.com/static/<filename>``

* Files under the per-collection ``./collections/<coll name>/static`` directory can be accessed via ``http://my-archive.example.com/static/_/<coll name>/<filename>``

Templates
^^^^^^^^^

pywb users Jinja2 templates to render HTML to render the HTML for all aspects of the application.
A version placed in the ``templates`` directory, either in the root or per collection, will override that template.

To copy the default pywb template to the template directory run:

``wb-manager template --add search_html``

The following templates are available:

 * ``home.html`` -- Home Page Template, used for ``http://my-archive.example.com/``

 * ``search.html`` -- Collection Template, used for each collection page ``http://my-archive.example.com/<coll name>/``

 * ``query.html`` -- Capture Query Page for a given url, used for ``http://my-archive.example.com/<coll name/*/<url>``

Error Pages:

 * ``not_found.html`` -- Page to show when a url is not found in the archive

 * ``error.html`` -- Generic Error Page for any error (except not found)

Replay and Banner templates:

 * ``frame_insert.html`` -- Top-frame for framed replay mode (not used with frameless mode)

 * ``head_insert.html`` -- Rewriting code injected into ``<head>`` of each replayed page. 
   This template includes the banner template and itself should generally not need to be modified.

 * ``banner.html`` -- The banner used for frameless replay. Can be set to blank to disable the banner.


Custom Outer Replay Frame
^^^^^^^^^^^^^^^^^^^^^^^^^

The top-frame used for framed replay can be replaced or augmented
by modifiying the ``frame_insert.html``.

To start with modifiying the default outer page, you can add it to the current
templates directory by running ``wb-frame template --add frame_insert.html``

To initialize the replay, the outer page should include ``wb_frame.js``,
create an ``<iframe>`` element and pass the id (or element itself) to the ``ContentFrame`` constructor:

.. code-block:: html

  <script src='{{ host_prefix }}/{{ static_path }}/wb_frame.js'> </script>
  <script>
  var cframe = new ContentFrame({"url": "{{ url }}" + window.location.hash,
                                 "prefix": "{{ wb_prefix }}",
                                 "request_ts": "{{ wb_url.timestamp }}",
                                 "iframe": "#replay_iframe"});
  </script>


The outer frame can receive notifications of changes to the replay via ``postMessage``

For example, to detect when the content frame changed and log the new url and timestamp,
use the following script to the outer frame html:

.. code-block:: javascript

  window.addEventListener("message", function(event.data) {
     if (event.data.wb_type == "load" && event.data.wb_type == "replace-url") {
        console.log("New Url: " + event.data.url);
        console.log("New Timestamp: " + event.data.ts);
     }
  }

The ``load`` message is sent when a new page is first loaded, while ``replace-url`` is used
for url changes caused by content frame History navigation.

