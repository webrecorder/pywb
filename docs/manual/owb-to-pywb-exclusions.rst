Migrating Exclusion Rules
=========================

pywb includes a new :ref:`access-control` system, which allows granual allow/block/exclude access control rules on paths and subpaths.

The rules are configured in .aclj files, and a command-line utility exists to import OpenWayback exclusions
into the pywb ACLJ format.

For example, given an OpenWayback exclusion list configuration for a static file:

.. code:: xml

    <bean id="excluder-factory-static" class="org.archive.wayback.accesscontrol.staticmap.StaticMapExclusionFilterFactory">
      <property name="file" value="/archive/exclusions.txt"/>
      <property name="checkInterval" value="600000" />
    </bean>


The exclusions file can be converted to an .aclj file by running: ::

  wb-manager acl importtxt /archive/exclusions.aclj /archive/exclusions.txt exclude


Then, in the pywb config, specify:

.. code:: yaml

    collections:
        wayback:
            index_paths: ...
            archive_paths: ...
            acl_paths: /archive/exclusions.aclj


It is possible to specify multiple access control files, which will all be applied.

Using ``block`` instead of ``exclude`` will result in pywb returning a 451 error, indicating that URLs are in the index but blocked.


CLI Tool
--------

After exclusions have been imported, it is recommended to use ``wb-manager acl`` command-line tool for managing exclusions:


To add an exclusion, run: ::

  wb-manager acl add /archive/exclusions.aclj http://httpbin.org/anything/something exclude

To remove an exclusion, run: ::

  wb-manager acl remove /archive/exclusions.aclj http://httpbin.org/anything/something


For more options, see the full :ref:`access-control` documentation or run ``wb-manager acl --help``.


Not Yet Supported
-----------------

Some OpenWayback exclusion options are not yet supported in pywb.
The following is not yet supported in the access control system:

- Exclusions/Access Control By specific date range
- Regex based exclusions
- Date Range Embargo on All URLs
- Robots.txt-based exclusions

