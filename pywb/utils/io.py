import zlib
from contextlib import closing, contextmanager

from warcio.utils import BUFF_SIZE
from warcio.limitreader import LimitReader
from tempfile import SpooledTemporaryFile


def close_raw(r):
    """Attempts to call the close and release_conn methods
    on the supplied request objects raw property.
    If the raw property is not found full_close is used.

    This method does not raise exceptions

    :param r: The object to be closed
    :return: None
    :rtype: None
    """
    raw = getattr(r, 'raw', None)
    if raw is not None:
        close = getattr(raw, 'close', None)
        if close is not None:
            try:
                close()
            except Exception:
                pass
        release_conn = getattr(raw, 'release_conn', None)
        if release_conn is not None:
            try:
                release_conn()
            except Exception:
                pass
    else:
        full_close(r)


def full_close(closable_object):
    """Attempts to call the close and release_conn methods
    on the supplied closable object.

    This method does not raise exceptions

    :param closable_object: The object to be fully closed
    :return: None
    :rtype: None
    """
    close = getattr(closable_object, 'close', None)
    if close is not None:
        try:
            close()
        except Exception:
            pass
    release_conn = getattr(closable_object, 'release_conn', None)
    if release_conn is not None:
        try:
            release_conn()
        except Exception:
            pass


def close_fh(fh):
    """Calls the close method on the supplied file handle.

    This method does not raise exceptions
    :param fh: The file handle to be closed
    :return: None
    :rtype: None
    """
    try:
        fh.close()
    except Exception:
        pass

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
        full_close(stream)


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

