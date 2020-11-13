.. _migrating-cdx:

Migrating CDX
=============

If you are not using OutbackCDX, you may need to check on the format of the CDX files that you are using.

Over the years, there have been many variations on the CDX (capture index) format which is used by OpenWayback and pywb to look up captures in WARC/ARC files.

When migrating CDX from OpenWayback, there are a few options.

pywb currently supports:

- 9 field CDX (surt-ordered)
- 11 field CDX (surt-ordered)
- CDXJ (surt-ordered)

pywb will support the 11-field and 9-field `CDX format <http://iipc.github.io/warc-specifications/specifications/cdx-format/cdx-2015/>`_ that is also used in OpenWayback.

Non-SURT ordered CDXs are not currently supported, though they may be supported in the future (see this `pending pull request <https://github.com/webrecorder/pywb/pull/586>`_).

CDXJ Conversion
---------------

The native format used by pywb is the :ref:`cdxj-index` with SURT-ordering, which uses JSON to encode the fields, allowing for more flexibility by storing most of the index in a JSON, allowing support for optional fields as needed.

If your CDX are not SURT-ordered, 11 or 9 field CDX, or if there is a mix, pywb also offers a conversion utility which will convert all CDX to the pywb native CDXJ: ::

  wb-manager cdx-convert <dir-of-cdx-files>

The converter will read the CDX files and create a corresponding .cdxj file for every cdx file. Since the conversion happens on the .cdx itself, it does not require reindexing the source WARC/ARC files and can happen fairly quickly.  The converted CDXJ are guaranteed to be in the right format to work with pywb.
