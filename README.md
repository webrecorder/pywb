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

1. Clone this repo

2. Install with `python setup.py install`

3. Run pywb by via script `run.sh`

  The script is very simple and assumes default python install, and default uwsgi install (on Ubuntu and OS X)
 
  May need to be modified to point for a different env)

4. Test pywb in your browser!


pywb is set to run on port 8080 by default.

If everything worked, the following pages should be loading (served from /sample_archive):

| Original Url       | Latest Capture  | List of All Captures    |
| -------------      | -------------   | ----------------------- |         
| `http://example.com` | http://localhost:8080/pywb/example.com | http://localhost:8080/pywb/*/example.com |
| `http://iana.org`    | http://localhost:8080/pywb/iana.org | http://localhost:8080/pywb/*/iana.org |



### Sample Setup

pywb is configurable via yaml.

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

The optional ui elements, the query/calendar and header insert are specifyable via html/Jinja2 templates.


(Refer to [full version of config.yaml](config.yaml) for additional documentation)



For more advanced use, the pywb init path can be customized further:


* The `PYWB_CONFIG` env can be used to set a different yaml file.

* The `PYWB_CONFIG_MODULE` env variable can be used to set a different init module, for implementing a custom init

(or for extensions not yet supported via yaml)


See `run.sh` for more details


### Running with Existing CDX/WARCs

If you have existing .warc/.arc and .cdx files, you can adjust the `index_paths` and `archive_paths` to point to
the location of those files.

#### SURT

By default, pywb expects the cdx files to be Sort-Friendly-Url-Transform (SURT) ordering. 
This is an ordering that transforms: `example.com` -> `com,example)/` to faciliate better search. 
It is recommended for future indexing, but is not required.

Non-SURT ordered cdx indexs will work as well, but be sure to specify:

`surt_ordered: False` in the [config.yaml](config.yaml)


### Creating CDX from WARCs

If you have WARC files without cdxs, the following steps can be taken to create the indexs

cdx indexs are a plain text file sorted format for the contents of one or more WARC/ARC files.

pywb does not currently generate indexs automatically, but this may be added in the future.

For production purposes, it is recommended that the cdx indexs be generated ahead of time.

** Note: these recommendations are subject to change as the external libraries are being cleaned up **

The directions are for running in a shell:


1. Clone https://bitbucket.org/rajbot/warc-tools

2. Clone https://github.com/internetarchive/CDX-Writer to get **cdx_writer.py**

3. Copy **cdx_writer.py** from `CDX_Writer` into **warctools/hanzo** in `warctools`

4. Ensure sort order set to byte-order `export LC_ALL=C`

4. From the directory of the warc(s), run `<FULL PATH>/warctools/hanzo/cdx_writer mypath/warcs/mywarc.gz | sort > mypath/cdx/mywarc.cdx` 

   This will create a sorted `mywarc.cdx` for `mywarc.gz`. Then point pywb to the `mypath/warcs` and `mypath/cdx` directories in the yaml config.


5. `pywb` sort merges all specified cdx files on the fly. However, if dealing with larger number of small cdxs, there will be performance benefit

    from sort-merging them into a larger cdx file before running pywb. This is recommended for production.

    An example sort merge post process can be done as follows:

   ```
   export LC_ALL=C
   sort -m mypath/cdx/*.cdx | sort -c > mypath/merged_cdx/merge_1.cdx
   ```

   (The merged cdx will have multiple ' CDX ' headers due to the merge.. these headers do not need to stripped out as pywb ignores them)


   Then in the yaml config, set `index_paths` to point to `mypath/merged_cdx/merged_1.cdx`









  [1]: https://archive.org/web/
