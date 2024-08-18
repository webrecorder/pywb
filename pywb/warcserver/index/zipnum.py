import datetime
import itertools
import json
import logging
import os
from io import BytesIO

import six
from warcio.bufferedreaders import gzip_decompressor

from pywb.utils.binsearch import iter_range, linearsearch, search
from pywb.utils.io import no_except_close
from pywb.utils.loaders import BlockLoader, read_last_line
from pywb.warcserver.index.cdxobject import CDXException, CDXObject, IDXObject
# from pywb.warcserver.index.cdxsource import CDXSource
from pywb.warcserver.index.indexsource import BaseIndexSource
from pywb.warcserver.index.query import CDXQuery


# ============================================================================
class ZipBlocks(object):
    def __init__(self, part, offset, length, count):
        self.part = part
        self.offset = offset
        self.length = length
        self.count = count


# ============================================================================
class AlwaysJsonResponse(dict):
    def to_json(self, *args):
        return json.dumps(self)

    def to_text(self, *args):
        return json.dumps(self)

    def to_cdxj(self, *args):
        return json.dumps(self)


# ============================================================================
#TODO: see if these could be combined with warc path resolvers

class LocMapResolver(object):
    """ Lookup shards based on a file mapping
    shard name to one or more paths. The entries are
    tab delimited.
    """
    def __init__(self, loc_summary, loc_filename):
        # initial loc map
        self.loc_map = {}
        self.loc_mtime = 0
        if not loc_filename:
            splits = os.path.splitext(loc_summary)
            loc_filename = splits[0] + '.loc'
        self.loc_filename = loc_filename

        self.load_loc()

    def load_loc(self):
        # check modified time of current file before loading
        new_mtime = os.path.getmtime(self.loc_filename)
        if (new_mtime == self.loc_mtime):
            return

        # update loc file mtime
        self.loc_mtime = new_mtime

        local_dir = os.path.dirname(self.loc_filename)

        def res_path(pathname):
            if '://' not in pathname:
                pathname = os.path.join(local_dir, pathname)
            return pathname

        logging.debug('Loading loc from: ' + self.loc_filename)
        with open(self.loc_filename, 'r') as fh:
            for line in fh:
                parts = line.rstrip().split('\t')

                paths = [res_path(pathname) for pathname in parts[1:]]
                self.loc_map[parts[0]] = paths

    def __call__(self, part, query):
        return self.loc_map[part]


# ============================================================================
class LocPrefixResolver(object):
    """ Use a prefix lookup, where the prefix can either be a fixed
    string or can be a regex replacement of the index summary path
    """
    def __init__(self, loc_summary, loc_config):
        import re
        loc_match = loc_config.get('match', '().*')
        loc_replace = loc_config['replace']
        loc_summary = os.path.dirname(loc_summary) + '/'
        self.prefix = re.sub(loc_match, loc_replace, loc_summary)

    def load_loc(self):
        pass

    def __call__(self, part, query):
        return [self.prefix + part]


# ============================================================================
class ZipNumIndexSource(BaseIndexSource):
    DEFAULT_RELOAD_INTERVAL = 10  # in minutes
    DEFAULT_MAX_BLOCKS = 10
    IDX_EXT = ('.idx', '.summary')

    def __init__(self, summary, config=None):
        self.max_blocks = self.DEFAULT_MAX_BLOCKS

        self.loc_resolver = None
        self.config = config or {}

        loc = None
        cookie_maker = None
        reload_ival = self.DEFAULT_RELOAD_INTERVAL

        if config:
            loc = config.get('shard_index_loc')
            cookie_maker = config.get('cookie_maker')

            self.max_blocks = config.get('max_blocks', self.max_blocks)

            reload_ival = config.get('reload_interval', reload_ival)

        if isinstance(loc, dict):
            self.loc_resolver = LocPrefixResolver(summary, loc)
        else:
            self.loc_resolver = LocMapResolver(summary, loc)

        self.summary = summary

        # reload interval
        self.loc_update_time = datetime.datetime.now(datetime.timezone.utc)
        self.reload_interval = datetime.timedelta(minutes=reload_ival)

        self.blk_loader = BlockLoader(cookie_maker=cookie_maker)

    def load_index(self, params):
        self.loc_resolver.load_loc()
        return self._do_load_cdx(self.summary, CDXQuery(params))

    def _do_load_cdx(self, filename, query):
        reader = open(filename, 'rb')

        idx_iter = self.compute_page_range(reader, query)

        if query.secondary_index_only:
            def gen_idx():
                for idx in idx_iter:
                    yield IDXObject(idx)

            return gen_idx()

        if query.page_count:
            return idx_iter

        blocks = self.idx_to_cdx(idx_iter, query)

        def gen_cdx():
            for blk in blocks:
                for cdx in blk:
                    yield CDXObject(cdx)

        return gen_cdx()

    def _page_info(self, pages, pagesize, blocks):
        info = AlwaysJsonResponse(
                    pages=pages,
                    pageSize=pagesize,
                    blocks=blocks)

        return info

    def compute_page_range(self, reader, query):
        pagesize = query.page_size
        if not pagesize:
            pagesize = self.max_blocks
        else:
            try:
                pagesize = int(pagesize)
            except ValueError:
                msg = 'Invalid value for pageSize= param: {}'
                raise CDXException(msg.format(pagesize))

        last_line = None

        # Get End
        end_iter = search(reader, query.end_key, prev_size=1)

        try:
            end_line = six.next(end_iter)
        except StopIteration:
            last_line = read_last_line(reader)
            end_line = last_line

        # Get Start
        first_iter = iter_range(reader,
                                query.key,
                                query.end_key,
                                prev_size=1)

        try:
            first_line = six.next(first_iter)
        except StopIteration:
            if end_line == last_line and query.key >= last_line:
                first_line = last_line
            else:
                no_except_close(reader)
                if query.page_count:
                    yield self._page_info(0, pagesize, 0)
                return

        first = IDXObject(first_line)

        end = IDXObject(end_line)

        try:
            blocks = end['lineno'] - first['lineno']
            total_pages = int(blocks / pagesize) + 1
        except:
            blocks = -1
            total_pages = 1

        if query.page_count:
            # same line, so actually need to look at cdx
            # to determine if it exists
            if blocks == 0:
                try:
                    block_cdx_iter = self.idx_to_cdx([first_line], query)
                    block = six.next(block_cdx_iter)
                    cdx = six.next(block)
                except StopIteration:
                    total_pages = 0
                    blocks = -1

            yield self._page_info(total_pages, pagesize, blocks + 1)
            no_except_close(reader)
            return

        curr_page = query.page
        if curr_page >= total_pages or curr_page < 0:
            msg = 'Page {0} invalid: First Page is 0, Last Page is {1}'
            no_except_close(reader)
            raise CDXException(msg.format(curr_page, total_pages - 1))

        startline = curr_page * pagesize
        endline = startline + pagesize - 1
        if blocks >= 0:
            endline = min(endline, blocks)

        if curr_page == 0:
            yield first_line
        else:
            startline -= 1

        try:
            idxiter = itertools.islice(first_iter, startline, endline)
            for idx in idxiter:
                yield idx
        except Exception:
            pass
        finally:
            no_except_close(reader)

    def search_by_line_num(self, reader, line):  # pragma: no cover
        def line_cmp(line1, line2):
            line1_no = int(line1.rsplit(b'\t', 1)[-1])
            line2_no = int(line2.rsplit(b'\t', 1)[-1])
            return cmp(line1_no, line2_no)

        line_iter = search(reader, line, compare_func=line_cmp)
        yield six.next(line_iter)

    def idx_to_cdx(self, idx_iter, query):
        blocks = None
        ranges = []

        for idx in idx_iter:
            idx = IDXObject(idx)

            if (blocks and blocks.part == idx['part'] and
                blocks.offset + blocks.length == idx['offset'] and
                blocks.count < self.max_blocks):

                    blocks.length += idx['length']
                    blocks.count += 1
                    ranges.append(idx['length'])

            else:
                if blocks:
                    yield self.block_to_cdx_iter(blocks, ranges, query)

                blocks = ZipBlocks(idx['part'],
                                   idx['offset'],
                                   idx['length'],
                                   1)

                ranges = [blocks.length]

        if blocks:
            yield self.block_to_cdx_iter(blocks, ranges, query)

    def block_to_cdx_iter(self, blocks, ranges, query):
        last_exc = None
        last_traceback = None

        try:
            locations = self.loc_resolver(blocks.part, query)
        except:
            raise Exception('No Locations Found for: ' + blocks.part)

        for location in self.loc_resolver(blocks.part, query):
            try:
                return self.load_blocks(location, blocks, ranges, query)
            except Exception as exc:
                last_exc = exc
                import sys
                last_traceback = sys.exc_info()[2]

        if last_exc:
            six.reraise(Exception, last_exc, last_traceback)
            #raise last_exc
        else:
            raise Exception('No Locations Found for: ' + blocks.part)

    def load_blocks(self, location, blocks, ranges, query):
        """ Load one or more blocks of compressed cdx lines, return
        a line iterator which decompresses and returns one line at a time,
        bounded by query.key and query.end_key
        """
        if (logging.getLogger().getEffectiveLevel() <= logging.DEBUG):
            msg = 'Loading {b.count} blocks from {loc}:{b.offset}+{b.length}'
            logging.debug(msg.format(b=blocks, loc=location))

        reader = self.blk_loader.load(location, blocks.offset, blocks.length)

        def decompress_block(range_):
            decomp = gzip_decompressor()
            buff = decomp.decompress(reader.read(range_))
            for line in BytesIO(buff):
                yield line

        def iter_blocks(reader):
            try:
                for r in ranges:
                    yield decompress_block(r)
            finally:
                no_except_close(reader)

        # iterate over all blocks
        iter_ = itertools.chain.from_iterable(iter_blocks(reader))

        # start bound
        iter_ = linearsearch(iter_, query.key)

        # end bound
        iter_ = itertools.takewhile(lambda line: line < query.end_key, iter_)
        return iter_

    def __repr__(self):
        return 'ZipNumIndexSource({0}, {1})'.format(self.summary, self.config)

    def __str__(self):
        return 'zipnum'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.summary == other.summary and
                self.config == other.config)

    @classmethod
    def init_from_string(cls, value):
        is_zipnum = False
        if value.startswith('zipnum+'):
            value = value[7:]
            is_zipnum = True

        if value.startswith('file://'):
            value = value[7:]

        if is_zipnum or value.endswith(cls.IDX_EXT):
            return cls(value, None)

    @classmethod
    def init_from_config(cls, config):
        if config['type'] != 'zipnum':
            return

        return cls(config['path'], config)

