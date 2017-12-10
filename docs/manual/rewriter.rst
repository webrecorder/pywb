Rewriter
========

pywb includes a sophisticated server and client-side rewriting systems, including a rules-based
configuration for domain and content-specific rewriting rules, fuzzy index matching for replay,
and a thorough client-side JS rewriting system.


URL Rewriting
-------------

Most of the rewriting performed is **url-rewriting**, changing the original URLs to point to
the pywb server instead of the live web. For example, a url to ``http://example.com/`` might be
rewritten as ``http://localhost:8080/my-coll/2017mp_/http://example.com/``

URL rewriting is applied to HTML, CSS files, and HTTP headers, as these are loaded directly by the browser.
pywb avoids URL rewriting in JavaScript, to allow that to be handled by the client.

(No url rewriting is performed when running in :ref:`https-proxy` mode)


Configuring Rewriters
---------------------

pywb provides customizeable rewriting based on content-type, the available types are configured
in the :py:mod:``pywb.rewriter.default_rewriter``, which specifies rewriter classes per known type,
and mapping of content-types to rewriters.


HTML Rewriting
~~~~~~~~~~~~~~

An HTML parser is used to rewrite HTML attributes and elements. Most rewriting is applied to url
attributes to add the url rewriting prefix. The CSS and JS in HTML is rewritten using the CS and JSS
rewriters.

CSS Rewriting
~~~~~~~~~~~~~

The CSS rewriter rewrites any urls found in CSS files or ``<style>`` blocks in HTML.


