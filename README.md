PyWb 0.1 Beta
==============

[![Build Status](https://travis-ci.org/ikreymer/pywb.png?branch=master)](https://travis-ci.org/ikreymer/pywb)

pywb is a Python implementation of the Wayback Machine software.

Some goals are to:

* Provide the best possible playback of archival web content (usually in WARC or ARC files)

* Be highly customizable in rewriting content to provide best possible playback experience

* Provide a pluggable, optional ui

* Be easy to deploy and hack



The Wayback Machine usually serves archival content in the following form:

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

- Run Start with `run.sh`

- Set your browser to `localhost:8080/pywb/example.com` or `localhost:8080/pywb/iana.org`
  to see pywb rendering the sample archive data


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



The `PYWB_CONFIG` env can be used to set a different file
The `PYWB_CONFIG_MODULE` env variable can be used to set a different init module
See `run.sh` for more details




  [1]: https://archive.org/web/
