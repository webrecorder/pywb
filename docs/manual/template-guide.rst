.. _template-guide:

Template Guide
==============

Introduction
------------

This guide provides a reference of all of the templates available in pywb and how they could be modified.

These templates are found in the ``pywb/templates`` directory and can be overridden as needed, one HTML page at a time.

Template variables are listed as ``{{ variable }}`` to indicate the syntax used for rendering the value of the variable in Jinja2.

Copying a Template For Modification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To modify a template, it is often useful to start with the default template. To do so, simply copy a default template
to a local ``templates`` directory.

For convenience, you can also run: ``wb-manager template --add <template-name>`` to add the template automatically.

For a list of available templates that can be overridden in this way, run ``wb-manager template --list``.


Per-Collection Templates
^^^^^^^^^^^^^^^^^^^^^^^^

Certain templates can be customized per-collection, instead of for all of pywb.

To override a template for a specific collection only, run ``wb-manager template --add <template-name> <coll-name>``

For example:


.. code:: console
    
    wb-manager init my-coll
    wb-manager template --add search_html my-coll

This will create the file ``collections/my-coll/templates/search.html``, a copy of the default search.html, but configured to be used only
for the collection ``my-coll``.



Base Templates (and supporting templates)
-----------------------------------------

File: ``base.html``

This template includes the HTML added to all pages other than framed replay. Shared JS and CSS includes meant for pages other than framed replay can be added here.

To customize the default pywb UI across multiple pages, the following additional templates
can also be overriden:

* ``head.html`` -- Template containing content to be added to the ``<head>`` of the ``base`` template

* ``header.html`` -- Template to be added as the first content of the ``<body>`` tag of the ``base`` template

* ``footer.html`` -- Template for adding content as the "footer" of the ``<body>`` tag of the ``base`` template


Note: The default pywb ``head.html`` and ``footer.html`` are currently blank. They can be populated to customize the rendering, add analytics, etc... as needed. Content such as styles or JS code (for example for analytics) must be added to the ``frame_insert.html`` template as well (details on that template below) to also be included in framed replay.


The ``base.html`` template also provides five blocks that can be supplied by templates that extend it.

* ``title`` -- Block for supplying the title for the page

* ``head`` -- Block for adding content to the ``<head>``, includes ``head.html`` template

* ``header`` -- Block for adding content to the ``<body>`` before the ``body`` block, includes the ``header.html`` template

* ``body`` -- Block for adding the primary content to template

* ``footer`` -- Block for adding content to the ``<body>`` after the ``body`` block, includes the ``footer.html`` template


Home, Collection and Search Templates
-------------------------------------


Home Page Template
^^^^^^^^^^^^^^^^^^

File: ``index.html``

This template renders the home page for pywb, and by default renders a list of available collections.


Template variables:

* ``{{ routes }}`` - a list of available collection routes.

* ``{{ all_metadata }}`` - a dictionary of all metadata for all collections, keyed by collection id. See :ref:`custom-metadata` for more info on the custom metadata.


Additionally, the :ref:`shared-template-vars` are also available to the home page template, as well as all other templates.


Collection Page Template
^^^^^^^^^^^^^^^^^^^^^^^^

File: ``search.html``

The 'collection page' template is the page rendered when no URL is specified, e.g. ``http://localhost:8080/my-collection/``.

The default template renders a search page that can be used to start searching for URLs.

Template variables:

* ``{{ coll }}`` - the collection name identifier.

* ``{{ metadata }}`` - an optional dictionary of metadata. See :ref:`custom-metadata` for more info.

* ``{{ ui }}`` - an optional ``ui`` dictionary from ``config.yaml``, if any


.. _custom-metadata:

Custom Metadata
"""""""""""""""

If custom collection metadata is provided, this page will automatically show this metadata as well.

It is possible to also add custom metadata per-collection that will be available to the collection.

For dynamic collections, any fields placed in ``<coll_name>/metadata.yaml`` files can be accessed

via the ``{{ metadata }}`` variable.

For example, if the metadata file contains:

.. code:: yaml

    somedata: value

Accessing ``{{ metadata.somedata }}`` will resolve to ``value``.

The metadata can also be added via commandline: ``wb-manager metadata myCollection --set somedata=value``.


URL Query/Calendar Page Template
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

File: ``query.html``

This template is rendered for any URL search response pages, either a single URL or more complex queries.

For example, the page ``http://localhost:8080/my-collection/*/https://example.com/`` will be rendered using this template, with functionality provided by a Vue application.

Template variables:

* ``{{ url }}`` - the URL being queried, e.g. ``https://example.com/``

* ``{{ prefix }}`` - the collection prefix that will be used for replay, e.g. ``http://localhost:8080/my-collection/``

* ``{{ ui }}`` - an optional ``ui`` dictionary from ``config.yaml``, if any

* ``{{ static_prefix }}`` - the prefix from which static files will be accessed from, e.g. ``http://localhost:8080/static/``.


Replay and Banner Templates
---------------------------

The following templates are used to configure the replay view itself.


Banner Template
^^^^^^^^^^^^^^^

File: ``banner.html``

This template is used to render the banner for framed replay. It is rendered only rendered in the top/outer frame.

Template variables:

* ``{{ url }}`` - the URL being replayed.

* ``{{ timestamp }}`` - the timestamp being replayed, e.g. ``20211226`` in ``http://localhost:8080/pywb/20211226/mp_/https://example.com/``

* ``{{ is_framed }}`` - true/false if currently in framed mode.

* ``{{ wb_prefix }}`` - the collection prefix, e.g. ``http://localhost:8080/pywb/``

* ``{{ host_prefix }}`` - the pywb server origin, e.g. ``http://localhost:8080``

* ``{{ config }}`` - provides the contents of the ``config.yaml`` as a dictionary.

* ``{{ ui }}`` - an optional ``ui`` dictionary from ``config.yaml``, if any.

The default banner creates the UI dynamically in JavaScript using Vue in the ``frame_insert.html`` template.


Custom Banner Template
^^^^^^^^^^^^^^^^^^^^^^

File: ``custom_banner.html``

This template can be used to render a custom banner for frameless replay. It is blank by default.

In frameless replay, the content of this template is injected into the ``head_insert.html`` template to render the banner.


Head Insert Template
^^^^^^^^^^^^^^^^^^^^

File: ``head_insert.html``

This template represents the HTML injected into every replay page to add support for client-side rewriting via ``wombat.js``.

This template is part of the core pywb replay, and modifying this template is not recommended. 

For customizing the banner, modify the ``banner.html`` (framed replay) or ``custom_banner.html`` (frameless replay) template instead.


Top Frame Template
^^^^^^^^^^^^^^^^^^

File: ``frame_insert.html``

This template represents the top-level frame that is inserted to render the replay in framed mode.

By design, this template does *not* extend from the base template.

This template is responsible for creating the iframe that will render the content.

This template only renders the banner and is designed *not* to set the encoding to allow the browser to 'detect' the encoding for the containing iframe.
For this reason, the template should only contain ASCII text, and %-encode any non-ASCII characters.

Content such as analytics code that is desired in the top frame of framed replay pages should be added to this template.

Template variables:

* ``{{ url }}`` - the URL being replayed.

* ``{{ timestamp }}`` - the timestamp being replayed, e.g. ``20211226`` in ``http://localhost:8080/pywb/20211226/mp_/https://example.com/``

* ``{{ wb_url }}`` - A complete ``WbUrl`` object, which contains the ``url``, ``timestamp`` and ``mod`` properties, representing the replay url.

* ``{{ wb_prefix }}`` - the collection prefix, e.g. ``http://localhost:8080/pywb/``

* ``{{ is_proxy }}`` - set to true if page is being loaded via an HTTP/S proxy (checks if WSGI env has ``wsgiprox.proxy_host`` set)

* ``{{ ui }}`` - an optional ``ui`` dictionary from ``config.yaml``, if any.


.. _custom-top-frame:

Customizing the Top Frame Template
""""""""""""""""""""""""""""""""""

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
use the following script in the outer frame html:

.. code-block:: javascript

  window.addEventListener("message", function(event) {
    if (event.data.wb_type == "load" || event.data.wb_type == "replace-url") {
      console.log("New Url: " + event.data.url);
      console.log("New Timestamp: " + event.data.ts);
    }
  });

The ``load`` message is sent when a new page is first loaded, while ``replace-url`` is used
for url changes caused by content frame History navigation.


Error Templates
---------------

The following templates are used to render errors.


Page Not Found Template
^^^^^^^^^^^^^^^^^^^^^^^

File: ``not_found.html`` - template for 404 error pages.

This template is used to render any 404/page not found errors that can occur when loading a URL that is not in the web archive.

Template variables:

* ``{{ url }}`` - the URL of the page

* ``{{ wbrequest }}`` - the full ``WbRequest`` object which can be used to get additional info about the request.


(The default template checks ``{{ wbrequest and wbrequest.env.pywb_proxy_magic }}`` to determine if the request is via an :ref:`https-proxy` connection or a regular request).


Generic Error Template
^^^^^^^^^^^^^^^^^^^^^^

File: ``error.html`` - generic error template.


This template is used to render all other errors that are not 'page not found'.

Template variables:

*  ``{{ err_msg }}`` - a shorter error message indicating what went wrong.

*  ``{{ err_details }}`` - additional details about the error.




.. _shared-template-vars:

Shared Template Variables
-------------------------

The following template variables are available to all templates.

* ``{{ env }}`` - contains environment variables passed to pywb.

* ``{{ env.pywb_proxy_magic }}`` - if set, indicates pywb is accessed via proxy. See :ref:`https-proxy`

* ``{{ static_prefix }}`` - URL path to use for loading static files.


UI Configuration
^^^^^^^^^^^^^^^^

Starting with pywb 2.7.0, the ``ui`` block in ``config.yaml`` can contain any custom ui-specific settings.

This block is provided to the ``search.html``, ``query.html`` and ``banner.html`` templates.


Localization Globals
^^^^^^^^^^^^^^^^^^^^

The Localization system (see: :ref:`localization`) adds several additional template globals, to facilitate listing available locales and getting URLs to switch locales, including:

* ``{{ _Q() }}`` - a function used to mark certain text for localization, e.g. ``{{ _Q('localize this text') }}``

* ``{{ env.pywb_lang }}`` - indicates current locale language code used for localization.

* ``{{ locales }}`` - a list of all available locale language codes, used for iterating over all locales.

* ``{{ get_locale_prefixes() }}`` - a function which returns the prefixes to use to switch locales.

* ``{{ switch_locale() }}`` - a function used to render a URL to switch locale for the current page. Ex: ``<a href="{{ switch_locale(locale) }}">{{ locale }}</a>`` renders a link to switch to a specific locale.

