### pywb.warc

This is the WARC/ARC record loading component of pywb wayback tool suite.
The package provides the following facilities:

* Resolve relative WARC/ARC filenames to a full path based on configurable resolvers

* Resolve 'revisit' records from provided index to find a full record with headers and payload content

* Load WARC/ARC records either locally or via http using http 1.1 range requests


When loading archived content, the format type (WARC vs ARC) and compressed ARCs/WARCs
are decompressed automatically.
No assumption is made about format based on filename, content type
or other external parameters other than the content itself.

### Tests

This package will includes a test suite for loading a variety of WARC and ARC records.

Tests so far:

* Compressed WARC, ARC Records
* Uncompressed ARC Records
* Compressed WARC created by wget 1.14
* Same Url revisit record resolving


TODO:

* Different url revisit record resolving
