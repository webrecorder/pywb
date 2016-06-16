r"""
# DecompressingBufferedReader Tests
#=================================================================

# DecompressingBufferedReader readline()
>>> print_str(DecompressingBufferedReader(open(test_cdx_dir + 'iana.cdx', 'rb')).readline())
' CDX N b a m s k r M S V g\n'

# detect not compressed
>>> print_str(DecompressingBufferedReader(open(test_cdx_dir + 'iana.cdx', 'rb'), decomp_type = 'gzip').readline())
' CDX N b a m s k r M S V g\n'

# decompress with on the fly compression, default gzip compression
>>> print_str(DecompressingBufferedReader(BytesIO(compress('ABC\n1234\n'))).read())
'ABC\n1234\n'

# decompress with on the fly compression, default 'inflate' compression
>>> print_str(DecompressingBufferedReader(BytesIO(compress_alt('ABC\n1234\n')), decomp_type='deflate').read())
'ABC\n1234\n'

# error: invalid compress type
>>> DecompressingBufferedReader(BytesIO(compress('ABC')), decomp_type = 'bzip2').read()
Traceback (most recent call last):
Exception: Decompression type not supported: bzip2

# invalid output when reading compressed data as not compressed
>>> DecompressingBufferedReader(BytesIO(compress('ABC')), decomp_type = None).read() != b'ABC'
True


# DecompressingBufferedReader readline() with decompression (zipnum file, no header)
>>> print_str(DecompressingBufferedReader(open(test_zip_dir + 'zipnum-sample.cdx.gz', 'rb'), decomp_type = 'gzip').readline())
'com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz\n'

# test very small block size
>>> dbr = DecompressingBufferedReader(BytesIO(b'ABCDEFG\nHIJKLMN\nOPQR\nXYZ'), block_size = 3)
>>> print_str(dbr.readline()); print_str(dbr.readline(4)); print_str(dbr.readline()); print_str(dbr.readline()); print_str(dbr.readline(2)); print_str(dbr.readline()); print_str(dbr.readline())
'ABCDEFG\n'
'HIJK'
'LMN\n'
'OPQR\n'
'XY'
'Z'
''

# test zero length reads
>>> x = DecompressingBufferedReader(LimitReader(BytesIO(b'\r\n'), 1))
>>> print_str(x.readline(0)); print_str(x.read(0))
''
''

# Chunk-Decoding Buffered Reader Tests
#=================================================================

Properly formatted chunked data:
>>> c = ChunkedDataReader(BytesIO(b"4\r\n1234\r\n0\r\n\r\n"));
>>> print_str(c.read() + c.read() + c.read())
'1234'

Non-chunked data:
>>> print_str(ChunkedDataReader(BytesIO(b"xyz123!@#")).read())
'xyz123!@#'

Non-chunked, compressed data, specify decomp_type
>>> print_str(ChunkedDataReader(BytesIO(compress('ABCDEF')), decomp_type='gzip').read())
'ABCDEF'

Non-chunked, compressed data, specifiy compression seperately
>>> c = ChunkedDataReader(BytesIO(compress('ABCDEF'))); c.set_decomp('gzip'); print_str(c.read())
'ABCDEF'

Non-chunked, compressed data, wrap in DecompressingBufferedReader
>>> print_str(DecompressingBufferedReader(ChunkedDataReader(BytesIO(compress('\nABCDEF\nGHIJ')))).read())
'\nABCDEF\nGHIJ'

Chunked compressed data
Split compressed stream into 10-byte chunk and a remainder chunk
>>> b = compress('ABCDEFGHIJKLMNOP')
>>> l = len(b)
>>> in_ = format(10, 'x').encode('utf-8') + b"\r\n" + b[:10] + b"\r\n" + format(l - 10, 'x').encode('utf-8') + b"\r\n" + b[10:] + b"\r\n0\r\n\r\n"
>>> c = ChunkedDataReader(BytesIO(in_), decomp_type='gzip')
>>> print_str(c.read())
'ABCDEFGHIJKLMNOP'

Starts like chunked data, but isn't:
>>> c = ChunkedDataReader(BytesIO(b"1\r\nxyz123!@#"));
>>> print_str(c.read() + c.read())
'1\r\nx123!@#'

Chunked data cut off part way through:
>>> c = ChunkedDataReader(BytesIO(b"4\r\n1234\r\n4\r\n12"));
>>> print_str(c.read() + c.read())
'123412'

Zero-Length chunk:
>>> print_str(ChunkedDataReader(BytesIO(b"0\r\n\r\n")).read())
''

"""

from io import BytesIO
from pywb.utils.bufferedreaders import ChunkedDataReader, ChunkedDataException
from pywb.utils.bufferedreaders import DecompressingBufferedReader
from pywb.utils.loaders import LimitReader

from pywb import get_test_dir

import six

import zlib
import pytest

test_cdx_dir = get_test_dir() + 'cdx/'
test_zip_dir = get_test_dir() + 'zipcdx/'


def compress(buff):
    buff = buff.encode('utf-8')
    compressobj = zlib.compressobj(6, zlib.DEFLATED, zlib.MAX_WBITS + 16)
    compressed = compressobj.compress(buff)
    compressed += compressobj.flush()

    return compressed

# plain "inflate"
def compress_alt(buff):
    buff = buff.encode('utf-8')
    compressobj = zlib.compressobj(6, zlib.DEFLATED)
    compressed = compressobj.compress(buff)
    compressed += compressobj.flush()
    # drop gzip headers/tail
    compressed = compressed[2:-4]

    return compressed

# Brotli

def test_brotli():
    with open(get_test_dir() + 'text_content/quickfox_repeated.compressed', 'rb') as fh:
        x = DecompressingBufferedReader(fh, decomp_type='br')
        x.read() == b'The quick brown fox jumps over the lazy dog' * 4096



# Errors

def test_err_compress_mix():
    # error: compressed member, followed by not compressed -- considered invalid
    x = DecompressingBufferedReader(BytesIO(compress('ABC') + b'123'), decomp_type = 'gzip')
    b = x.read()
    assert b == b'ABC'
    x.read_next_member()
    assert x.read() == b''
    #with pytest.raises(zlib.error):
    #    x.read()
    #error: Error -3 while decompressing: incorrect header check

def test_err_chunk_cut_off():
    # Chunked data cut off with exceptions
    c = ChunkedDataReader(BytesIO(b"4\r\n1234\r\n4\r\n12"), raise_exceptions=True)
    with pytest.raises(ChunkedDataException):
        c.read() + c.read()
    #ChunkedDataException: Ran out of data before end of chunk



def print_str(string):
    return string.decode('utf-8') if six.PY3 else string



if __name__ == "__main__":
    import doctest
    doctest.testmod()
