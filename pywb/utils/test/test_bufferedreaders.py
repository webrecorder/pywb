r"""
# DecompressingBufferedReader Tests
#=================================================================

# DecompressingBufferedReader readline()
>>> DecompressingBufferedReader(open(test_cdx_dir + 'iana.cdx', 'rb')).readline()
' CDX N b a m s k r M S V g\n'

# detect not compressed
>>> DecompressingBufferedReader(open(test_cdx_dir + 'iana.cdx', 'rb'), decomp_type = 'gzip').readline()
' CDX N b a m s k r M S V g\n'

# decompress with on the fly compression, default gzip compression
>>> DecompressingBufferedReader(BytesIO(compress('ABC\n1234\n'))).read()
'ABC\n1234\n'

# decompress with on the fly compression, default 'inflate' compression
>>> DecompressingBufferedReader(BytesIO(compress_alt('ABC\n1234\n')), decomp_type='deflate').read()
'ABC\n1234\n'

# error: invalid compress type
>>> DecompressingBufferedReader(BytesIO(compress('ABC')), decomp_type = 'bzip2').read()
Traceback (most recent call last):
Exception: Decompression type not supported: bzip2

# error: compressed member, followed by not compressed -- considered invalid
>>> x = DecompressingBufferedReader(BytesIO(compress('ABC') + '123'), decomp_type = 'gzip')
>>> b = x.read()
>>> b = x.read_next_member()
>>> x.read()
Traceback (most recent call last):
error: Error -3 while decompressing: incorrect header check

# invalid output when reading compressed data as not compressed
>>> DecompressingBufferedReader(BytesIO(compress('ABC')), decomp_type = None).read() != 'ABC'
True


# DecompressingBufferedReader readline() with decompression (zipnum file, no header)
>>> DecompressingBufferedReader(open(test_zip_dir + 'zipnum-sample.cdx.gz', 'rb'), decomp_type = 'gzip').readline()
'com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz\n'

# test very small block size
>>> dbr = DecompressingBufferedReader(BytesIO('ABCDEFG\nHIJKLMN\nOPQR\nXYZ'), block_size = 3)
>>> dbr.readline(); dbr.readline(4); dbr.readline(); dbr.readline(); dbr.readline(2); dbr.readline(); dbr.readline()
'ABCDEFG\n'
'HIJK'
'LMN\n'
'OPQR\n'
'XY'
'Z'
''

# test zero length reads
>>> x = DecompressingBufferedReader(LimitReader(BytesIO('\r\n'), 1))
>>> x.readline(0); x.read(0)
''
''

# Chunk-Decoding Buffered Reader Tests
#=================================================================

Properly formatted chunked data:
>>> c = ChunkedDataReader(BytesIO("4\r\n1234\r\n0\r\n\r\n"));
>>> c.read() + c.read() + c.read()
'1234'

Non-chunked data:
>>> ChunkedDataReader(BytesIO("xyz123!@#")).read()
'xyz123!@#'

Non-chunked, compressed data, specify decomp_type
>>> ChunkedDataReader(BytesIO(compress('ABCDEF')), decomp_type='gzip').read()
'ABCDEF'

Non-chunked, compressed data, specifiy compression seperately
>>> c = ChunkedDataReader(BytesIO(compress('ABCDEF'))); c.set_decomp('gzip'); c.read()
'ABCDEF'

Non-chunked, compressed data, wrap in DecompressingBufferedReader
>>> DecompressingBufferedReader(ChunkedDataReader(BytesIO(compress('\nABCDEF\nGHIJ')))).read()
'\nABCDEF\nGHIJ'

Chunked compressed data
Split compressed stream into 10-byte chunk and a remainder chunk
>>> b = compress('ABCDEFGHIJKLMNOP')
>>> l = len(b)
>>> in_ = format(10, 'x') + "\r\n" + b[:10] + "\r\n" + format(l - 10, 'x') + "\r\n" + b[10:] + "\r\n0\r\n\r\n"
>>> c = ChunkedDataReader(BytesIO(in_), decomp_type='gzip')
>>> c.read()
'ABCDEFGHIJKLMNOP'

Starts like chunked data, but isn't:
>>> c = ChunkedDataReader(BytesIO("1\r\nxyz123!@#"));
>>> c.read() + c.read()
'1\r\nx123!@#'

Chunked data cut off part way through:
>>> c = ChunkedDataReader(BytesIO("4\r\n1234\r\n4\r\n12"));
>>> c.read() + c.read()
'123412'

Zero-Length chunk:
>>> ChunkedDataReader(BytesIO("0\r\n\r\n")).read()
''

Chunked data cut off with exceptions
>>> c = ChunkedDataReader(BytesIO("4\r\n1234\r\n4\r\n12"), raise_exceptions=True)
>>> c.read() + c.read()
Traceback (most recent call last):
ChunkedDataException: Ran out of data before end of chunk

"""

from io import BytesIO
from pywb.utils.bufferedreaders import ChunkedDataReader
from pywb.utils.bufferedreaders import DecompressingBufferedReader
from pywb.utils.loaders import LimitReader

from pywb import get_test_dir

import zlib

test_cdx_dir = get_test_dir() + 'cdx/'
test_zip_dir = get_test_dir() + 'zipcdx/'


def compress(buff):
    compressobj = zlib.compressobj(6, zlib.DEFLATED, zlib.MAX_WBITS + 16)
    compressed = compressobj.compress(buff)
    compressed += compressobj.flush()

    return compressed

# plain "inflate"
def compress_alt(buff):
    compressobj = zlib.compressobj(6, zlib.DEFLATED)
    compressed = compressobj.compress(buff)
    compressed += compressobj.flush()
    # drop gzip headers/tail
    compressed = compressed[2:-4]

    return compressed

if __name__ == "__main__":
    import doctest
    doctest.testmod()
