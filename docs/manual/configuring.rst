Configuring the Web Archive
===========================

pywb offers an extensible YAML based configuration format via a main ``config.yaml`` at the root of each web archive


Framed vs Frameless replay
---------------------------

pywb supports both two replay modes:
 * Framed replay, where the replayed content is loaded into an iframe, and a top frame UI provides info and metadata
 * Frameless replay, where the replayed content is loaded directly, and a banner UI is injected into the page.

For security reasons, we recommend running pywb in framed mode, because a malicious site
`could tamper with the banner <http://labs.rhizome.org/presentations/security.html#/13>`_

However, for certain situations, frameless replay made be appropriate.

To disable framed replay, simply add:

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
    |----+ <coll name>
         |
         +----+ archives
              |
              +---- (WARC or ARC files here)
              |
              + indexes
              |
              +---- (CDXJ index files here)
              |
              + templates (optional)
              |
              + static (optional)
              
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

Root Collection Access
^^^^^^^^^^^^^^^^^^^^^^

It is also possible to define a "root" collection, for example, accessible at ``http://localhost:8080/<url>``
Such a collection must be defined explicitly using the ``$root`` as collection name::

  collections:
    $root:
       index: ./path/to/indexes
       resource: ./path/to/archive/

Note: When a root collection is set, no other collections are currently accessible, they are ignored.


HTTP/S Proxy Mode
-----------------


Recording Mode
--------------


UI Customizations
-----------------

pywb supports UI customizations, either for an entire archive,
or per-collection.

Static Files
^^^^^^^^^^^^

The replay server will automatically support static files placed under the following directories:

* Files under the root ``static`` directory can be accessed via ``http://localhost:8080/static/<filename>``

* Files under the per-collection ``./collections/<coll name>/static`` directory can be accessed via ``http://localhost:8080/static/_/<coll name>/<filename>``

Templates
^^^^^^^^^

pywb users Jinja2 templates to render HTML to render the HTML for all aspects of the application.
A version placed in the ``templates`` directory, either in the root or per collection, will override that template.

To copy the default pywb template to the template directory run:

``wb-manager template --add search_html``

The following templates are available:

 * ``home.html`` -- Home Page Template, used for ``http://localhost:8080/``

 * ``search.html`` -- Collection Template, used for each collection page ``http://localhost:8080/<coll name>/``

 * ``query.html`` -- Capture Query Page for a given url, used for ``http://localhost:8080/<coll name/*/<url>``

Error Pages:

 * ``not_found.html`` -- Page to show when a url is not found in the archive

 * ``error.html`` -- Generic Error Page for any error (except not found)

Replay and Banner templates:

 * ``frame_insert.html`` -- Top-frame for framed replay mode (not used with frameless mode)

 * ``head_insert.html`` -- Rewriting code injected into ``<head>`` of each replayed page. 
   This template includes the banner template and itself should generally not need to be modified.

 * ``banner.html`` -- The banner used for frameless replay. Can be set to blank to disable the banner.


