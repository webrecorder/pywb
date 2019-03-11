.. _memento-api:

Memento API
===========

pywb supports the Memento Protocol as specified in `RFC 7089 <https://tools.ietf.org/html/rfc7089>`_ and provides API endpoints
for Memento TimeMaps and TimeGates per collection.

Memento support is enabled by default and can be controlled via the ``enable_memento: true|false`` setting in the ``config.yaml``


TimeMap API
-----------

The timemap API is available at ``/<coll>/timemap/<type>/<url>`` for any pywb collection ``<coll>`` and ``<url>`` in the collection.

The timemap (URI-T) can be provided in several output formats, as specified by the ``<type>`` param:

* ``link`` -- returns an ``application/link-format`` as required by the `Memento spec <https://tools.ietf.org/html/rfc7089#section-5>`_
* ``cdxj`` -- returns a timemap in the native CDXJ format.
* ``json`` -- returns the timemap as newline-delimited JSON lines (NDJSON) format.


Although not required by the Memento spec, the Link output produced by timemap also includes the extra ``collection=`` field, specifying
the collection of each url. This is especially useful when accessing the timemap for the special :ref:`auto-all` to view a timemap across
multiple collections in a single response.


The Timemap API is implemented as a subset of the :ref:`cdx-server-api` and should produce the same result as the equivalent CDX server query.

For example, the timemap query:
``http://localhost:8080/pywb/timemap/link/http://example.com/`` is equivalent to the CDX server query:
``http://localhost:8080/pywb/cdx?url=http://example.com/&output=link``


TimeGate API
------------

The TimeGate API for any pywb collection is ``/<coll>/<url>``, eg. ``/my-coll/http://example.com/``

The timegate can either be a non-redirecting timegate (URI-M, 200-style negotiation) and return a URI-M response, or a redirecting timegate  (302-style negotiation) and redirect to a URI-M.

.. _memento-no-redirect:

Non-Redirecting TimeGate (Memento Pattern 2.2)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This behavior is consistent with `Memento Pattern 2.2 <https://tools.ietf.org/html/rfc7089#section-4.2.2>`_ and is the default behavior.

To avoid an extra redirect, the TimeGate returns the requested memento directly (200-style negotiation) without redirecting to its canonical, timestamped url.
The 'canonical' URI-M is included in the ``Content-Location`` header and should be used to reference the memento in the future.


(For HTML Mementos, the rewriting system also injects the url and timestamp into the page so that it can be displayed to the user). This behavior optimizes network traffic by avoiding unneeded redirects.


Redirecting TimeGate (Memento Pattern 2.3)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This behavior is consistent with `Memento Pattern 2.3 <https://tools.ietf.org/html/rfc7089#section-4.2.3>`_

To enable this behavior, add ``redirect_to_exact: true`` to the config.

In this mode, the TimeGate always issues a 302 to redirect a request to the "canonical" URI-M memento. The ``Location`` header is always present
with the redirect.

As this approach always includes a redirect, use of this system is discouraged when the intent is to render mementos. However, this approach is useful when the goal is to determine the URI-M and to provide backwards compatibility.


.. _memento-proxy:

Proxy Mode Memento API
^^^^^^^^^^^^^^^^^^^^^^

When running in :ref:`https-proxy`, pywb behaves roughly in accordance with `Memento Pattern 1.3 <https://tools.ietf.org/html/rfc7089#section-4.1.3>`_

Every URI in proxy mode is also a TimeGate, and the ``Accept-Datetime`` header can be used to specify which timestamp to use in proxy mode.
The ``Accept-Datetime`` header overrides any other timestamp setting in proxy mode.

The main distinction from the standard is that the URI-R, the original resource, is not available in proxy mode. (It is simply the URL loaded without the proxy,
which is not possible to specify via the URL alone).


URI-M Headers
-------------

When serving a URI-M (any archived url), the following additional headers are included in accordance with Memento spec:

* ``Link`` header with at least ``original``, ``timegate`` and ``timemap`` relations
* ``Content-Location`` is included if using :ref:`memento-no-redirect` behavior

(Note: the ``Content-Location`` may also be included in case of fuzzy-matching response, where the actual/canonical url is different than requested url due to an inexact match)








