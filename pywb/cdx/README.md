## PyWb CDX v0.2

[![Build Status](https://travis-ci.org/ikreymer/pywb_cdx.png?branch=master)](https://travis-ci.org/ikreymer/pywb_cdx)


This package contains the CDX processing suite of the pywb wayback tool suite.

The CDX Server loads, filters and transforms cdx from multiple sources in response
to a given query.

### Installation and Tests

`pip install -r requirements` -- to install

`python run-tests.py` -- to run all tests


### Sample App

A very simple reference WSGI app is included.

Run: `python -m pywb_cdx.wsgi_cdxserver` to start the app, keyboard interrupt to stop.

The default [config.yaml](pywb_cdx/config.yaml) points to the sample data directory
and uses port 8080

### CDX Server API Reference

Goal is to provide compatiblity with this feature set and more:
https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server

TODO




