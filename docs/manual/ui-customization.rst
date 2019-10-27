.. _ui-customizations:

UI Customizations
-----------------

pywb supports UI customizations, either for an entire archive,
or per-collection. Jinja2 templates are used for rendering all views,
and static files can also be added as needed.

Templates
^^^^^^^^^

Default templates, listed below, are found in the ``./pywb/templates/`` directory.

Custom template files placed in the ``templates`` directory, either in the root or per collection, will override that template.

To copy the default pywb template to the template directory using the cli tools, run:

``wb-manager template --add search_html``

The following page-level templates are available, corresponding to home page, collection page or search results:

 * ``index.html`` -- Home Page Template, used for ``http://my-archive.example.com/``

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


To customize the default pywb UI across multiple pages, the following generic templates
can also be overriden:

* ``base.html`` -- The base template used for non-replay related pages.

* ``head.html`` -- Template containing content to be added to the ``<head>`` of the ``base`` template

* ``header.html`` -- Template to be added as the first content of the ``<body>`` tag of the ``base`` template

* ``footer.html`` -- Template for adding content as the "footer" of the ``<body>`` tag of the ``base`` template


The ``base.html`` template also provides five blocks that can be supplied by templates that extend it.

* ``title`` -- Block for supplying the title for the page

* ``head`` -- Block for adding content to the ``<head>``, includes ``head.html`` template

* ``header`` -- Block for adding content to the ``<body>`` before the ``body`` block, includes the ``header.html`` template

* ``body`` -- Block for adding the primary content to template

* ``footer`` -- Block for adding content to the ``<body>`` after the ``body`` block, includes the ``footer.html`` template

Static Files
^^^^^^^^^^^^

The pywb server will automatically support static files placed under the following directories:

* Files under the root ``static`` directory can be accessed via ``http://my-archive.example.com/static/<filename>``

* Files under the per-collection ``./collections/<coll name>/static`` directory can be accessed via ``http://my-archive.example.com/static/_/<coll name>/<filename>``


Custom Metadata
^^^^^^^^^^^^^^^

It is possible to also add custom metadata that will be available in the Jinja2 template.

For dynamic collections, any fields placed under ``<coll_name>/metadata.yaml`` filed can be accessed

via the ``{{ metadata }}`` variable.

For example, if metadata file contains:

.. ex-block:: yaml

    somedata: value

Accessing ``{{ metadata.somedata }}`` will resolve to ``value``

The metadata can also be added via commandline: ``wb-manager metadata myCollection --set somedata=value]``



The default collection UI template (search.html) currently lists all of the available metadata fields.


Custom Outer Replay Frame
^^^^^^^^^^^^^^^^^^^^^^^^^

The top-frame used for framed replay can be replaced or augmented
by modifying the ``frame_insert.html``.

To start with modifying the default outer page, you can add it to the current
templates directory by running ``wb-manager template --add frame_insert_html``

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

  window.addEventListener("message", function(event) {
    if (event.data.wb_type == "load" || event.data.wb_type == "replace-url") {
      console.log("New Url: " + event.data.url);
      console.log("New Timestamp: " + event.data.ts);
    }
  });

The ``load`` message is sent when a new page is first loaded, while ``replace-url`` is used
for url changes caused by content frame History navigation.
