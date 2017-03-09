from warcio.bufferedreaders import DecompressingBufferedReader
from warcio.recordloader import ArcWarcRecordLoader
from pywb.utils.loaders import BlockLoader


#=================================================================
class BlockArcWarcRecordLoader(ArcWarcRecordLoader):
    def __init__(self, loader=None, cookie_maker=None, block_size=8192, *args, **kwargs):
        if not loader:
            loader = BlockLoader(cookie_maker=cookie_maker)

        self.loader = loader
        self.block_size = block_size
        super(BlockArcWarcRecordLoader, self).__init__(*args, **kwargs)

    def load(self, url, offset, length, no_record_parse=False):
        """ Load a single record from given url at offset with length
        and parse as either warc or arc record
        """
        try:
            length = int(length)
        except:
            length = -1

        stream = self.loader.load(url, int(offset), length)
        decomp_type = 'gzip'

        # Create decompressing stream
        stream = DecompressingBufferedReader(stream=stream,
                                             decomp_type=decomp_type,
                                             block_size=self.block_size)

        return self.parse_record_stream(stream, no_record_parse=no_record_parse)
