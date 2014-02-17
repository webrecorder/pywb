
"""
Test loading different types of records from a variety of formats

# Load response record from WARC
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

# Load revisit record from WARC
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
  ( 'WARC-Profile',
    'http://netpreserve.org/warc/0.18/revisit/identical-payload-digest'),
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


# Test of record loading based on cdx line
# Print parsed http headers + 2 lines of content
# ==============================================================================

# Test loading from ARC based on cdx line
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


# Test loading from WARC based on cdx line
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

# Test cdx w/ revisit
>>> load_from_cdx_test('com,example)/?example=1 20140103030341 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1864 example.warc.gz 1043 333 example.warc.gz')
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

# Error Handling

# Invalid WARC Offset
>>> load_from_cdx_test('com,example)/?example=1 20140103030341 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1860 example.warc.gz 1043 333 example.warc.gz')
Exception: ArchiveLoadFailed


# Invalid ARC Offset
>>> load_from_cdx_test('com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 332 example.warc.gz')
Exception: ArchiveLoadFailed


# Error Expected with revisit -- invalid offset on original
>>> load_from_cdx_test('com,example)/?example=1 20140103030341 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1864 example.warc.gz 1043 330 example.warc.gz')
Exception: ArchiveLoadFailed

"""

import os
import sys
import pprint

from pywb.warc.recordloader import ArcWarcRecordLoader, ArchiveLoadFailed
from pywb.warc.pathresolvers import make_best_resolvers
from pywb.warc.resolvingloader import ResolvingLoader
from pywb.cdx.cdxobject import CDXObject

from pywb import get_test_dir

#test_warc_dir = os.path.dirname(os.path.realpath(__file__)) + '/../sample_data/'
test_warc_dir = get_test_dir() + 'warcs/'

def load_test_archive(test_file, offset, length):
    path = test_warc_dir + test_file

    testloader = ArcWarcRecordLoader()

    archive = testloader.load(path, offset, length)
    archive = testloader.load(path, offset, length)

    pprint.pprint((archive.type, archive.rec_headers, archive.status_headers))


def load_from_cdx_test(cdx):
    resolve_loader = ResolvingLoader(test_warc_dir)
    cdx = CDXObject(cdx)
    try:
        (headers, stream) = resolve_loader.resolve_headers_and_payload(cdx, None)
        print headers
        sys.stdout.write(stream.readline())
        sys.stdout.write(stream.readline())
    except Exception as e:
        print 'Exception: ' + e.__class__.__name__

