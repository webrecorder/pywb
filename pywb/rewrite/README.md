### pywb.rewrite

This package includes the content rewriting component of the pywb wayback tool suite.

This package applies standard rewriting content rewriting, in the form of url rewriting, for
HTTP headers, html, css, js and xml content.

An additional domain-specific rewritin is planned, especially for JS, to allow for proper
replay of difficult pages.


#### Command-Line Rewriter

To enable easier testing of rewriting, this package includes a command-line rewriter 
which will fetch a live url and apply the registered rewriting rules to that url:

Run:

`python ./pywb.rewrite/rewrite_live.py http://example.com`

To specify custom timestamp and prefix:

```
python ./pywb.rewrite/rewrite_live.py http://example.com /mycoll/20141026000102/http://mysite.example.com/path.html
```

This will print to stdout the content of `http://example.com` with all urls rewritten relative to 
`/mycoll/20141026000102/http://mysite.example.com/path.html`.

Headers are also rewritten, for further details, consult the `get_rewritten` function in
[pywb_rewrite/rewrite_live.py](pywb_rewrite/rewrite_live.py)


#### Tests

Rewriting doctests as well as live rewriting tests (subject to change) are provided.

pywb.rewrite is part of a full test suite that can be executed via
`python run-tests.py`



