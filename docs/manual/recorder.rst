.. _recorder:

Recorder
========

The recorder component acts a proxy component, intercepting requests to and response from the :ref:`warcserver` and recording them
to a WARC file on disk.

The recorder uses the :class:`pywb.recorder.multifilewarcwriter.MultiFileWARCWriter` which extends the base :class:`warcio.warcwriter.WARCWriter` from :mod:`warcio` and provides support for:

* appending to multiple WARC files at once

* WARC 'rollover' based on maximum size idle time

* indexing (CDXJ) on write


Many of the features of the Recorder are created for use with Webrecorder project, although the core recorder is used to provide
a basic recording via ``/record/`` endpoint. (See: :ref:`recording-mode`)


Deduplication Filters
---------------------

The core recorder class provides for optional deduplication using the :class:`pywb.recorder.redisindexer.WritableRedisIndexer` class which requires Redis to store the index, and can be used to either:

* write duplicates responses.

* write ``revisit`` records.

* ignore duplicates and don't write to WARC.


Custom Filtering
----------------

The recorder filter system also includes a filtering system to allow for not writing certain requests and responses.
Filters include:

* Skipping by regex applied to source (``Warcserver-Source-Coll`` header from Warcserver)

* Skipping if ``Recorder-Skip: 1`` header is provided

* Skipping if ``Range`` request header is provided

* Filtering out certain HTTP headers, for example, http-only cookies

The additional recorder functionality will be enhanced in a future version.

For a more detailed examples, please consult the tests in :mod:`pywb.recorder.test.test_recorder`



