### pywb.cdx package

This package contains the CDX processing suite of the pywb wayback tool suite.

The CDX Server loads, filters and transforms cdx from multiple sources in response
to a given query.

#### Sample App

A very simple reference WSGI app is included.

Run: `python -m pywb.cdx.wsgi_cdxserver` to start the app, keyboard interrupt to stop.

The default [config.yaml](config.yaml) points to the sample data directory
and uses port 8080.

The domain specific [rules.yaml](rules.yaml) are also loaded.

#### CDX Server API Reference

Goal is to provide compatiblity with this feature set and more:
https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server

TODO




