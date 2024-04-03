.. _access-control:

Embargo and Access Control
--------------------------

The embargo system allows for date-based rules to block access to captures based on their capture dates.

The access controls system provides additional URL-based rules to allow, block or exclude access to specific URL prefixes or exact URLs.

The embargo and access control rules are configured per collection.

Embargo Settings
================

The embargo system allows restricting access to all URLs within a collection based on the timestamp of each URL.
Access to these resources is 'embargoed' until the date range is adjusted or the time interval passes.

The embargo can be used to disallow access to captures based on following criteria:

- Captures before an exact date
- Captures after an exact date
- Captures newer than a time interval
- Captures older than a time interval

Embargo Before/After Exact Date
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To block access to all captures before or after a specific date, use the ``before`` or ``after`` embargo blocks
with a specific timestamp.

For example, the following blocks access to all URLs captured before 2020-12-26 in the collection ``embargo-before``::

  embargo-before:
      index_paths: ...
      archive_paths: ...
      embargo:
          before: '20201226'


The following blocks access to all URLs captured on or after 2020-12-26 in collection ``embargo-after``::

  embargo-after:
      index_paths: ...
      archive_paths: ...
      embargo:
          after: '20201226'

Embargo By Time Interval
^^^^^^^^^^^^^^^^^^^^^^^^

The embargo can also be set for a relative time interval, consisting of years, months, weeks and/or days.


For example, the following blocks access to all URLs newer than 1 year::

  embargo-newer:
      ...
      embargo:
          newer:
            years: 1



The following blocks access to all URLs older than 1 year, 2 months, 3 weeks and 4 days::

  embargo-older:
      ...
      embargo:
          older:
            years: 1
            months: 2
            weeks: 3
            days: 4


Any combination of years, months, weeks and days can be used (as long as at least one is provided) for the ``newer`` or ``older`` embargo settings.


Access Control Settings
=======================

Access Control Files (.aclj)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

URL-based access controls are set in one or more access control JSON files (.aclj), sorted in reverse alphabetical order.
To determine the best match, a binary search is used (similar to CDXJ lookup) and then the best match is found forward.

An .aclj file may look as follows::

  org,httpbin)/anything/something - {"access": "allow", "url": "http://httpbin.org/anything/something"}
  org,httpbin)/anything - {"access": "exclude", "url": "http://httpbin.org/anything"}
  org,httpbin)/ - {"access": "block", "url": "httpbin.org/"}
  com, - {"access": "allow", "url": "com,"}


Each JSON entry contains an ``access`` field and the original ``url`` field that was used to convert to the SURT (if any).

The JSON entry may also contain a ``user`` field, as explained below.

The prefix consists of a SURT key and a ``-`` (currently reserved for a timestamp/date range field to be added later).

Given these rules, a user would:

* be allowed to visit ``http://httpbin.org/anything/something`` (allow)
* but would receive an 'access blocked' error message when viewing ``http://httpbin.org/`` (block)
* would receive a 404 not found error when viewing ``http://httpbin.org/anything`` (exclude)

To match any possible URL in an .aclj file, set ``*,`` as the leading SURT, for example::

  *, - {"access": "allow"}

Lines starting with ``*,`` should generally be at the end of the file, respecting the reverse alphabetical order.


Access Types: allow, block, exclude, allow_ignore_embargo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The available access types are as follows:

- ``exclude`` - when matched, results are excluded from the index, as if they do not exist. User will receive a 404.
- ``block`` - when matched, results are not excluded from the index, but access to the actual content is blocked. User will see a 451.
- ``allow`` - full access to the index and the resource, but may be overriden by embargo.
- ``allow_ignore_embargo`` - full access to the index and resource, overriding any embargo settings.

The difference between ``exclude`` and ``block`` is that when blocked, the user can be notified that access is blocked, while
with exclude, no trace of the resource is presented to the user.

The use of ``allow`` is useful to provide access to more specific resources within a broader block/exclude rule, while ``allow_ignore_embargo``
can be used to override any embargo settings.

If both are present, the embargo restrictions are checked first and take precedence, unless the ``allow_ignore_embargo`` option is used
to override the embargo.


User-Based Access Controls
^^^^^^^^^^^^^^^^^^^^^^^^^^

The access control rules can further be customized be specifying different permissions for different 'users'. Since pywb does not have a user system,
a special header, ``X-Pywb-ACL-User`` can be used to indicate a specific user.

This setting is designed to allow a more privileged user to access additional content or override an embargo.

For example, the following access control settings restrict access to ``https://example.com/restricted/`` by default, but allow access for the ``staff`` user::

  com,example)/restricted - {"access": "allow", "user": "staff"}
  com,example)/restricted - {"access": "block"}


Combined with the embargo settings, this can also be used to override the embargo for internal organizational users, while keeping the embargo for general access::

  com,example)/restricted - {"access": "allow_ignore_embargo", "user": "staff"}
  com,example)/restricted - {"access": "allow"}

To make this work, pywb must be running behind an Apache or Nginx system that is configured to set ``X-Pywb-ACL-User: staff`` based on certain settings.

For example, this header may be set based on IP range, or based on password authentication.

To allow a user access to all URLs, overriding more specific rules and the ``default_access`` configuration setting, use the ``*,`` SURT::

  *, - {"access": "allow", "user": "staff"}

Further examples of how to set this header will be provided in the deployments section.

**Note: Do not use the user-based rules without configuring proper authentication on an Apache or Nginx frontend to set or remove this header, otherwise the 'X-Pywb-ACL-User' can easily be faked.**

See the :ref:`config-acl-header` section in Usage for examples on how to configure this header.


Access Error Messages
^^^^^^^^^^^^^^^^^^^^^

The special error code 451 is used to indicate that a resource has been blocked (access setting ``block``).

The `error.html <https://github.com/webrecorder/pywb/blob/master/pywb/templates/error.html>`_ template contains a special message for this access and can be customized further.

By design, resources that are ``exclude``-ed simply appear as 404 not found and no special error is provided.


Managing Access Lists via Command-Line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The .aclj files need not ever be added or edited manually.

The pywb ``wb-manager`` utility has been extended to provide tools for adding, removing and checking access control rules.

The access rules are written to ``<collection>/acl/access-rules.aclj`` for a given collection ``<collection>`` for automatic collections.

For example, to add the first line to an ACL file ``access.aclj``, one could run::

  wb-manager acl add <collection> http://httpbin.org/anything/something exclude


The URL supplied can be a URL or a SURT prefix. If a SURT is supplied, it is used as is::

  wb-manager acl add <collection> com, allow


A specific user for user-based rules can also be specified, for example to add ``allow_ignore_embargo`` for user ``staff`` only, run::

  wb-manager acl add <collection> http://httpbin.org/anything/something allow_ignore_embargo -u staff


By default, access control rules apply to a prefix of a given URL or SURT.

To have the rule apply only to the exact match, use::

  wb-manager acl add <collection> http://httpbin.org/anything/something allow --exact-match

Rules added with and without the ``--exact-match`` flag are considered distinct rules, and can be added
and removed separately.

With the above rules, ``http://httpbin.org/anything/something`` would be allowed, but
``http://httpbin.org/anything/something/subpath`` would be excluded for any ``subpath``.

To remove a rule, one can run::

  wb-manager acl remove <collection> http://httpbin.org/anything/something

To import rules in bulk, such as from an OpenWayback-style excludes.txt and mark them as ``exclude``::

  wb-manager acl importtxt <collection> ./excludes.txt exclude


See ``wb-manager acl -h`` for a list of additional commands such as for validating rules files and running a match against
an existing rule set.



Access Controls for Custom Collections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For manually configured collections, there are additional options for configuring access controls.
The access control files can be specified explicitly using the ``acl_paths`` key and allow specifying multiple ACL files,
and allow sharing access control files between different collections.

Single ACLJ::

  collections:
       test:
            acl_paths: ./path/to/file.aclj
            default_access: block



Multiple ACLJ::

  collections:
       test:
            acl_paths:
                 - ./path/to/allows.aclj
                 - ./path/to/blocks.aclj
                 - ./path/to/other.aclj
                 - ./path/to/directory

            default_access: block

The ``acl_paths`` can be a single entry or a list, and can also include directories. If a directory is specified, all ``.aclj`` files
in the directory are checked.

When finding the best rule from multiple ``.aclj`` files, each file is binary searched and the result
set merge-sorted to find the best match (very similar to the CDXJ index lookup).

Note: It might make sense to separate ``allows.aclj`` and ``blocks.aclj`` into individual files for organizational reasons,
but there is no specific need to keep more than one access control file.

Finally, ACLJ and embargo settings combined for the same collection might look as follows::

  collections:
       test:
            ...
            embargo:
                newer:
                    days: 366

            acl_paths:
                 - ./path/to/allows.aclj
                 - ./path/to/blocks.aclj


Default Access
^^^^^^^^^^^^^^

An additional ``default_access`` setting can be added to specify the default rule if no other rules match for custom collections.
If omitted, this setting is ``default_access: allow``, which is usually the desired default.

Setting ``default_access: block`` and providing a list of ``allow`` rules provides a flexible way to allow access
to only a limited set of resources, and block access to anything out of scope by default.


