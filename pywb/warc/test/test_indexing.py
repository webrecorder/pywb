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
>>> print_cdx_index('example.warc', include_all=True)
 CDX N b a m s k r M S V g
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1987 460 example.warc
com,example)/?example=1 20140103030321 http://example.com?example=1 - - - - - 706 2451 example.warc
com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 896 3161 example.warc
com,example)/?example=1 20140103030341 http://example.com?example=1 - - - - - 706 4061 example.warc
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 854 4771 example.warc

# arc.gz
>>> print_cdx_index('example.arc.gz')
 CDX N b a m s k r M S V g
com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 856 171 example.arc.gz

# arc
>>> print_cdx_index('example.arc')
 CDX N b a m s k r M S V g
com,example)/ 20140216050221 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1656 151 example.arc

# wget warc, includes metadata by default
>>> print_cdx_index('example-wget-1-14.warc.gz')
 CDX N b a m s k r M S V g
com,example)/ 20140216012908 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1151 792 example-wget-1-14.warc.gz
metadata)/gnu.org/software/wget/warc/manifest.txt 20140216012908 metadata://gnu.org/software/wget/warc/MANIFEST.txt text/plain - SWUF4CK2XMZSOKSA7SDT7M7NUGWH2TRE - - 315 1943 example-wget-1-14.warc.gz
metadata)/gnu.org/software/wget/warc/wget_arguments.txt 20140216012908 metadata://gnu.org/software/wget/warc/wget_arguments.txt text/plain - UCXDCGORD6K4RJT5NUQGKE2PKEG4ZZD6 - - 340 2258 example-wget-1-14.warc.gz
metadata)/gnu.org/software/wget/warc/wget.log 20140216012908 metadata://gnu.org/software/wget/warc/wget.log text/plain - 2ULE2LD5UOWDXGACCT624TU5BVKACRQ4 - - 599 2598 example-wget-1-14.warc.gz


# wget warc, includes metadata and request
>>> print_cdx_index('example-wget-1-14.warc.gz', include_all=True)
 CDX N b a m s k r M S V g
com,example)/ 20140216012908 http://example.com/ - - - - - 394 398 example-wget-1-14.warc.gz
com,example)/ 20140216012908 http://example.com/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1151 792 example-wget-1-14.warc.gz
metadata)/gnu.org/software/wget/warc/manifest.txt 20140216012908 metadata://gnu.org/software/wget/warc/MANIFEST.txt text/plain - SWUF4CK2XMZSOKSA7SDT7M7NUGWH2TRE - - 315 1943 example-wget-1-14.warc.gz
metadata)/gnu.org/software/wget/warc/wget_arguments.txt 20140216012908 metadata://gnu.org/software/wget/warc/wget_arguments.txt text/plain - UCXDCGORD6K4RJT5NUQGKE2PKEG4ZZD6 - - 340 2258 example-wget-1-14.warc.gz
metadata)/gnu.org/software/wget/warc/wget.log 20140216012908 metadata://gnu.org/software/wget/warc/wget.log text/plain - 2ULE2LD5UOWDXGACCT624TU5BVKACRQ4 - - 599 2598 example-wget-1-14.warc.gz

# bad arcs -- test error edge cases
>>> print_cdx_index('bad.arc', include_all=True)
 CDX N b a m s k r M S V g
com,example)/ 20140401000000 http://example.com/ text/html - 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 67 134 bad.arc
com,example)/ 20140102000000 http://example.com/ text/plain - 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 59 202 bad.arc
com,example)/ 20140401000000 http://example.com/ text/html - 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 68 262 bad.arc


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
org,httpbin)/post?foo=bar&test=abc 20140610000859 http://httpbin.org/post application/json 200 M532K5WS4GY2H4OVZO6HRPOP47A7KDWU - - 720 0 post-test.warc.gz
org,httpbin)/post?a=1&b=[]&c=3 20140610001151 http://httpbin.org/post application/json 200 M7YCTM7HS3YKYQTAWQVMQSQZBNEOXGU2 - - 723 1196 post-test.warc.gz
org,httpbin)/post?data=^&foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/json 200 B6E5P6JUZI6UPDTNO4L2BCHMGLTNCUAJ - - 723 2395 post-test.warc.gz

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
org,httpbin)/post?foo=bar&test=abc 20140610000859 http://httpbin.org/post application/json 200 M532K5WS4GY2H4OVZO6HRPOP47A7KDWU - - 720 0 post-test.warc.gz
org,httpbin)/post?foo=bar&test=abc 20140610000859 http://httpbin.org/post application/x-www-form-urlencoded - - - - 476 720 post-test.warc.gz
org,httpbin)/post?a=1&b=[]&c=3 20140610001151 http://httpbin.org/post application/json 200 M7YCTM7HS3YKYQTAWQVMQSQZBNEOXGU2 - - 723 1196 post-test.warc.gz
org,httpbin)/post?a=1&b=[]&c=3 20140610001151 http://httpbin.org/post application/x-www-form-urlencoded - - - - 476 1919 post-test.warc.gz
org,httpbin)/post?data=^&foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/json 200 B6E5P6JUZI6UPDTNO4L2BCHMGLTNCUAJ - - 723 2395 post-test.warc.gz
org,httpbin)/post?data=^&foo=bar 20140610001255 http://httpbin.org/post?foo=bar application/x-www-form-urlencoded - - - - 475 3118 post-test.warc.gz



# Test CLI interface -- (check for num lines)
#=================================================================

# test sort, multiple inputs
>>> cli_lines(['--sort', '-',  TEST_WARC_DIR])
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz
org,iana,example)/ 20130702195402 http://example.iana.org/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1001 353 example-url-agnostic-orig.warc.gz
Total: 206

# test sort, multiple inputs, all records + post query
>>> cli_lines(['--sort', '-a', '-p', '-9', TEST_WARC_DIR])
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - 355 example-url-agnostic-revisit.warc.gz
org,iana,example)/ 20130702195402 http://example.iana.org/ text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - 353 example-url-agnostic-orig.warc.gz
Total: 398

# test writing to stdout
>>> cli_lines(['-', TEST_WARC_DIR + 'example.warc.gz'])
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 example.warc.gz
Total: 4

# test writing to stdout ('-' omitted)
>>> cli_lines([TEST_WARC_DIR + 'example.warc.gz'])
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 example.warc.gz
Total: 4

# test writing to temp dir, also use unicode filename
>>> cli_lines_with_dir(unicode(TEST_WARC_DIR + 'example.warc.gz'))
example.cdx
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
org,iana)/domains/example 20140128051539 http://www.iana.org/domains/example text/html 302 JZ622UA23G5ZU6Y3XAKH4LINONUEICEG - - 577 2907 example.warc.gz
Total: 4
"""

from pywb import get_test_dir

from pywb.warc.cdxindexer import write_cdx_index, main, cdx_filename

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
    sys.stdout.write(cdx_index(*args, **kwargs))

def assert_cdx_match(cdx, warc, sort=False):
    assert read_fully(cdx) == cdx_index(warc, sort=sort)

def test_sorted_warc_gz():
    assert_cdx_match('example.cdx', 'example.warc.gz', sort=True)
    assert_cdx_match('dupes.cdx', 'dupes.warc.gz', sort=True)
    assert_cdx_match('iana.cdx', 'iana.warc.gz', sort=True)

def cli_lines(cmds):
    buff = BytesIO()
    orig = sys.stdout
    sys.stdout = buff
    main(cmds)
    sys.stdout = orig
    lines = buff.getvalue().rstrip().split('\n')

    # print first, last, num lines
    print(lines[1])
    print(lines[-1])
    print('Total: ' + str(len(lines)))

def cli_lines_with_dir(input_):
    try:
        lines = None
        tmp_dir = None
        tmp_dir = tempfile.mkdtemp()

        main([tmp_dir, input_])

        filename = cdx_filename(os.path.basename(input_))

        print filename

        with open(os.path.join(tmp_dir, filename), 'rb') as fh:
            lines = fh.read(8192).rstrip().split('\n')

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
    print (lines[1])
    print (lines[-1])
    print('Total: ' + str(len(lines)))


def test_non_chunked_gzip_err():
    with raises(Exception):
        print_cdx_index('example-bad.warc.gz.bad')


if __name__ == "__main__":
    import doctest
    doctest.testmod()
