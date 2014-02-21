import os
import collections
import itertools
import logging

from cdxsource import CDXSource
from cdxobject import IDXObject

from pywb.utils.loaders import FileLoader
from pywb.utils.loaders import SeekableTextFileReader
from pywb.utils.bufferedreaders import DecompressingBufferedReader
from pywb.utils.binsearch import iter_range, linearsearch


#=================================================================
class ZipBlock:
    def __init__(self, part, offset, length, count):
        self.part = part
        self.offset = offset
        self.length = length
        self.count = count


#=================================================================
def readline_to_iter(stream):
    try:
        count = 0
        buff = stream.readline()
        while buff:
            count += 1
            yield buff
            buff = stream.readline()

    finally:
        stream.close()


#=================================================================
class ZipNumCluster(CDXSource):
    def __init__(self, summary, loc=None):
        if not loc:
            splits = os.path.splitext(summary)
            loc = splits[0] + '.loc'

        self.summary = summary
        self.loc = loc
        self.loc_map = self.load_loc(loc)

    @staticmethod
    def load_loc(loc_file):
        loc_map = {}
        with open(loc_file) as fh:
            for line in fh:
                parts = line.rstrip().split('\t')
                loc_map[parts[0]] = parts[1:]

        return loc_map

    def lookup_loc(self, part):
        return self.loc_map[part]

    def load_cdx(self, params):
        reader = SeekableTextFileReader(self.summary)

        idx_iter = iter_range(reader,
                              params['key'],
                              params['end_key'],
                              prev_size=1)

        if params.get('showPagedIndex'):
            params['proxyAll'] = True
            return idx_iter
        else:
            blocks = self.idx_to_cdx(idx_iter, params)

            def gen_cdx():
                for blk in blocks:
                    for cdx in blk:
                        yield cdx

            return gen_cdx()

    def idx_to_cdx(self, idx_iter, params):
        block = None
        max_blocks = 1

        for idx in idx_iter:
            idx = IDXObject(idx)

            if (block and block.part == idx['part'] and
                block.offset + block.length == idx['offset'] and
                block.count < max_blocks):

                    block.length += idx['length']
                    block.count += 1

            else:
                if block:
                    yield self.block_to_cdx_iter(block, params)

                block = ZipBlock(idx['part'], idx['offset'], idx['length'], 1)

        if block:
            yield self.block_to_cdx_iter(block, params)

    def block_to_cdx_iter(self, block, params):
        last_exc = None
        last_traceback = None

        for location in self.lookup_loc(block.part):
            try:
                return self.load_block(location, block, params)
            except Exception as exc:
                last_exc = exc
                import sys
                last_traceback = sys.exc_info()[2]

        if last_exc:
            raise exc, None, last_traceback
        else:
            raise Exception('No Locations Found for: ' + block.part)

    def load_block(self, location, block, params):
        if (logging.getLogger().getEffectiveLevel() <= logging.DEBUG):
            msg = 'Loading {block.count} blocks from {location}:\
{block.offset}+{block.length}'.format(block=block, location=location)
            logging.debug(msg)

        reader = FileLoader().load(location,
                                   block.offset,
                                   block.length)

        # read whole zip block into buffer
        reader = DecompressingBufferedReader(reader,
                                             decomp_type='gzip',
                                             block_size=block.length)

        iter_ = readline_to_iter(reader)

        # start bound
        iter_ = linearsearch(iter_, params['key'])

        # end bound
        end = params['end_key']
        iter_ = itertools.takewhile(lambda line: line < end, iter_)
        return iter_
