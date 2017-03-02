
"""
Test loading different types of records from a variety of formats

# Load response record from compressed WARC
>>> load_test_archive('example.warc.gz', '333', '1043')
(('warc', 'response'),
 StatusAndHeaders(protocol = 'WARC/1.0', statusline = '', headers = [ ('WARC-Type', 'response'),
  ('WARC-Record-ID', '<urn:uuid:6d058047-ede2-4a13-be79-90c17c631dd4>'),
  ('WARC-Date', '2014-01-03T03:03:21Z'),
  ('Content-Length', '1610'),
  ('Content-Type', 'application/http; msgtype=response'),
  ('WARC-Payload-Digest', 'sha1:B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A'),
  ('WARC-Target-URI', 'http://example.com?example=1'),
  ('WARC-Warcinfo-ID', '<urn:uuid:fbd6cf0a-6160-4550-b343-12188dc05234>')]),
 StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Cache-Control', 'max-age=604800'),
  ('Content-Type', 'text/html'),
  ('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
  ('Etag', '"359670651"'),
  ('Expires', 'Fri, 10 Jan 2014 03:03:21 GMT'),
  ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('x-ec-custom-error', '1'),
  ('Content-Length', '1270'),
  ('Connection', 'close')]))

# Load revisit record from compressed WARC
>>> load_test_archive('example.warc.gz', '1864', '553')
(('warc', 'revisit'),
 StatusAndHeaders(protocol = 'WARC/1.0', statusline = '', headers = [ ('WARC-Type', 'revisit'),
  ('WARC-Record-ID', '<urn:uuid:3619f5b0-d967-44be-8f24-762098d427c4>'),
  ('WARC-Date', '2014-01-03T03:03:41Z'),
  ('Content-Length', '340'),
  ('Content-Type', 'application/http; msgtype=response'),
  ('WARC-Payload-Digest', 'sha1:B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A'),
  ('WARC-Target-URI', 'http://example.com?example=1'),
  ('WARC-Warcinfo-ID', '<urn:uuid:fbd6cf0a-6160-4550-b343-12188dc05234>'),
  ('WARC-Profile', 'http://netpreserve.org/warc/0.18/revisit/identical-payload-digest'),
  ('WARC-Refers-To-Target-URI', 'http://example.com?example=1'),
  ('WARC-Refers-To-Date', '2014-01-03T03:03:21Z')]),
 StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Cache-Control', 'max-age=604800'),
  ('Content-Type', 'text/html'),
  ('Date', 'Fri, 03 Jan 2014 03:03:41 GMT'),
  ('Etag', '"359670651"'),
  ('Expires', 'Fri, 10 Jan 2014 03:03:41 GMT'),
  ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('x-ec-custom-error', '1'),
  ('Content-Length', '1270'),
  ('Connection', 'close')]))

# request parsing
>>> load_test_archive('example.warc.gz', '1376', '488')
(('warc', 'request'),
 StatusAndHeaders(protocol = 'WARC/1.0', statusline = '', headers = [ ('WARC-Type', 'request'),
  ('WARC-Record-ID', '<urn:uuid:9a3ffea5-9556-4790-a6bf-c15231fd6b97>'),
  ('WARC-Date', '2014-01-03T03:03:21Z'),
  ('Content-Length', '323'),
  ('Content-Type', 'application/http; msgtype=request'),
  ('WARC-Concurrent-To', '<urn:uuid:6d058047-ede2-4a13-be79-90c17c631dd4>'),
  ('WARC-Target-URI', 'http://example.com?example=1'),
  ('WARC-Warcinfo-ID', '<urn:uuid:fbd6cf0a-6160-4550-b343-12188dc05234>')]),
 StatusAndHeaders(protocol = 'GET', statusline = '/?example=1 HTTP/1.1', headers = [ ('Connection', 'close'),
  ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'),
  ('Accept-Language', 'en-US,en;q=0.8'),
  ('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/31.0.1650.57 Safari/537.36 (via Wayback Save Page)'),
  ('Host', 'example.com')]))


# Test of record loading based on cdx line
# Print parsed http headers + 2 lines of content
# ==============================================================================

# Test loading from compressed ARC based on cdx line
>>> load_from_cdx_test('com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 856 171 example.arc.gz')
StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Cache-Control', 'max-age=604800'),
  ('Content-Type', 'text/html'),
  ('Date', 'Sun, 16 Feb 2014 05:02:20 GMT'),
  ('Etag', '"359670651"'),
  ('Expires', 'Sun, 23 Feb 2014 05:02:20 GMT'),
  ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('x-ec-custom-error', '1'),
  ('Content-Length', '1270')])
<!doctype html>
<html>

# Uncompressed arc
>>> load_from_cdx_test('com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1656 151 example.arc')
StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Cache-Control', 'max-age=604800'),
  ('Content-Type', 'text/html'),
  ('Date', 'Sun, 16 Feb 2014 05:02:20 GMT'),
  ('Etag', '"359670651"'),
  ('Expires', 'Sun, 23 Feb 2014 05:02:20 GMT'),
  ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('x-ec-custom-error', '1'),
  ('Content-Length', '1270')])
<!doctype html>
<html>


# Test loading from compressed WARC based on cdx line
>>> load_from_cdx_test('com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz')
StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Cache-Control', 'max-age=604800'),
  ('Content-Type', 'text/html'),
  ('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
  ('Etag', '"359670651"'),
  ('Expires', 'Fri, 10 Jan 2014 03:03:21 GMT'),
  ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('x-ec-custom-error', '1'),
  ('Content-Length', '1270'),
  ('Connection', 'close')])
<!doctype html>
<html>

# Uncompressed WARC
>>> load_from_cdx_test('com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1987 460 example.warc')
StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Cache-Control', 'max-age=604800'),
  ('Content-Type', 'text/html'),
  ('Date', 'Fri, 03 Jan 2014 03:03:21 GMT'),
  ('Etag', '"359670651"'),
  ('Expires', 'Fri, 10 Jan 2014 03:03:21 GMT'),
  ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('x-ec-custom-error', '1'),
  ('Content-Length', '1270'),
  ('Connection', 'close')])
<!doctype html>
<html>

# Test cdx w/ revisit, also no length specified
>>> load_from_cdx_test('com,example)/?example=1 20140103030341 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - - 1864 example.warc.gz 1043 333 example.warc.gz')
StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Cache-Control', 'max-age=604800'),
  ('Content-Type', 'text/html'),
  ('Date', 'Fri, 03 Jan 2014 03:03:41 GMT'),
  ('Etag', '"359670651"'),
  ('Expires', 'Fri, 10 Jan 2014 03:03:41 GMT'),
  ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('x-ec-custom-error', '1'),
  ('Content-Length', '1270'),
  ('Connection', 'close')])
<!doctype html>
<html>

# Test loading warc created by wget 1.14
>>> load_from_cdx_test('com,example)/ 20140216012908 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1151 792 example-wget-1-14.warc.gz')
StatusAndHeaders(protocol = 'HTTP/1.1', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Cache-Control', 'max-age=604800'),
  ('Content-Type', 'text/html'),
  ('Date', 'Sun, 16 Feb 2014 01:29:08 GMT'),
  ('Etag', '"359670651"'),
  ('Expires', 'Sun, 23 Feb 2014 01:29:08 GMT'),
  ('Last-Modified', 'Fri, 09 Aug 2013 23:54:35 GMT'),
  ('Server', 'ECS (sjc/4FB4)'),
  ('X-Cache', 'HIT'),
  ('x-ec-custom-error', '1'),
  ('Content-Length', '1270')])
<!doctype html>
<html>


# Test Url Agnostic Revisit Resolving
# ==============================================================================
>>> load_from_cdx_test(URL_AGNOSTIC_ORIG_CDX)
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Content-Type', 'text/html; charset=UTF-8'),
  ('Date', 'Tue, 02 Jul 2013 19:54:02 GMT'),
  ('ETag', '"780602-4f6-4db31b2978ec0"'),
  ('Last-Modified', 'Thu, 25 Apr 2013 16:13:23 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('Content-Length', '1270'),
  ('Connection', 'close')])
<!doctype html>
<html>

>>> load_from_cdx_test(URL_AGNOSTIC_REVISIT_CDX)
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Content-Type', 'text/html; charset=UTF-8'),
  ('Date', 'Mon, 29 Jul 2013 19:51:51 GMT'),
  ('ETag', '"780602-4f6-4db31b2978ec0"'),
  ('Last-Modified', 'Thu, 25 Apr 2013 16:13:23 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('Content-Length', '1270'),
  ('Connection', 'close')])
<!doctype html>
<html>

>>> load_from_cdx_test(URL_AGNOSTIC_REVISIT_NO_DIGEST_CDX)
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '200 OK', headers = [ ('Accept-Ranges', 'bytes'),
  ('Content-Type', 'text/html; charset=UTF-8'),
  ('Date', 'Mon, 29 Jul 2013 19:51:51 GMT'),
  ('ETag', '"780602-4f6-4db31b2978ec0"'),
  ('Last-Modified', 'Thu, 25 Apr 2013 16:13:23 GMT'),
  ('Server', 'ECS (sjc/4FCE)'),
  ('X-Cache', 'HIT'),
  ('Content-Length', '1270'),
  ('Connection', 'close')])
<!doctype html>
<html>

# Error Handling
# ==============================================================================

# Warc not found, keep track of failed files
>>> failed_files = []
>>> load_from_cdx_test('com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 856 170 x-not-found-x.warc.gz',\
failed_files=failed_files)
Exception: ArchiveLoadFailed

# ensure failed_files being filled
>>> print_strs(failed_files)
['x-not-found-x.warc.gz']

>>> load_from_cdx_test('com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 856 170 x-not-found-x.warc.gz',\
failed_files=failed_files)
Exception: ArchiveLoadFailed


# Invalid WARC Offset
>>> load_from_cdx_test('com,example)/?example=1 20140103030341 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1860 example.warc.gz 1043 333 example.warc.gz')
Exception: ArchiveLoadFailed


# Invalid ARC Offset
>>> load_from_cdx_test('com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 856 170 example.arc.gz')
Exception: ArchiveLoadFailed


# Error Expected with revisit -- invalid offset on original
>>> load_from_cdx_test('com,example)/?example=1 20140103030341 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1864 example.warc.gz 1043 330 example.warc.gz')
Exception: ArchiveLoadFailed


# Test EOF
>>> parse_stream_error(stream=None, statusline='', known_format='warc')
Exception: EOFError

>>> parse_stream_error(stream=None, statusline='', known_format='arc')
Exception: EOFError

# Invalid ARC
>>> parse_stream_error(stream=None, statusline='ABC', known_format='arc')
Exception: ArchiveLoadFailed

# Invalid WARC
>>> parse_stream_error(stream=None, statusline='ABC', known_format='warc')
Exception: ArchiveLoadFailed

# Revisit Errors
# original missing, no match
>>> load_from_cdx_test('com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - - 1864 example.warc.gz - - -', revisit_func=lambda x: [])
Exception: ArchiveLoadFailed

# revisit fallback: original warc in cdx not found, try lookup
>>> load_from_cdx_test('com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - - 1864 example.warc.gz 100 10 someunknown.warc.gz', revisit_func=load_orig_bad_cdx)
Exception: ArchiveLoadFailed

# no revisit func available
>>> load_from_cdx_test(URL_AGNOSTIC_REVISIT_CDX, revisit_func=None)
Exception: ArchiveLoadFailed


# url-agnostic original found, but could not be loaded
>>> load_from_cdx_test(URL_AGNOSTIC_REVISIT_CDX, revisit_func=load_orig_bad_cdx)
Exception: ArchiveLoadFailed


"""

import os
import sys
import pprint
import six

from warcio.recordloader import ArcWarcRecordLoader, ArchiveLoadFailed
from pywb.warc.blockrecordloader import BlockArcWarcRecordLoader
from pywb.warc.resolvingloader import ResolvingLoader
from pywb.warc.pathresolvers import PathResolverMapper
from pywb.cdx.cdxobject import CDXObject

import warcio.statusandheaders

from pywb import get_test_dir

#==============================================================================
test_warc_dir = get_test_dir() + 'warcs/'


URL_AGNOSTIC_ORIG_CDX = 'org,iana,example)/ 20130702195402 http://example.iana.org/ \
text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - \
1001 353 example-url-agnostic-orig.warc.gz'

URL_AGNOSTIC_REVISIT_CDX = 'com,example)/ 20130729195151 http://test@example.com/ \
warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - \
591 355 example-url-agnostic-revisit.warc.gz'

URL_AGNOSTIC_REVISIT_NO_DIGEST_CDX = 'com,example)/ 20130729195151 http://test@example.com/ \
warc/revisit - - - - \
591 355 example-url-agnostic-revisit.warc.gz'

BAD_ORIG_CDX = b'org,iana,example)/ 20130702195401 http://example.iana.org/ \
text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - \
1001 353 someunknown.warc.gz'


#==============================================================================
def load_test_archive(test_file, offset, length):
    path = test_warc_dir + test_file

    testloader = BlockArcWarcRecordLoader()

    archive = testloader.load(path, offset, length)

    warcio.statusandheaders.WRAP_WIDTH = 160

    pprint.pprint(((archive.format, archive.rec_type),
                   archive.rec_headers, archive.http_headers), indent=1, width=160)

    warcio.statusandheaders.WRAP_WIDTH = 80


#==============================================================================
def load_orig_bad_cdx(_):
    return [CDXObject(BAD_ORIG_CDX),
            CDXObject(BAD_ORIG_CDX)]


#==============================================================================
def load_orig_cdx(_):
    return [CDXObject(BAD_ORIG_CDX),
            CDXObject(URL_AGNOSTIC_ORIG_CDX.encode('utf-8'))]


#==============================================================================
def load_from_cdx_test(cdx, revisit_func=load_orig_cdx, reraise=False,
                       failed_files=None):
    resolve_loader = ResolvingLoader(PathResolverMapper()(test_warc_dir))
    cdx = CDXObject(cdx.encode('utf-8'))

    try:
        (headers, stream) = resolve_loader(cdx, failed_files, revisit_func)
        print(repr(headers))
        sys.stdout.write(stream.readline().decode('utf-8'))
        sys.stdout.write(stream.readline().decode('utf-8'))
    except ArchiveLoadFailed as e:
        if reraise:
            raise
        else:
            print('Exception: ' + e.__class__.__name__)


#==============================================================================
def parse_stream_error(**params):
    try:
        return ArcWarcRecordLoader().parse_record_stream(**params)
    except Exception as e:
        print('Exception: ' + e.__class__.__name__)


#==============================================================================
def print_strs(strings):
    return list(map(lambda string: string.encode('utf-8') if six.PY2 else string, strings))




if __name__ == "__main__":
    import doctest
    doctest.testmod()
