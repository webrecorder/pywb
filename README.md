PyWb 0.1 Beta
==============

[![Build Status](https://travis-ci.org/ikreymer/pywb.png?branch=master)](https://travis-ci.org/ikreymer/pywb)

pywb is a Python re-implementation of the Wayback Machine software.

The goal is to provide a brand new, clean implementation of Wayback.

This involves playing back archival web content (usually in WARC or ARC files) as best or accurately
as possible, in straightforward by highly customizable way.

It should be easy to deploy and hack!


### Wayback Machine

A typical Wayback Machine serves archival content in the following form:

`http://<host>/<collection>/<timestamp>/<original url>`


Ex: The [Internet Archive Wayback Machine][1] has urls of the form:

`http://web.archive.org/web/20131015120316/http://archive.org/`


A listing of archived content, often in calendar form, is available when a `*` is used instead of timestamp.

pywb uses this interface as a starting point.


### Requirements

pywb currently works best with 2.7.x
It should run in a standard WSGI container, although currently
tested primarily with uWSGI 1.9 and 2.0

Support for other versions of Python 3 is planned.


### Installation

pywb comes with sample archived content, also used
for unit testing the app.

The data can be found in `sample_archive` and contains
`warc` and `cdx` files. The sample archive contains
recent captures from `http://example.com` and `http://iana.org`


To start a pywb with sample data

- Clone this repo

- Install with `python setup.py install`

- Run pywb by via script `run.sh`

- Test following pages in a browser:

A recent captures of these sites is included in the sample_archive:

* [http://localhost:8080/pywb/example.com](http://localhost:8080/pywb/example.com)

* [http://localhost:8080/pywb/iana.org](http://localhost:8080/pywb/iana.org)

Capture Listings:

* [http://localhost:8080/pywb/*/example.com](http://localhost:8080/pywb/*/example.com)

* [http://localhost:8080/pywb/*/iana.org](http://localhost:8080/pywb/*/iana.org)



### Sample Setup

pywb is currently configurable via yaml.

The simplest [config.yaml](config.yaml) is roughly as follows:

``` yaml

routes:
    - name: pywb

     index_paths:
          - ./sample_archive/cdx/

     archive_paths:
          - ./sample_archive/warcs/

     head_insert_html_template: ./ui/head_insert.html

     calendar_html_template: ./ui/query.html


hostpaths: ['http://localhost:8080/']

```


(Refer to [full version of config.yaml](config.yaml) for additional documentation)




* The `PYWB_CONFIG` env can be used to set a different file.

* The `PYWB_CONFIG_MODULE` env variable can be used to set a different init module

See `run.sh` for more details


### Running with Existing CDX/WARCs

If you have existing warc and cdx files, you can adjust the `index_paths` and `archive_paths` to point to
the location of those files.

#### SURT

By default, pywb expects the cdx files to be Sort-Friendly-Url-Transform (SURT) ordering. This is an ordering
that transforms: `example.com` -> `com,example)/` to faciliate better search. It is recommended for future indexing.

However, non-SURT ordered cdx indexs will work as well, but be sure to specify

`surt_ordered: False` in the [config.yaml](config.yaml)


### Generating new CDX

TODO







  [1]: https://archive.org/web/
