#!/bin/bash
cdx-indexer /webarchive/sample_archive/warcs/example.warc.gz > /tmp/index.cdx
curl -X POST --data-binary @/tmp/index.cdx http://outbackcdx:8080/pywb

