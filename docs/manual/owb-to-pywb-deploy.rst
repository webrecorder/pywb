Deploying pywb: Path Prefix and Nginx/Apache
============================================

In pywb, the collection name is also the access point and each the collections in ``config.yaml``
can be accessed by their name as the subpath:

.. code:: yaml

      collections:
        wayback:
            ...

        another-collection:
            ...

If pywb is deployedon port 8080, each collection will be available under:
``http://<hostname>/wayback/*/https://example.com/`` and ``http://<hostname>/another-collection/*/https://example.com/``

To make a collection available under the root, simply set its name to: ``$root``


.. code:: yaml

      collections:
        $root:
            ...

        another-collection:
            ...


Now, the first collection from: ``http://<hostname>/*/https://example.com/``


Nginx and Apache Reverse Proxy
------------------------------

The recommended deployment for pywb is with uWSGI and behind an Nginx or Apache frontend.

This configuration allows for more robust deployment, and allowing these servers to handle static files.

Running behind Nginx or Apache also allows for configuring pywb to run on a specific subpath, by setting the ``SCRIPT_NAME`` parameter.

To serve pywb from ``http://<hostname>/prefix/to/pywb/``,

For Nginx, set: ::

  uwsgi_param SCRIPT_NAME prefix/to/pywb/;

For Apache, set: ::

  SetEnv SCRIPT_NAME prefix/to/pywb/


See the :ref:`deployment` section for more detailed examples of Nginx and Apache configurations.


