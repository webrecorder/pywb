## PyWb Warc v0.2

[![Build Status](https://travis-ci.org/ikreymer/pywb_warc.png?branch=master)](https://travis-ci.org/ikreymer/pywb_warc)

This is the WARC/ARC record loading component of pywb wayback tool suite.


This package provides the following facilities:

* Resolve relative WARC/ARC filenames to a full path based on configurable resolvers

* Resolve 'revisit' records from provided index to find a full record with headers and payload content

* Load WARC and ARC records either locally or via http using http 1.1 range requests


### Tests

This package will include a test suite for different WARC and ARC loading formats.

To run: `python run-tests.py`

