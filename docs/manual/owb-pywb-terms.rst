OpenWayback vs pywb Terms
=========================

pywb and OpenWayback use slightly different terms to describe the configuration options, as explained below.

Some differences are:
  - The ``wayback.xml`` config file in OpenWayback is replaced with ``config.yaml`` yaml
  - The terms ``Access Point`` and ``Wayback Collection`` are replaced with ``Collection`` in pywb. The collection configuration represents a unique path (access point) and the data that is accessed at that path.
  - The ``Resource Store`` in OpenWayback is known in pywb as the archive paths, configured under ``archive_paths``
  - The ``Resource Index`` in OpenWayback is known in pywb as the index paths, configurable under ``index_paths``
  - The ``Exclusions`` in OpenWayback are replaced with general :ref:`access-control`



Pywb Collection Basics
----------------------

A pywb collection must consist of a minimum of three parts: the collection name, the ``index_paths`` (where to read the index), and the ``archive_paths`` (where to read the WARC files).

The collection is accessed by name, so there is no distinct access point.

The collections are configured in the ``config.yaml`` under the ``collections`` key:

For example, a basic collection definition can be specified via:

.. code:: yaml

    collections:
        wayback:
            index_paths: /archive/cdx/
            archive_paths: /archive/storage/warcs/


Pywb also supports a convention-based directory structure. Collections created in this structure can be detected automatically
and need not be specified in the ``config.yaml``. This structure is designed for smaller collections that are all stored locally in a subdirectory.

See the :ref:`dir_structure` for the default pywb directory structure.

However, for importing existing collections from OpenWayback, it is probably easier to specify the existing paths as shown above.



