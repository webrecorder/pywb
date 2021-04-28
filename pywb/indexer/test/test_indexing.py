r"""

#=================================================================
# warc.gz
>>> print_cdx_index('example.warc.gz')
 CDX N b a m s k r M S V g
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1864 example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 example.warc.gz

# warc.gz -- parse all
>>> print_cdx_index('example.warc.gz', include_all=True)
 CDX N b a m s k r M S V g
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
com,example)/?example=1 20140103030321 http://example.com?example=1 - - - - - 488 1376 example.warc.gz
com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1864 example.warc.gz
com,example)/?example=1 20140103030341 http://example.com?example=1 - - - - - 490 2417 example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 example.warc.gz

# warc
>>> print_cdx_index('example.warc')
 CDX N b a m s k r M S V g
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1987 460 example.warc
com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 896 3161 example.warc
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 854 4771 example.warc

# warc all
# note: length of request record set to 1 byte less then record to test truncation handling
>>> print_cdx_index('example.warc', include_all=True)
 CDX N b a m s k r M S V g
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1987 460 example.warc
com,example)/?example=1 20140103030321 http://example.com?example=1 - - - - - 706 2451 example.warc
com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 896 3161 example.warc
com,example)/?example=1 20140103030341 http://example.com?example=1 - - - - - 703 4061 example.warc
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 854 4771 example.warc

# arc.gz
>>> print_cdx_index('example.arc.gz')
 CDX N b a m s k r M S V g
com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 856 171 example.arc.gz

# arc
>>> print_cdx_index('example.arc')
 CDX N b a m s k r M S V g
com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1656 151 example.arc

# arc.gz
>>> print_cdx_index('example.arc.gz', arc2warc=True)
 CDX N b a m s k r M S V g
com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 856 171 example.arc.gz

# arc
>>> print_cdx_index('example.arc', arc2warc=True)
 CDX N b a m s k r M S V g
com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1656 151 example.arc




# wget warc, includes metadata by default
>>> print_cdx_index('example-wget-1-14.warc.gz')
 CDX N b a m s k r M S V g
com,example)/ 20140216012908 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1151 792 example-wget-1-14.warc.gz
org,gnu)/software/wget/warc/manifest.txt 20140216012908 metadata://gnu.org/software/wget/warc/MANIFEST.txt text/plain - SWUF4CK2XMZSOKSA7SDT7M7NUGWH2TRE - - 315 1943 example-wget-1-14.warc.gz
org,gnu)/software/wget/warc/wget_arguments.txt 20140216012908 metadata://gnu.org/software/wget/warc/wget_arguments.txt text/plain - UCXDCGORD6K4RJT5NUQGKE2PKEG4ZZD6 - - 340 2258 example-wget-1-14.warc.gz
org,gnu)/software/wget/warc/wget.log 20140216012908 metadata://gnu.org/software/wget/warc/wget.log text/plain - 2ULE2LD5UOWDXGACCT624TU5BVKACRQ4 - - 599 2598 example-wget-1-14.warc.gz


# wget warc, includes metadata and request
>>> print_cdx_index('example-wget-1-14.warc.gz', include_all=True)
 CDX N b a m s k r M S V g
com,example)/ 20140216012908 http://example.com/ - - - - - 394 398 example-wget-1-14.warc.gz
com,example)/ 20140216012908 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1151 792 example-wget-1-14.warc.gz
org,gnu)/software/wget/warc/manifest.txt 20140216012908 metadata://gnu.org/software/wget/warc/MANIFEST.txt text/plain - SWUF4CK2XMZSOKSA7SDT7M7NUGWH2TRE - - 315 1943 example-wget-1-14.warc.gz
org,gnu)/software/wget/warc/wget_arguments.txt 20140216012908 metadata://gnu.org/software/wget/warc/wget_arguments.txt text/plain - UCXDCGORD6K4RJT5NUQGKE2PKEG4ZZD6 - - 340 2258 example-wget-1-14.warc.gz
org,gnu)/software/wget/warc/wget.log 20140216012908 metadata://gnu.org/software/wget/warc/wget.log text/plain - 2ULE2LD5UOWDXGACCT624TU5BVKACRQ4 - - 599 2598 example-wget-1-14.warc.gz

# wpull warc, includes metadata by default
>>> print_cdx_index('example-wpull.warc.gz')
 CDX N b a m s k r M S V g
com,example)/ 20150330235046 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1150 2031 example-wpull.warc.gz
urn:x-wpull:log 20150330235046 urn:X-wpull:log text/plain - Q32A3PBAN6S7I26HWZDX5CDCB6MN6UN6 - - 557 3181 example-wpull.warc.gz

# bad arcs -- test error edge cases
>>> print_cdx_index('bad.arc', include_all=True)
 CDX N b a m s k r M S V g
com,example)/ 20140401000000 http://example.com/ text/html 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 67 134 bad.arc
com,example)/ 20140102000000 http://example.com/ text/plain 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 59 202 bad.arc
com,example)/ 20140401000000 http://example.com/ text/html 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 68 262 bad.arc


# POST request tests
#=================================================================
# no post append, no requests
>>> print_cdx_index('post-test.warc.gz')
 CDX N b a m s k r M S V g
org,httpbin)/post 20140610000859 http://httpbin.org/post application/json 200 M532K5WS4GY2H4OVZO6HRPOP47A7KDWU - - 720 0 post-test.warc.gz
org,httpbin)/post 20140610001151 http://httpbin.org/post application/json 200 M7YCTM7HS3YKYQTAWQVMQSQZBNEOXGU2 - - 723 1196 post-test.warc.gz
org,httpbin)/post?foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/json 200 B6E5P6JUZI6UPDTNO4L2BCHMGLTNCUAJ - - 723 2395 post-test.warc.gz

# post append
>>> print_cdx_index('post-test.warc.gz', append_post=True)
 CDX N b a m s k r M S V g
org,httpbin)/post?__wb_method=post&foo=bar&test=abc 20140610000859 http://httpbin.org/post application/json 200 M532K5WS4GY2H4OVZO6HRPOP47A7KDWU - - 720 0 post-test.warc.gz
org,httpbin)/post?__wb_method=post&a=1&b=[]&c=3 20140610001151 http://httpbin.org/post application/json 200 M7YCTM7HS3YKYQTAWQVMQSQZBNEOXGU2 - - 723 1196 post-test.warc.gz
org,httpbin)/post?__wb_method=post&data=^&foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/json 200 B6E5P6JUZI6UPDTNO4L2BCHMGLTNCUAJ - - 723 2395 post-test.warc.gz

# no post append, requests included
>>> print_cdx_index('post-test.warc.gz', include_all=True)
 CDX N b a m s k r M S V g
org,httpbin)/post 20140610000859 http://httpbin.org/post application/json 200 M532K5WS4GY2H4OVZO6HRPOP47A7KDWU - - 720 0 post-test.warc.gz
org,httpbin)/post 20140610000859 http://httpbin.org/post application/x-www-form-urlencoded - - - - 476 720 post-test.warc.gz
org,httpbin)/post 20140610001151 http://httpbin.org/post application/json 200 M7YCTM7HS3YKYQTAWQVMQSQZBNEOXGU2 - - 723 1196 post-test.warc.gz
org,httpbin)/post 20140610001151 http://httpbin.org/post application/x-www-form-urlencoded - - - - 476 1919 post-test.warc.gz
org,httpbin)/post?foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/json 200 B6E5P6JUZI6UPDTNO4L2BCHMGLTNCUAJ - - 723 2395 post-test.warc.gz
org,httpbin)/post?foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/x-www-form-urlencoded - - - - 475 3118 post-test.warc.gz

# post append + requests included
>>> print_cdx_index('post-test.warc.gz', include_all=True, append_post=True)
 CDX N b a m s k r M S V g
org,httpbin)/post?__wb_method=post&foo=bar&test=abc 20140610000859 http://httpbin.org/post application/json 200 M532K5WS4GY2H4OVZO6HRPOP47A7KDWU - - 720 0 post-test.warc.gz
org,httpbin)/post?__wb_method=post&foo=bar&test=abc 20140610000859 http://httpbin.org/post application/x-www-form-urlencoded - - - - 476 720 post-test.warc.gz
org,httpbin)/post?__wb_method=post&a=1&b=[]&c=3 20140610001151 http://httpbin.org/post application/json 200 M7YCTM7HS3YKYQTAWQVMQSQZBNEOXGU2 - - 723 1196 post-test.warc.gz
org,httpbin)/post?__wb_method=post&a=1&b=[]&c=3 20140610001151 http://httpbin.org/post application/x-www-form-urlencoded - - - - 476 1919 post-test.warc.gz
org,httpbin)/post?__wb_method=post&data=^&foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/json 200 B6E5P6JUZI6UPDTNO4L2BCHMGLTNCUAJ - - 723 2395 post-test.warc.gz
org,httpbin)/post?__wb_method=post&data=^&foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/x-www-form-urlencoded - - - - 475 3118 post-test.warc.gz

# post append + minimal = error
>>> print_cdx_index('example.arc.gz', append_post=True, minimal=True)
Traceback (most recent call last):
Exception: Sorry, minimal index option and append POST options can not be used together

# Test with custom verbs/protocol
#================================================================
# no validation
>>> print_cdx_index('example-extra.warc')
 CDX N b a m s k r M S V g
com,example)/?example=2 20140103030321 http://example.com?example=2 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1987 0 example-extra.warc
com,example)/?example=2 20140603030341 http://example.com?example=2 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 504 2701 example-extra.warc
com,example)/?example=2 20140103030321 http://example.com?example=2 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1987 3207 example-extra.warc
com,example)/?example=2 20140603030341 http://example.com?example=2 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 504 5910 example-extra.warc

>>> print_cdx_index('example-extra.warc', verify_http=True)  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
StatusAndHeadersParserException: Expected Status Line starting with ['HTTP/1.0', 'HTTP/1.1'] - Found: HTTPX/1.1 200 OK


# Test CLI interface -- (check for num lines)
#=================================================================

# test sort, multiple inputs
>>> cli_lines(['--sort', '-o', '-',  TEST_WARC_DIR])
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz
urn:x-wpull:log 20150330235046 urn:X-wpull:log text/plain - Q32A3PBAN6S7I26HWZDX5CDCB6MN6UN6 - - 557 3181 example-wpull.warc.gz
Total: 213

# test sort, multiple inputs, recursive, from base test dir
>>> cli_lines(['--sort', '-r', '-o', '-',  get_test_dir()])
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 warcs/example-url-agnostic-revisit.warc.gz
urn:x-wpull:log 20150330235046 urn:X-wpull:log text/plain - Q32A3PBAN6S7I26HWZDX5CDCB6MN6UN6 - - 557 3181 warcs/example-wpull.warc.gz
Total: 213

# test sort, 9-field, multiple inputs, all records + post query
>>> cli_lines(['--sort', '-a', '-p', '-9', TEST_WARC_DIR])
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - 355 example-url-agnostic-revisit.warc.gz
urn:x-wpull:log 20150330235046 urn:X-wpull:log text/plain - Q32A3PBAN6S7I26HWZDX5CDCB6MN6UN6 - 3181 example-wpull.warc.gz
Total: 408

# test writing to stdout
>>> cli_lines([TEST_WARC_DIR + 'example.warc.gz'])
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 example.warc.gz
Total: 4

# test writing to stdout ('-' omitted)
>>> cli_lines([TEST_WARC_DIR + 'example.warc.gz'])
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 example.warc.gz
Total: 4

# test custom root dir for cdx filenames, single warc
>>> cli_lines(['--dir-root', get_test_dir() + 'other/', TEST_WARC_DIR + 'example.warc.gz'])
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 ../warcs/example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 ../warcs/example.warc.gz
Total: 4

# test custom root dir for cdx filenames, dir input
>>> cli_lines(['--sort', '--dir-root', get_test_dir() + 'other/', TEST_WARC_DIR])
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 ../warcs/example-url-agnostic-revisit.warc.gz
urn:x-wpull:log 20150330235046 urn:X-wpull:log text/plain - Q32A3PBAN6S7I26HWZDX5CDCB6MN6UN6 - - 557 3181 ../warcs/example-wpull.warc.gz
Total: 213

# test writing to temp dir, also use unicode filename
>>> cli_lines_with_dir(TEST_WARC_DIR + 'example.warc.gz')
example.cdx
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 example.warc.gz
Total: 4
"""

from pywb import get_test_dir

from pywb.indexer.cdxindexer import write_cdx_index, main, cdx_filename

from pywb.warcserver.index.cdxobject import CDXObject

from io import BytesIO
import sys

import os
import shutil
import tempfile

from pytest import raises


TEST_CDX_DIR = get_test_dir() + 'cdx/'
TEST_WARC_DIR = get_test_dir() + 'warcs/'

def read_fully(cdx):
    with open(TEST_CDX_DIR + cdx, 'rb') as fh:
        curr = BytesIO()
        while True:
            b = fh.read()
            if not b:
                break
            curr.write(b)
    return curr.getvalue()

def cdx_index(warc, **options):
    buff = BytesIO()

    with open(TEST_WARC_DIR + warc, 'rb') as fh:
        write_cdx_index(buff, fh,  warc, **options)

    return buff.getvalue()

def print_cdx_index(*args, **kwargs):
    sys.stdout.write(cdx_index(*args, **kwargs).decode('utf-8'))

def assert_cdx_match(cdx, warc, sort=False):
    assert read_fully(cdx) == cdx_index(warc, sort=sort)

def test_sorted_warc_gz():
    assert_cdx_match('example.cdx', 'example.warc.gz', sort=True)
    assert_cdx_match('dupes.cdx', 'dupes.warc.gz', sort=True)
    assert_cdx_match('iana.cdx', 'iana.warc.gz', sort=True)

def cli_lines(cmds):
    buff = BytesIO()
    orig = sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else None
    sys.stdout.buffer = buff
    main(cmds)
    sys.stdout.buffer = orig
    lines = buff.getvalue().rstrip().split(b'\n')

    # print first, last, num lines
    print(lines[1].decode('utf-8'))
    print(lines[-1].decode('utf-8'))
    print('Total: ' + str(len(lines)))

def cli_lines_with_dir(input_):
    try:
        lines = None
        tmp_dir = None
        tmp_dir = tempfile.mkdtemp()

        main(['-o', tmp_dir, input_])

        filename = cdx_filename(os.path.basename(input_))

        print(filename)

        with open(os.path.join(tmp_dir, filename), 'rb') as fh:
            lines = fh.read(8192).rstrip().split(b'\n')

    finally:
        try:
            if tmp_dir:
                shutil.rmtree(tmp_dir)
        except OSError as exc:
            if exc.errno != 2:
                raise

    if not lines:
        return

    # print first, last, num lines
    print(lines[1].decode('utf-8'))
    print(lines[-1].decode('utf-8'))
    print('Total: ' + str(len(lines)))


def test_non_chunked_gzip_err():
    with raises(Exception):
        print_cdx_index('example-bad.warc.gz.bad')


def parse_cdxj(string):
    lines = string.split(b'\n')
    if lines[0] == b'':
        lines = lines[1:]
    cdxlist = list(map(CDXObject, lines))
    return list(map(dict, cdxlist))


def test_cdxj_warc_minimal():
    # cdxj minimal
    res = cdx_index('example.warc.gz', minimal=True, cdxj=True)

    assert parse_cdxj(res) == parse_cdxj(b"""
com,example)/?example=1 20140103030321 {"url": "http://example.com?example=1", "digest": "B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A", "length": "1043", "offset": "333", "filename": "example.warc.gz"}
com,example)/?example=1 20140103030341 {"url": "http://example.com?example=1", "mime": "warc/revisit", "digest": "B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A", "length": "553", "offset": "1864", "filename": "example.warc.gz"}
org,iana)/domains/example 20140128051539 {"url": "http://www.iana.org/domains/example", "digest": "JZ622UA23G5ZU6Y3XAKH4LINONUEICEG", "length": "577", "offset": "2907", "filename": "example.warc.gz"}
""")


def test_cdxj_warc_all():
    # warc.gz -- parse all -- CDXJ
    res = cdx_index('example.warc.gz', include_all=True, cdxj=True)

    assert parse_cdxj(res) == parse_cdxj(b"""
com,example)/?example=1 20140103030321 {"url": "http://example.com?example=1", "mime": "text/html", "status": "200", "digest": "B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A", "length": "1043", "offset": "333", "filename": "example.warc.gz"}
com,example)/?example=1 20140103030321 {"url": "http://example.com?example=1", "length": "488", "offset": "1376", "filename": "example.warc.gz"}
com,example)/?example=1 20140103030341 {"url": "http://example.com?example=1", "mime": "warc/revisit", "digest": "B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A", "length": "553", "offset": "1864", "filename": "example.warc.gz"}
com,example)/?example=1 20140103030341 {"url": "http://example.com?example=1", "length": "490", "offset": "2417", "filename": "example.warc.gz"}
org,iana)/domains/example 20140128051539 {"url": "http://www.iana.org/domains/example", "mime": "text/html", "status": "302", "digest": "JZ622UA23G5ZU6Y3XAKH4LINONUEICEG", "length": "577", "offset": "2907", "filename": "example.warc.gz"}
""")

def test_cdxj_arc():
    # arc.gz -- json
    res = cdx_index('example.arc.gz', cdxj=True)
    assert parse_cdxj(res) == parse_cdxj(b"""
com,example)/ 20140216050221 {"url": "http://example.com/", "mime": "text/html", "status": "200", "digest": "B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A", "length": "856", "offset": "171", "filename": "example.arc.gz"}
""")

def test_cdxj_arc_minimal():
    # arc.gz -- minimal + json
    res = cdx_index('example.arc.gz', cdxj=True, minimal=True)
    assert parse_cdxj(res) == parse_cdxj(b"""
com,example)/ 20140216050221 {"url": "http://example.com/", "digest": "PEWDX5GTH66WU74WBPGFECIYBMPMP3FP", "length": "856", "offset": "171", "filename": "example.arc.gz"}
""")

def test_cdxj_arc_conv():
    # arc.gz -- json
    res = cdx_index('example.arc.gz', cdxj=True, arc2warc=True)
    assert parse_cdxj(res) == parse_cdxj(b"""
com,example)/ 20140216050221 {"url": "http://example.com/", "mime": "text/html", "status": "200", "digest": "B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A", "length": "856", "offset": "171", "filename": "example.arc.gz"}
""")

def test_cdxj_arc_minimal_conv():
    # arc.gz -- minimal + json
    res = cdx_index('example.arc.gz', cdxj=True, minimal=True, arc2warc=True)
    assert parse_cdxj(res) == parse_cdxj(b"""
com,example)/ 20140216050221 {"url": "http://example.com/", "digest": "PEWDX5GTH66WU74WBPGFECIYBMPMP3FP", "length": "856", "offset": "171", "filename": "example.arc.gz"}
""")




def test_cdxj_empty():
    options = dict(cdxj=True)

    buff = BytesIO()

    empty = BytesIO()

    write_cdx_index(buff, empty,  'empty.warc.gz', **options)

    assert buff.getvalue() == b''


def test_cdxj_middle_empty_records():
    empty_gzip_record = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    new_warc = BytesIO()

    with open(TEST_WARC_DIR + 'example2.warc.gz', 'rb') as fh:
        new_warc.write(empty_gzip_record)
        new_warc.write(fh.read())
        new_warc.write(empty_gzip_record)
        new_warc.write(empty_gzip_record)
        fh.seek(0)
        new_warc.write(fh.read())

    options = dict(cdxj=True)

    buff = BytesIO()
    new_warc.seek(0)

    write_cdx_index(buff, new_warc, 'empty.warc.gz', **options)

    lines = buff.getvalue().rstrip().split(b'\n')

    assert len(lines) == 2, lines


def test_invalid_decoding_uri_py2():
    test_data = b'\
WARC/1.0\r\n\
WARC-Type: resource\r\n\
WARC-Record-ID: <urn:uuid:12345678-feb0-11e6-8f83-68a86d1772ce>\r\n\
WARC-Target-URI: http://example.com/\xc3\x83\xc2\xa9\r\n\
WARC-Date: 2000-01-01T00:00:00Z\r\n\
Content-Type: text/plain\r\n\
Content-Length: 4\r\n\
\r\n\
ABCD\r\n\
\r\n'

    options = dict(include_all=True)

    buff = BytesIO()

    test_record = BytesIO(test_data)

    write_cdx_index(buff, test_record,  'test.warc.gz', **options)

    assert buff.getvalue() == b"""\
 CDX N b a m s k r M S V g
com,example)/%c3%83%c2%a9 20000101000000 http://example.com/\xc3\x83\xc2\xa9 text/plain - 7MXYLSEFM7Z4RTU3PGOHYVDEFUGHWQPW - - 222 0 test.warc.gz
"""


def test_no_index_metadata_mime_textanvl():
    test_data = b'\
WARC/0.18\r\n\
WARC-Type: response\r\n\
WARC-Record-ID: <urn:uuid:1fd7789c-9cd5-47ea-b7ba-2a97dc06680b>\r\n\
WARC-Target-URI: http://example.com/xyz.pdf\r\n\
WARC-Date: 2014-04-01T05:20:11Z\r\n\
WARC-Payload-Digest: sha1:EDIYL6WNHDY62TPKUCPSEWMOAAGYTOAS\r\n\
Content-Type: application/http; msgtype=response\r\n\
Content-Length: 4\r\n\
\r\n\
ABCD\r\n\
\r\n\
\r\n\
\r\n\
WARC/0.18\r\n\
WARC-Type: metadata\r\n\
WARC-Record-ID: <urn:uuid:0735267f-5749-4c02-b08b-955af5d76032>\r\n\
WARC-Target-URI: http://example.com/xyz.pdf\r\n\
WARC-Date: 2014-04-01T05:20:11Z\r\n\
WARC-Payload-Digest: sha1:EDIYL6WNHDY62TPKUCPSEWMOAAGYTOAS\r\n\
Content-Type: text/anvl\r\n\
Content-Length: 4\r\n\
\r\n\
ABCD\r\n\
\r\n\
'
    options = dict(include_all=True)

    buff = BytesIO()

    test_record = BytesIO(test_data)

    write_cdx_index(buff, test_record, 'test.warc.gz', **options)

    assert buff.getvalue() == b"""\
 CDX N b a m s k r M S V g
com,example)/xyz.pdf 20140401052011 http://example.com/xyz.pdf application/http 200 EDIYL6WNHDY62TPKUCPSEWMOAAGYTOAS - - 310 0 test.warc.gz
"""


def test_multipart_form():
    test_data = b'\
WARC/1.0\r\n\
WARC-Type: response\r\n\
WARC-Record-ID: <urn:uuid:073fac44-c383-4a2b-980d-76fec83bd20d>\r\n\
WARC-Date: 2020-11-19T19:54:34Z\r\n\
WARC-Target-URI: https://example.com/ajax/bz?foo=bar\r\n\
Content-Type: application/http;msgtype=response\r\n\
WARC-Payload-Digest: sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ\r\n\
Content-Length: 48\r\n\
WARC-Block-Digest: sha1:XN45YTSBLG5PLJ4HA7DRDYGJBM5VW4UO\r\n\
\r\n\
Content-Type: text/html; charset="utf-8"\r\n\
\r\n\
ABCD\r\n\
\r\n\
\r\n\
\r\n\
WARC/1.0\r\n\
WARC-Type: request\r\n\
WARC-Record-ID: <urn:uuid:3084e79c-ae58-4bfd-8590-fcf2830fe896>\r\n\
WARC-Date: 2020-11-19T19:54:34Z\r\n\
WARC-Target-URI: https://example.com/ajax/bz?foo=bar\r\n\
WARC-Concurrent-To: <urn:uuid:073fac44-c383-4a2b-980d-76fec83bd20d>\r\n\
WARC-Block-Digest: sha1:LNYP3X3NWXQLUGDI745P4L4FK27XGP24\r\n\
Content-Type: application/http;msgtype=request\r\n\
Content-Length: 321\r\n\
\r\n\
POST /ajax/bz?foo=bar HTTP/1.1\r\n\
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryWUBf9liofZK0nuJd\r\n\
content-Length: 199\r\n\
\r\n\
------WebKitFormBoundaryWUBf9liofZK0nuJd\r\n\
Content-Disposition: form-data; name="q"\r\n\
\r\n\
[{"webSessionId":"pb2tr7:vx83uz:fdi8ta","user":"0"}]\r\n\
------WebKitFormBoundaryWUBf9liofZK0nuJd--\r\n\
\r\n\
'
    options = dict(include_all=True, append_post=True)
    buff = BytesIO()
    test_record = BytesIO(test_data)
    write_cdx_index(buff, test_record, 'test.warc.gz', **options)
    print(buff.getvalue())
    assert buff.getvalue() == b"""\
 CDX N b a m s k r M S V g
com,example)/ajax/bz?__wb_method=post&foo=bar&q=[{"websessionid":"pb2tr7:vx83uz:fdi8ta","user":"0"}] 20201119195434 https://example.com/ajax/bz?foo=bar unk text/html; 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 420 0 test.warc.gz
com,example)/ajax/bz?__wb_method=post&foo=bar&q=[{"websessionid":"pb2tr7:vx83uz:fdi8ta","user":"0"}] 20201119195434 https://example.com/ajax/bz?foo=bar multipart/form-data - - - - 701 428 test.warc.gz
"""


def test_multipart_form_no_boundary():
    test_data = b'\
WARC/1.0\r\n\
WARC-Type: response\r\n\
WARC-Record-ID: <urn:uuid:3bc1606a-d517-487e-a6d5-bfeaebda2ec3>\r\n\
WARC-Date: 2020-11-19T14:02:52Z\r\n\
WARC-Target-URI: https://capi.connatix.com/core/story?v=77797\r\n\
WARC-IP-Address: 18.221.6.219\r\n\
Content-Type: application/http;msgtype=response\r\n\
WARC-Payload-Digest: sha1:SIGZ3RJW5J7DUKEZ4R7RSYUZNGLETIS5\r\n\
Content-Length: 41\r\n\
WARC-Block-Digest: sha1:JXKKZNALIPOW7J2FX5XUTGQZXKBSGZLU\r\n\
\r\n\
Content-Type: multipart/form-data\r\n\
\r\n\
ABCD\r\n\
\r\n\
\r\n\
\r\n\
WARC/1.0\r\n\
WARC-Type: request\r\n\
WARC-Record-ID: <urn:uuid:d5e7186f-5725-4ed1-b199-56fbdf4bd805>\r\n\
WARC-Date: 2020-11-19T14:02:52Z\r\n\
WARC-Target-URI: https://capi.connatix.com/core/story?v=77797\r\n\
WARC-Concurrent-To: <urn:uuid:3bc1606a-d517-487e-a6d5-bfeaebda2ec3>\r\n\
WARC-Block-Digest: sha1:QJ2YUIKEWDSCLK5A2DHGLQ7WWEKYMO3W\r\n\
Content-Type: application/http;msgtype=request\r\n\
Content-Length: 111\r\n\
\r\n\
POST /core/story?v=77797 HTTP/1.1\r\n\
Content-Length: 19\r\n\
Content-Type: multipart/form-data\r\n\
\r\n\
{"text": "default"}\r\n\
\r\n\
'
    options = dict(include_all=True, append_post=True)
    buff = BytesIO()
    test_record = BytesIO(test_data)
    write_cdx_index(buff, test_record, 'test.warc.gz', **options)
    assert buff.getvalue() == b"""\
 CDX N b a m s k r M S V g
com,connatix,capi)/core/story?__wb_method=post&__wb_post_data=eyj0zxh0ijogimrlzmf1bhqifq==&v=77797 20201119140252 https://capi.connatix.com/core/story?v=77797 unk multipart/form-data SIGZ3RJW5J7DUKEZ4R7RSYUZNGLETIS5 - - 453 0 test.warc.gz
com,connatix,capi)/core/story?__wb_method=post&__wb_post_data=eyj0zxh0ijogimrlzmf1bhqifq==&v=77797 20201119140252 https://capi.connatix.com/core/story?v=77797 multipart/form-data - - - - 500 461 test.warc.gz
"""


if __name__ == "__main__":
    import doctest
    doctest.testmod()
