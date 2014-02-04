PyWb 0.1 Beta
==============

[![Build Status](https://travis-ci.org/ikreymer/pywb.png?branch=master)](https://travis-ci.org/ikreymer/pywb)

pywb is a Python re-implementation of the Wayback Machine software.

The goal is to provide a brand new, clean implementation of Wayback.

The focus is to focus on providing the best/accurate replay of archival web content (usually in WARC or ARC files),
and new ways of handling dynamic and difficult content.

pywb should also be easy to deploy and modify!


### Wayback Machine

A typical Wayback Machine serves archival content in the following form:

`http://<host>/<collection>/<timestamp>/<original url>`


Ex: The [Internet Archive Wayback Machine](https//archive.org/web/) has urls of the form:

`http://web.archive.org/web/20131015120316/http://archive.org/`


A listing of archived content, often in calendar form, is available when a `*` is used instead of timestamp.

The Wayback Machine uses an html parser to rewrite relative and absolute links, as well as absolute links found in javascript, css and some xml.

pywb uses this interface as a starting point.


### Requirements

pywb currently works best with 2.7.x
It should run in a standard WSGI container, although currently
tested primarily with uWSGI 1.9 and 2.0

Support for Python 3 is planned.


### Installation

pywb comes with sample archived content, also used
for unit testing the app.

The data can be found in `sample_archive` and contains
`warc` and `cdx` files. The sample archive contains
recent captures from `http://example.com` and `http://iana.org`


To start a pywb with sample data

1. Clone this repo

2. Install with `python setup.py install`

3. Run pywb by via script `run.sh` (script currently assumes a default python and uwsgi install, feel free to edit as needed)

4. Test pywb in your browser!  (pywb is set to run on port 8080 by default.)


If everything worked, the following pages should be loading (served from *sample_archive* dir):

| Original Url       | Latest Capture  | List of All Captures    |
| -------------      | -------------   | ----------------------- |
| `http://example.com` | [http://localhost:8080/pywb/example.com](http://localhost:8080/pywb/example.com) | [http://localhost:8080/pywb/*/example.com](http://localhost:8080/pywb/*/example.com) |
| `http://iana.org`    | [http://localhost:8080/pywb/iana.org](http://localhost:8080/pywb/iana.org) | [http://localhost:8080/pywb/*/iana.org](http://localhost:8080/pywb/*/iana.org) |


### Vagrant

pywb comes with a Vagrantfile to help you set up a VM quickly for testing.
If you have [Vagrant](http://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/)
installed, then you can start a test instance of pywb like so:

```bash
git clone https://github.com/ikreymer/pywb.git
cd pywb
vagrant up
```

After pywb and all its dependencies are installed, the uwsgi server will start up and you should see:

```
spawned uWSGI worker 1 (and the only) (pid: 123, cores: 1)
```

At this point, you can open a web browser and navigate to `http://localhost:8080` for testing.


### Automated Tests

Currently pywb consists of numerous doctests against the sample archive.

The `run-tests.py` file currently contains a few basic integration tests against the default config.


The current set of tests can be run with py.test:

`py.test run-tests.py ./pywb/ --doctest-modules`


or with Nose:

`nosetests --with-doctest`


### Sample Setup

pywb is configurable via yaml.

The simplest [config.yaml](config.yaml) is roughly as follows:

```yaml

collections:
   pywb: ./sample_archive/cdx/


archive_paths: ./sample_archive/warcs/

```

This sets up pywb with a single route for collection /pywb


(The [full version of config.yaml](config.yaml) contains additional documentation and specifies
all the optional properties, such as ui filenames for Jinja2/html template files.)


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

If you have warc files without cdxs, the following steps can be taken to create the indexs.

cdx indexs are sorted plain text files indexing the contents of archival records in one or more WARC/ARC files.

(The cdx_writer tool creates SURT ordered keys by default)

pywb does not currently generate indexs automatically, but this may be added in the future.

For production purposes, it is recommended that the cdx indexs be generated ahead of time.


** Note: these recommendations are subject to change as the external libraries are being cleaned up **

The directions are for running in a shell:


1. Clone https://bitbucket.org/rajbot/warc-tools

2. Clone https://github.com/internetarchive/CDX-Writer to get **cdx_writer.py**

3. Copy **cdx_writer.py** from `CDX_Writer` into **warctools/hanzo** in `warctools`

4. Ensure sort order set to byte-order `export LC_ALL=C` to ensure proper sorting.

5. From the directory of the warc(s), run `<FULL PATH>/warctools/hanzo/cdx_writer mypath/warcs/mywarc.gz | sort > mypath/cdx/mywarc.cdx`

   This will create a sorted `mywarc.cdx` for `mywarc.gz`. Then point `pywb` to the `mypath/warcs` and `mypath/cdx` directories in the yaml config.



6. pywb sort merges all specified cdx files on the fly. However, if dealing with larger number of small cdxs, there will be performance benefit

    from sort-merging them into a larger cdx file before running pywb. This is recommended for production.

    An example sort merge post process can be done as follows:

   ```
   export LC_ALL=C
   sort -m mypath/cdx/*.cdx | sort -c > mypath/merged_cdx/merge_1.cdx
   ```

   (The merged cdx will start with several ` CDX` headers due to the merge. These headers indicate cdx format and should be all the same!
    They are always first and pywb ignores them)


   In the yaml config, set `index_paths` to point to `mypath/merged_cdx/merged_1.cdx`


### Additional Documentation

* For additional/up-to-date configuration details, consult the current [config.yaml](config.yaml)

* The [wiki](https://github.com/ikreymer/pywb/wiki) will have additional technical documentation about various aspects of pywb

### Contributions

You are encouraged to fork and contribute to this project to improve web archiving replay

Please take a look at list of current [issues](https://github.com/ikreymer/pywb/issues?state=open) and feel free to open new ones


