import zlib
from contextlib import closing, contextmanager

from warcio.utils import BUFF_SIZE
from warcio.limitreader import LimitReader
from tempfile import SpooledTemporaryFile


#=============================================================================
def StreamIter(stream, header1=None, header2=None, size=BUFF_SIZE, closer=closing):
    with closer(stream):
        if header1:
            yield header1

        if header2:
            yield header2

        while True:
            buff = stream.read(size)
            if not buff:
                break
            yield buff


#=============================================================================
@contextmanager
def call_release_conn(stream):
    try:
        yield stream
    finally:
        if hasattr(stream, 'release_conn'):
            stream.release_conn()
        else:
            stream.close()


#=============================================================================
def chunk_encode_iter(orig_iter):
    for chunk in orig_iter:
        if not len(chunk):
            continue
        chunk_len = b'%X\r\n' % len(chunk)
        yield chunk_len
        yield chunk
        yield b'\r\n'

    yield b'0\r\n\r\n'


#=============================================================================
def buffer_iter(status_headers, iterator, buff_size=BUFF_SIZE * 4):
    out = SpooledTemporaryFile(buff_size)
    size = 0

    for buff in iterator:
        size += len(buff)
        out.write(buff)

    content_length_str = str(size)
    # remove existing content length
    status_headers.replace_header('Content-Length',
                                  content_length_str)

    out.seek(0)
    return StreamIter(out)


#=============================================================================
def compress_gzip_iter(orig_iter):
    compressobj = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS + 16)
    for chunk in orig_iter:
        buff = compressobj.compress(chunk)
        if len(buff) == 0:
            continue

        yield buff

    yield compressobj.flush()


# ============================================================================
class OffsetLimitReader(LimitReader):
    def __init__(self, stream, offset, length):
        super(OffsetLimitReader, self).__init__(stream, length)
        self.offset = offset
        if offset > 0:
            self._skip_reader = LimitReader(stream, offset)
        else:
            self._skip_reader = None

    def _skip(self):
        while self._skip_reader:
            buff = self._skip_reader.read()
            if not buff:
                self._skip_reader = None

    def read(self, length=None):
        self._skip()
        return super(OffsetLimitReader, self).read(length)

    def readline(self, length=None):
        self._skip()
        return super(OffsetLimitReader, self).readline(length)

