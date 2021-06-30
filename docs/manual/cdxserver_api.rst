.. _cdx-server-api:


CDXJ Server API
===============

The following is a reference of the api for querying and filtering archived resources.

The api can be used to get information about a range of archive captures/mementos, including
filtering, sorting, and pagination for bulk query.

The actual archive files (WARC/ARC) files are not loaded during this query, only the generated CDXJ index. 

The :ref:`warcserver` component uses this same api internally to perform all index and resource lookups in a consistent way.


For example, the following query might return the first 10 results from host ``http://example.com/*`` where the mime type is text/html::

  http://localhost:8080/coll/cdx?url=http://example.com/*&page=1&filter=mime:text/html&limit=10


By default, the api endpoint is available at ``/<coll>/cdx`` for a collection named ``<coll>``.

The setting can be changed by setting ``cdx_api_endpoint`` in ``config.yaml``.

For example, to change to ``cdx_api_endpoint: -index`` to use ``/<coll>-index`` as the endpoint (previous default for older version of pywb).

To disable CDXJ access altogether, set ``cdx_api_endpoint: ''`` 


API Reference
-------------


``url``
^^^^^^^

| The only required parameter to the cdx server api is the url, ex:
| ``http://localhost:8080/coll/cdx?url=example.com``

will return a list of captures for ‘example.com’ in the collection
``coll`` (see above regarding per-collection api endpoints).


``from, to``
^^^^^^^^^^^^

Setting ``from=<ts>`` or ``to=<ts>`` will restrict the results to the
given date/time range (inclusive).

Timestamps may be <=14 digits and will be padded to either lower or
upper bound.

| For example, ``...?url=example.com&from=2014&to=2014`` will
  return results of ``example.com`` that
| have a timestamp between ``20140101000000`` and ``20141231235959``


``matchType``
^^^^^^^^^^^^^

The cdx server supports the following ``matchType``

-  ``exact`` – default setting, will return captures that match the url
   exactly

-  ``prefix`` – return captures that begin with a specified path, eg:
   ``http://example.com/path/*``

-  ``host`` – return captures which for a begin host (the path segment
   is ignored if specified)

-  ``domain`` – return captures for the current host and all subdomains,
   eg. ``*.example.com``

As a shortcut, instead of specifying a separate ``matchType`` parameter,
wildcards may be used in the url:

-  ``...?url=http://example.com/path/*`` is equivalent to
   ``...?url=http://example.com/path/&matchType=prefix``

-  ``...?url=*.example.com`` is equivalent to
   ``...?url=example.com&matchType=domain``

*Note: if you are using legacy cdx index files which are not
SURT-ordered, the ``domain`` option will not be available. if this is
the case, you can use the ``wb-manager convert-cdx`` option to easily
convert any cdx to latest format\`*


``limit``
^^^^^^^^^

Setting ``limit=`` will limit the number of index lines returned. Limit
must be set to a positive integer. If no limit is provided, all the
matching lines are returned, which may be slow. (If using a ZipNum
compressed cluster, the page size limit is enforced and no captures are
read beyond the single page. See :ref:pagination-api for more info).


``sort``
^^^^^^^^

The ``sort`` param can be set as follows:

-  ``reverse`` – will sort the matching captures in reverse order. It is
   only recommended for ``exact`` query as reverse a large match may be
   very slow. (An optimized version is planned)

-  ``closest`` – setting this option also requires setting
   ``closest=<ts>`` where ``<ts>`` is a specific timestamp to sort by.
   This option will only work correctly for ``exact`` query and is
   useful for sorting captures based no time distance from a certain
   timestamp. (pywb uses this option internally for replay in order to
   fallback to ‘next closest’ capture if one fails)

Both options may be combined with ``limit`` to return the top N closest,
or the last N results.


``output``
^^^^^^^^^^

This option will toggle the output format of the resulting CDXJ.

* ``output=cdxj`` (default) native format used by pywb, it consists of a space-delimited url timestamp followed by a JSON dictionary (*url timestamp {...}*)

* ``output=json`` will return each line as a proper JSON dictionary, resulting in newline-delimited JSON (NDJSON).

* ``output=link`` will return each line in ``application/link`` format suitable for use as a Memento TimeMap

* ``output=text`` will return each line as fully space-delimited. As the number of fields may vary due to mix of different sources, this format is not recommended and only provided for backward compatibility.


Using ``output=json`` is recommended for extensive analysis and it may become the default option in a future release.


``filter``
^^^^^^^^^^

The ``filter`` param can be specified multiple times to filter by
specific fields in the cdx index. Field names correspond to the fields
returned in the JSON output. Filters can be specified as follows:

-  ``...?url=example.com/*&filter==mime:text/html&filter=!=status:200``
   Return captures from example.com/\* where mime is text/html and http
   status is not 200.
-  ``...?url=example.com&matchType=domain&filter=~url:.*\.php$``
   Return captures from the domain example.com which URL ends in
   ``.php``.

The ``!`` modifier before ``=status`` indicates negation. The ``=`` and
``~`` modifiers are optional and specify exact resp. regular expression
matches. The default (no specific modifier) is to filter whether the
query string is contained in the field value. Negation and exact/regex
modifier may be combined, eg. ``filter=!~text/.*``

The formal syntax is: ``filter=<fieldname>:[!][=|~]<expression>`` with
the following modifiers:

+---------------+-----------------------------+------------------------------------+
| modifier(s)   | example                     | description                        |
+===============+=============================+====================================+
| (no modifier) | ``filter=mime:html``        | field "mime" contains string       |
|               |                             | "html"                             |
+---------------+-----------------------------+------------------------------------+
| ``=``         | ``filter==mime:text/html``  | exact match: field "mime" is       |
|               |                             | "text/html"                        |
+---------------+-----------------------------+------------------------------------+
| ``~``         | ``filter=~mime:.*/html$``   | regex match: expression matches    |
|               |                             | beginning of field “mime” (cf.     |
|               |                             | `re.match`_)                       |
+---------------+-----------------------------+------------------------------------+
| ``!``         | ``filter=!mime:html``       | field “mime” does not contain      |
|               |                             | string “html”                      |
+---------------+-----------------------------+------------------------------------+
| ``!=``        | ``filter=!=mime:text/html`` | field “mime” is not “text/html”    |
|               |                             |                                    |
+---------------+-----------------------------+------------------------------------+
| ``!~``        | ``filter=!~mime:.*/html``   | expression does not match          |
|               |                             | beginning of field “mime”          |
+---------------+-----------------------------+------------------------------------+


``fields``
^^^^^^^^^^

The ``fields`` param can be used to specify which fields to include in the
output. The standard available fields are usually: ``urlkey``,
``timestamp``, ``url``, ``mime``, ``status``, ``digest``, ``length``,
``offset``, ``filename``

If a minimal cdx index is used, the ``mime`` and ``status`` fields may
not be available. Additional fields may be introduced in the future,
especially in the CDX JSON format.

Fields can be comma delimited, for example ``fields=urlkey,timestamp`` will
only include the ``urlkey``, ``timestamp`` and ``filename`` in the
output.

.. _pagination-api:

Pagination API
^^^^^^^^^^^^^^

The cdx server supports an optional pagination api, but it is currently
only available when using :ref:`zipnum` instead of a plain
text cdx files. (Additional pagination support may be added for CDXJ
files as well).

The pagination api supports the following params:

``page``
""""""""

``page`` is the current page number, and defaults to 0 if omitted. If
the ``page`` exceeds the number of available ``pages`` from the page
count query, a 400 error will be returned.

``pageSize``
""""""""""""

| ``pageSize`` is an optional parameter which can increase or decrease
  the amount of data returned in each page.
| The default setting can be configuration dependent.

``showNumPages=true``
"""""""""""""""""""""

This is a special query which, if successful, always returns a JSON
response indicating the size of the full results. The query should be very quick regardless of the
size of the query.

::

    {"blocks": 423, "pages": 85, "pageSize": 5}

In this result:

-  ``pages`` is the total number of pages available for this query. The
   ``page`` parameter may be between 0 and ``pages - 1``

-  ``pageSize`` is the total number of ZipNum compressed blocks that are
   read for each page. The default value can be set in the pywb
   ``config.yaml`` via the ``max_blocks: 5`` option.

-  ``blocks`` is the actual number of compressed blocks that match the
   query. This can be used to quickly estimate the total number of
   captures, within a margin of error. In general,
   ``blocks / pageSize + 1 = pages`` (since there is always at least 1
   page even if ``blocks < pageSize``)

If changing ``pageSize``, the same value should be used for both the
``showNumPages`` query and the regular paged query. ex:

-  Use ``...pageSize=2&showNumPages=true`` and read ``pages`` to get
   total number of pages

-  Use ``...pageSize=2&page=N`` to read the ``N``-th pages from 0 to
   ``pages-1``

``showPagedIndex=true``
"""""""""""""""""""""""

When this param is set, the returned data is the *secondary index*
instead of the actual CDX. Each line represents a compressed cdx block,
and the number of lines returned should correspond to the ``blocks``
value in ``showNumPages`` query. This query is used internally before
reading the actual compressed blocks and should be significantly faster.
At this time, this option can not be combined with other query params
listed in the api, except for ``output=json``. Using ``output=json`` is
recommended with this query as the default text format may change in the
future.


.. _re.match: https://docs.python.org/3/library/re.html#re.match
.. _ZipNum Compressed Index: CDX-Index-Format#zipnum-sharded-cdx
