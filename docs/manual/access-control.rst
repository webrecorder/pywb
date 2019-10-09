.. _access-control:

Access Control System
---------------------

The access controls system allows for a flexible configuration of rules to allow,
block or exclude access to individual urls by longest-prefix match.

Access Control Files (.aclj)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Access controls are set in one or more access control json files (.aclj), sorted in reverse alphabetical order.
To determine the best match, a binary search is used (similar to CDXJ) lookup and then the best match is found forward.

An .aclj file may look as follows::

  org,httpbin)/anything/something - {"access": "allow", "url": "http://httpbin.org/anything/something"}
  org,httpbin)/anything - {"access": "exclude", "url": "http://httpbin.org/anything"}
  org,httpbin)/ - {"access": "block", "url": "httpbin.org/"}
  com, - {"access": "allow", "url": "com,"}


Each JSON entry contains an ``access`` field and the original ``url`` field that was used to convert to the SURT (if any).

The prefix consists of a SURT key and a ``-`` (currently reserved for a timestamp/date range field to be added later)

Given these rules, a user would:
* be allowed to visit ``http://httpbin.org/anything/something`` (allow)
* but would receive an 'access blocked' error message when viewing ``http://httpbin.org/`` (block)
* would receive a 404 not found error when viewing ``http://httpbin.org/anything`` (exclude)

Default .aclj files
^^^^^^^^^^^^^^^^^^^

A default set of access control files is provided in the ``./aclj directory``

These are in use with the default ``config.yaml``


Access Types: allow, block, exclude
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The available access types are as follows:

- ``exclude`` - when matched, results are excluded from the index, as if they do not exist. User will receive a 404.
- ``block`` - when matched, results are not excluded from the index, marked with ``access: block``, but access to the actual is blocked. User will see a 451
- ``allow`` - full access to the index and the resource.

The difference between ``exclude`` and ``block`` is that when blocked, the user can be notified that access is blocked, while
with exclude, no trace of the resource is presented to the user.

The use of ``allow`` is useful to provide access to more specific resources within a broader block/exclude rule.


Managing Access Lists
^^^^^^^^^^^^^^^^^^^^^

The .aclj files need not ever be edited manually by the user.

The pywb ``wb-manager`` utility has been extended to provide tools for adding, removing and checking access control rules.

For example, to add the first line to an ACL file ``access.aclj``, one could run::

  wb-manager acl add ./access.aclj http://httpbin.org/anything/something exclude


The URL supplied can be a URL or a SURT prefix. If a SURT is supplied, it is used as is::

  wb-manager acl add ./access.aclj com, allow


To remove a rule, one can run::

  wb-manager acl remove ./access.aclj http://httpbin.org/anything/something


To import rules in bulk, such as from an OpenWayback-style excludes.txt and mark them as ``exclude``::

  wb-manager acl importtxt ./accessl.aclj ./excludes.txt exclude


See ``wb-manager acl -h`` for a list of additional commands such as for validating rules files and running a match against
an existing rule set.

Configuring Access Controls
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For manually configured collections, access controls can be specified explicitly using the ``acl_paths`` key:

Single ACLJ::

  collections:
       ukwa:
            acl_paths: ./path/to/file.aclj
            default_access: block



Multiple ACLJ::

  collections:
       ukwa:
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
but there is no difference for the system and no specific need to keep different rule types separate.

Default Access
^^^^^^^^^^^^^^

An additional ``default_access`` setting can be added to specify the default rule if no other rules match.
If omitted, this setting is ``default_access: allow``.

Setting ``default_access: block`` and providing a list of ``allow`` rules provides a flexible way to allow access
to only a limited set of resources, and block access to anything out of scope by default.

Access Error Messages
^^^^^^^^^^^^^^^^^^^^^

The special error code 451 is used to indicate that a resource has been blocked (access setting ``block``)

The [error.html](https://github.com/webrecorder/pywb/blob/master/pywb/templates/error.html) template contains a special message for this access and can be customized further.

By design, resources that are ``exclude``-ed simply appear as 404 not found and no special error is provided.

