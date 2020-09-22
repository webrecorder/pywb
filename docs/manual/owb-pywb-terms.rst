OpenWayback vs pywb Terms
=========================

pywb and OpenWayback use slightly different terms to describe the configuration options, as explained below.

Some differences are:
  - The ``wayback.xml`` config file in OpenWayback is replaced with ``config.yaml`` yaml
  - The terms ``Access Point`` and ``Wayback Collection`` are replaced with ``Collection`` in pywb. The collection configuration represents a unique path (access point) and the data that is accessed at that path.
  - The ``Resource Store`` in OpenWayback is known as the archive paths, configured under ``archive_paths``
  - The ``Resource Index`` in OpenWayback is known as the index paths, configurable under ``index_paths``
  - The ``Exclusions`` in OpenWayback are replaced with general :ref:`access-control`


See the :ref:`dir_structure` for the default pywb directory structure.


