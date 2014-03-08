from io import BytesIO
import zlib


#=================================================================
def gzip_decompressor():
    """
    Decompressor which can handle decompress gzip stream
    """
    return zlib.decompressobj(16 + zlib.MAX_WBITS)


#=================================================================
class DecompressingBufferedReader(object):
    """
    A wrapping line reader which wraps an existing reader.
    Read operations operate on underlying buffer, which is filled to
    block_size (1024 default)

    If an optional decompress type is specified,
    data is fed through the decompressor when read from the buffer.
    Currently supported decompression: gzip

    If decompression fails on first try, data is assumed to be decompressed
    and no exception is thrown. If a failure occurs after data has been
    partially decompressed, the exception is propagated.

    """

    DECOMPRESSORS = {'gzip': gzip_decompressor}

    def __init__(self, stream, block_size=1024, decomp_type=None):
        self.stream = stream
        self.block_size = block_size

        if decomp_type:
            try:
                self.decompressor = self.DECOMPRESSORS[decomp_type.lower()]()
            except KeyError:
                raise Exception('Decompression type not supported: ' +
                                decomp_type)
        else:
            self.decompressor = None

        self.buff = None
        self.num_read = 0
        self.buff_size = 0

    def _fillbuff(self, block_size=None):
        if not block_size:
            block_size = self.block_size

        if not self.buff or self.buff.tell() == self.buff_size:
            data = self.stream.read(block_size)
            self._process_read(data)

    def _process_read(self, data):
        data = self._decompress(data)
        self.buff_size = len(data)
        self.num_read += self.buff_size
        self.buff = BytesIO(data)

    def _decompress(self, data):
        if self.decompressor and data:
            try:
                data = self.decompressor.decompress(data)
            except Exception:
                # if first read attempt, assume non-gzipped stream
                if self.num_read == 0:
                    self.decompressor = None
                # otherwise (partly decompressed), something is wrong
                else:
                    raise
        return data

    def read(self, length=None):
        """
        Fill bytes and read some number of bytes
        (up to length if specified)
        < length bytes may be read if reached the end of input
        or at a buffer boundary. If at a boundary, the subsequent
        call will fill buffer anew.
        """
        self._fillbuff()
        return self.buff.read(length)

    def readline(self, length=None):
        """
        Fill buffer and read a full line from the buffer
        (up to specified length, if provided)
        If no newline found at end, try filling buffer again in case
        at buffer boundary.
        """
        self._fillbuff()
        linebuff = self.buff.readline(length)
        # we may be at a boundary
        while not linebuff.endswith('\n'):
            if length:
                length -= len(linebuff)
                if length <= 0:
                    break

            self._fillbuff()

            if self.buff_size == 0:
                break

            linebuff += self.buff.readline(length)

        return linebuff

    def close(self):
        if self.stream:
            self.stream.close()
            self.stream = None


#=================================================================
class ChunkedDataException(Exception):
    pass


#=================================================================
class ChunkedDataReader(DecompressingBufferedReader):
    r"""
    A ChunkedDataReader is a BufferedReader which also supports de-chunking
    of the data if it happens to be http 'chunk-encoded'.

    If at any point the chunked header is not available, the stream is
    assumed to not be chunked and no more dechunking occurs.

    Properly formatted chunked data:
    >>> c = ChunkedDataReader(BytesIO("4\r\n1234\r\n0\r\n\r\n"));
    >>> c.read() + c.read()
    '1234'

    Non-chunked data:
    >>> ChunkedDataReader(BytesIO("xyz123!@#")).read()
    'xyz123!@#'

    Starts like chunked data, but isn't:
    >>> c = ChunkedDataReader(BytesIO("1\r\nxyz123!@#"));
    >>> c.read() + c.read()
    '1\r\nx123!@#'

    Chunked data cut off part way through:
    >>> c = ChunkedDataReader(BytesIO("4\r\n1234\r\n4\r\n12"));
    >>> c.read() + c.read()
    '123412'
    """

    all_chunks_read = False
    not_chunked = False

    # if False, we'll use best-guess fallback for parse errors
    raise_chunked_data_exceptions = False

    def _fillbuff(self, block_size=None):
        if self.not_chunked:
            return super(ChunkedDataReader, self)._fillbuff(block_size)

        if self.all_chunks_read:
            return

        if not self.buff or self.buff.tell() >= self.buff_size:
            length_header = self.stream.readline(64)
            self._data = ''

            try:
                self._try_decode(length_header)
            except ChunkedDataException:
                if self.raise_chunked_data_exceptions:
                    raise

                # Can't parse the data as chunked.
                # It's possible that non-chunked data is served
                # with a Transfer-Encoding: chunked.
                # Treat this as non-chunk encoded from here on.
                self._process_read(length_header + self._data)
                self.not_chunked = True

    def _try_decode(self, length_header):
        # decode length header
        try:
            chunk_size = int(length_header.strip().split(';')[0], 16)
        except ValueError:
            raise ChunkedDataException("Couldn't decode length header " +
                                       length_header)

        if not chunk_size:
            # chunk_size 0 indicates end of file
            self.all_chunks_read = True
            #self._process_read('')
            return

        data_len = len(self._data)

        # read chunk
        while data_len < chunk_size:
            new_data = self.stream.read(chunk_size - data_len)

            # if we unexpectedly run out of data,
            # either raise an exception or just stop reading,
            # assuming file was cut off
            if not new_data:
                if self.raise_chunked_data_exceptions:
                    msg = 'Ran out of data before end of chunk'
                    raise ChunkedDataException(msg)
                else:
                    chunk_size = data_len
                    self.all_chunks_read = True

            self._data += new_data
            data_len = len(self._data)

        # if we successfully read a block without running out,
        # it should end in \r\n
        if not self.all_chunks_read:
            clrf = self.stream.read(2)
            if clrf != '\r\n':
                raise ChunkedDataException("Chunk terminator not found.")

        # hand to base class for further processing
        self._process_read(self._data)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
