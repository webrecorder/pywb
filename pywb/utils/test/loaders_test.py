#=================================================================
"""
# LimitReader Tests
>>> LimitReader(StringIO.StringIO('abcdefghjiklmnopqrstuvwxyz'), 10).read(26)
'abcdefghji'

>>> LimitReader(StringIO.StringIO('abcdefghjiklmnopqrstuvwxyz'), 8).readline(26)
'abcdefgh'

>>> read_multiple(LimitReader(StringIO.StringIO('abcdefghjiklmnopqrstuvwxyz'), 10), [2, 2, 20])
'efghji'

# FileLoader Tests (includes LimitReader)
# Ensure attempt to read more than 100 bytes, reads exactly 100 bytes
>>> len(FileLoader().load(test_cdx_dir + 'iana.cdx', 0, 100).read('400'))
100

# SeekableTextFileReader Test
>>> sr = SeekableTextFileReader(test_cdx_dir + 'iana.cdx')
>>> sr.getsize()
30399

>>> seek_read_full(sr, 100)
'org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200826 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 34054 620049 iana.warc.gz\\n'

#DecompressingBufferedReader readline()
>>> DecompressingBufferedReader(open(test_cdx_dir + 'iana.cdx', 'rb')).readline()
' CDX N b a m s k r M S V g\\n'

#DecompressingBufferedReader readline() with decompression
>>> DecompressingBufferedReader(open(test_cdx_dir + 'iana.cdx.gz', 'rb'), decomp_type = 'gzip').readline()
' CDX N b a m s k r M S V g\\n'

>>> HttpLoader(HMACCookieMaker('test', 'test', 5)).load('http://example.com', 41, 14).read()
'Example Domain'
"""


#=================================================================
import os
import StringIO
from pywb.utils.loaders import FileLoader, HttpLoader, HMACCookieMaker
from pywb.utils.loaders import LimitReader, SeekableTextFileReader
from pywb.utils.bufferedreaders import DecompressingBufferedReader

from pywb import get_test_dir
#test_cdx_dir = os.path.dirname(os.path.realpath(__file__)) + '/../sample-data/'
test_cdx_dir = get_test_dir() + 'cdx/'


def read_multiple(reader, inc_reads):
    result = None
    for x in inc_reads:
        result = reader.read(x)
    return result


def seek_read_full(seekable_reader, offset):
    seekable_reader.seek(offset)
    seekable_reader.readline() #skip
    return seekable_reader.readline()



if __name__ == "__main__":
    import doctest
    doctest.testmod()


