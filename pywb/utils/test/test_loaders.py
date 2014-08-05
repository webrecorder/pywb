#=================================================================
r"""
# LimitReader Tests
>>> LimitReader(BytesIO('abcdefghjiklmnopqrstuvwxyz'), 10).read(26)
'abcdefghji'

>>> LimitReader(BytesIO('abcdefghjiklmnopqrstuvwxyz'), 8).readline(26)
'abcdefgh'

>>> read_multiple(LimitReader(BytesIO('abcdefghjiklmnopqrstuvwxyz'), 10), [2, 2, 20])
'efghji'

# zero-length read
>>> LimitReader(BytesIO('a'), 0).readline(0)
''

# don't wrap if invalid length
>>> b = BytesIO('b')
>>> LimitReader.wrap_stream(b, 'abc') == b
True

# BlockLoader Tests (includes LimitReader)
# Ensure attempt to read more than 100 bytes, reads exactly 100 bytes
>>> len(BlockLoader().load(test_cdx_dir + 'iana.cdx', 0, 100).read('400'))
100

# no length specified, read full amount requested
>>> len(BlockLoader().load('file://' + test_cdx_dir + 'example.cdx', 0, -1).read(400))
400

# HMAC Cookie Maker
>>> BlockLoader(HMACCookieMaker('test', 'test', 5)).load('http://example.com', 41, 14).read()
'Example Domain'

# fixed cookie, range request
>>> BlockLoader('some=value').load('http://example.com', 41, 14).read()
'Example Domain'

# range request
>>> BlockLoader().load('http://example.com', 1262).read()
'</html>\n'

# test with extra id, ensure 4 parts of the A-B=C-D form are present
>>> len(re.split('[-=]', HMACCookieMaker('test', 'test', 5).make('extra')))
4
"""


#=================================================================
import re
from io import BytesIO
from pywb.utils.loaders import BlockLoader, HMACCookieMaker
from pywb.utils.loaders import LimitReader

from pywb import get_test_dir

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


