Deploying pywb: Collection Paths and routing with Nginx/Apache
======================================================

In pywb, the collection name is also the access point, and each of the collections in ``config.yaml``
can be accessed by their name as the subpath:

.. code:: yaml

      collections:
        wayback:
            ...

        another-collection:
            ...

If pywb is deployed on port 8080, each collection will be available under:
``http://<hostname>/wayback/*/https://example.com/`` and ``http://<hostname>/another-collection/*/https://example.com/``

To make a collection available under the root, simply set its name to: ``$root``


.. code:: yaml

      collections:
        $root:
            ...

        another-collection:
            ...


Now, the first collection is available at: ``http://<hostname>/*/https://example.com/``.


To deploy pywb on a subdirectory, eg. ``http://<hostname>/pywb/another-collection/*/https://example.com/``,

and in general, for production use, it is recommended to deploy pywb behind an Nginx or Apache reverse proxy.


Nginx and Apache Reverse Proxy
------------------------------

The recommended deployment for pywb is with uWSGI and behind an Nginx or Apache frontend.

This configuration allows for more robust deployment, and allowing these servers to handle static files.


See the :ref:`nginx-deploy` and :ref:`apache-deploy` sections for more info on deploying with Nginx and Apache.


Working Docker Compose Examples
-------------------------------

The pywb `Deployment Examples <https://github.com/webrecorder/pywb/blob/main/sample-deploy/>`_ include working examples of deploying pywb with Nginx, Apache and OutbackCDX
in Docker using Docker Compose, widely available container orchestration tools.

See `Installing Docker <https://docs.docker.com/get-docker/>`_ and `Installing Docker Compose <https://docs.docker.com/compose/install/>`_ for instructions on how to install these tools.

The examples are available in the ``sample-deploy`` directory of the pywb repo. The examples include:

 - ``docker-compose-outback.yaml`` -- Docker Compose config to start OutbackCDX and pywb, and ingest sample data into OutbackCDX
 - ``docker-compose-nginx.yaml`` -- Docker Compose config to launch pywb and latest Nginx, with pywb running on subdirectory ``/wayback`` and Nginx serving static files from pywb.
 - ``docker-compose-apache.yaml`` -- Docker Compose config to launch pywb and latest Apache, with pywb running on subdirectory ``/wayback`` and Apache serving static files from pywb.


The examples are designed to be run one at a time, and assume port 8080 is available.

After installing Docker and Docker Compose, run either of:

- ``docker-compose -f docker-compose-outback.yaml up``
- ``docker-compose -f docker-compose-nginx.yaml up``
- ``docker-compose -f docker-compose-apache.yaml up``

This will download the standard Docker images and start all of the components in Docker.

If everything works correctly, you should be able to access: ``http://localhost:8080/pywb/https://example.com/`` to view the sample pywb collection.

Press CTRL+C to interrupt and stop the example in the console.


