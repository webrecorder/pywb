.. _ui-customizations:

Customization Guide
===================

Most aspects of the pywb user-interface can be customized by changing the default styles, or overriding the HTML templates.

This guide covers a few different options for customizing the UI.


New Vue-based UI
----------------

With pywb 2.7.0, pywb includes a brand new UI which includes a visual calendar mode and a histogram-based banner.

See :ref:`vue-ui` for more information on how to enable this UI.


Customizing UI Templates
------------------------

pywb renders HTML using the Jinja2 templating engine, loading default templates from the ``pywb/templates`` directory.

If running from a custom directory, templates can be placed in the ``templates`` directory and will override the defaults.

See :ref:`template-guide` for more details on customizing the templates.


Static Files
------------

pywb will automatically support static files placed under the following directories:

* Files under the root ``static`` directory: ``static/my-file.js`` can be accessed via ``http://localhost:8080/static/my-file.js``


* Files under the per-collection directory: ``./collections/my-coll/static/my-file.js`` can be accessed via ``http://localhost:8080/static/_/my-coll/my-file.js``


It is possible to change these settings via ``config.yaml``:

* ``static_prefix`` - sets the URL path used in pywb to serve static content (default ``static``)

* ``static_dir`` - sets the directory name used to read static files on disk (default ``static``)

While pywb can serve static files, it is recommended to use an existing web server to serve static files, especially if already using it in production.

For example, this can be done via nginx with:


.. code:: text

    location /wayback/static {
        alias /pywb/pywb/static;
    }


Loading Custom Metadata
-----------------------

pywb includes a default mechanism for loading externally defined metadata, loaded from a per-collection ``metadata.yaml`` YAML file at runtime.

See :ref:`custom-metadata` for more details.

Additionally, the banner template has access to the contents of the ``config.yaml`` via the ``{{ config }}`` template variable,
allowing for passing in arbitrary config information.

For more dynamic loading of data, the banner and all of the templates can load additional data via JS ``fetch()`` calls.


Embedding pywb in frames
------------------------

It should be possible to embed pywb replay itself as an iframe as needed.

For customizing the top-level page and banner, see :ref:`custom-top-frame`.

However, there may be other reasons to embed pywb in an iframe.

This can be done simply by including something like:

.. code:: html

   <html>
     <head>
       <body>
         <div>Embedding pywb replay</div>
         <iframe style="width: 100%; height: 100%" src="http://localhost:8080/pywb/20130729195151/http://test@example.com/"></iframe>
      </body>
   </html>

