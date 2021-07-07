.. _rewriter:

Rewriter
========

pywb includes a sophisticated server and client-side rewriting systems, including a rules-based
configuration for domain and content-specific rewriting rules, fuzzy index matching for replay,
and a thorough client-side JS rewriting system.

With pywb 2.3.0, the client-side rewriting system exists in a separate module at ``https://github.com/webrecorder/wombat``


URL Rewriting
-------------

URL rewriting is a key aspect of correctly replaying archived pages.
It is applied to HTML, CSS files, and HTTP headers, as these are loaded directly by the browser.
pywb avoids URL rewriting in JavaScript, to allow that to be handled by the client.

(No url rewriting is performed when running in :ref:`https-proxy` mode)

Most of the rewriting performed is **url-rewriting**, changing the original URLs to point to
the pywb server instead of the live web. Typically, the rewriting converts:

``<url>`` -> ``<pywb host>/<coll>/<timestamp><modifier>/<url>``

For example, the ``http://example.com/`` might be
rewritten as ``http://localhost:8080/my-coll/2017mp_/http://example.com/``

The rewritten url 'prefixes' the pywb host, the collection, requested datetime (timestamp) and type modifier
to the actual url. The result is an 'archival url' which contains the original url and additional information about the archive and timestamp.

.. _urlrewrite_type_mod:

Url Rewrite Type Modifier
~~~~~~~~~~~~~~~~~~~~~~~~~

The type modifier included after the timestamp specifies the format of the resource to be loaded.
Currently, pywb supports the following modifiers:


Identity Modifier (``id_``)
"""""""""""""""""""""""""""

When this modifier is used, eg. ``/my-coll/id_/http://example.com/``, no content rewriting is performed
on the response, and the original, un-rewritten content is returned.
This is useful for HTML or other text resources that are normally rewritten when using the default (``mp_`` modifier).

Note that certain HTTP headers (hop-by-hop or cookie related) may still be prefixed with ``X-Orig-Archive-`` as they may affect the transmission,
so original headers are not guaranteed.


No Modifier
"""""""""""

The 'canonical' replay url is one without the modifier and represents the url that a user will see and enter into the browser.

The behavior for the canonical/no modifier archival url is only different if framed replay is used (see :ref:`framed_vs_frameless`)

* If framed replay, this url serves the top level frame
* If frameless replay, this url serves the content and is equivalent to the ``mp_`` modifier.


Main Page Modifier (``mp_``)
""""""""""""""""""""""""""""

This modifier is used to indicate 'main page' content replay, generally HTML pages. Since pywb also checks content type detection, this modifier can
be used for any resources that is being loaded for replay, and generally render it correctly. Binary resources can be rendered with this modifier.

JS and CSS Hint Modifiers (``js_`` and ``cs_``)
"""""""""""""""""""""""""""""""""""""""""""""""

These modifiers are useful to 'hint' for pywb that a certain resource is being treated as a JS or CSS file. This only makes a difference where there is an ambiguity.

For example, if a resource has type ``text/html`` but is loaded in a ``<script>`` tag with the ``js_`` modifier, it will be rewritten as JS instead of as HTML.


Other Modifiers
"""""""""""""""

For compatibility and historical reasons, the pywb HTML parser also adds the following special hints:

* ``im_`` -- hint that this resource is being used as an image.
* ``oe_`` -- hint that this resource is being used as an object or embed
* ``if_`` -- hint that this resource is being used as an iframe
* ``fr_`` -- hint that this resource is being used as an frame

However, these modifiers are essentially treated the same as ``mp_``, deferring to content-type analysis to determine if rewriting is needed.


Configuring Rewriters
---------------------

pywb provides customizable rewriting based on content-type, the available types are configured
in the :py:mod:`pywb.rewrite.default_rewriter`, which specifies rewriter classes per known type,
and mapping of content-types to rewriters.


HTML Rewriting
~~~~~~~~~~~~~~

An HTML parser is used to rewrite HTML attributes and elements. Most rewriting is applied to url
attributes to add the url rewriting prefix and :ref:`urlrewrite_type_mod` based on the HTML tag and attribute.

Inline CSS and JS in HTML is rewritten using CSS and JS specific rewriters.


CSS Rewriting
~~~~~~~~~~~~~

The CSS rewriter rewrites any urls found in ``<style>`` blocks in HTML, as well as any files determined to be css
(based on ``text/css`` content type or ``cs_`` modifier).


JS Rewriting
~~~~~~~~~~~~

The JS rewriter is applied to inline ``<script>`` blocks, or inline attribute js, and any files determine to be javascript (based on content type and ``js_`` modifier).

The default JS rewriter does not rewrite any links. Instead, JS rewriter performs limited regular expression on the following:

* ``postMessage`` calls
* certain ``this`` property accessors
* specific ``location =`` assignment

Then, the entire script block is wrapped in a special code block to be executed client side. The result is that client-side execution of ``location``, ``window``, ``top`` and other top-level objects follows goes through a client-side proxy object. The client-side rewriting is handled by ``wombat.js``

The server-side rewriting is to aid the client-side execution of wrapped code.

For more information, see :py:mod:`pywb.rewrite.regex_rewriters.JSWombatProxyRewriterMixin`


JSONP Rewriting
~~~~~~~~~~~~~~~

A special case of JS rewriting is JSONP rewriting, which is applied if the url and content is determined to be JSONP, to ensure
the JSONP callback matches the expected param.

For example, a requested url might be ``/my-coll/http://example.com?callback=jQuery123`` but the returned content might be:
``jQuery456(...)`` due to fuzzy matching, which matched this inexact response to the requested url.

To ensure the JSONP callback works as expected, the content is rewritten to ``jQuery123(...)`` -> ``jQuery456(...)``

For more information, see :py:mod:`pywb.rewrite.jsonp_rewriter`


DASH and HLS Rewriting
~~~~~~~~~~~~~~~~~~~~~~

To support recording and replaying, adaptive streaming formants (DASH and HLS), pywb can perform special rewriting on the manifests for these formats to remoe all but one possible resolution/format. As a result, the non-deterministic format selection is reduced to a single consistent format.

For more information, see :py:mod:`pywb.rewrite.rewrite_hls` and :py:mod:`pywb.rewrite.rewrite_dash` and the tests in ``pywb/rewrite/test/test_content_rewriter.py``

