import os
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from bisect import insort

from io import BytesIO

from archiveiterator import DefaultRecordIter

#=================================================================
class BaseCDXWriter(object):
    def __init__(self, out):
        self.out = out

    def __enter__(self):
        self._write_header()
        return self

    def write(self, entry, filename):
        if not entry.url or not entry.key:
            return

        if entry.record.rec_type == 'warcinfo':
            return

        self.write_cdx_line(self.out, entry, filename)

    def __exit__(self, *args):
        return False


#=================================================================
class CDX06(object):
    def _write_header(self):
        self.out.write(' CDX N b a S V g\n')

    def write_cdx_line(self, out, entry, filename):
        out.write(entry.key)
        out.write(' ')
        out.write(entry.timestamp)
        out.write(' ')
        out.write(entry.url)
        out.write(' ')
        out.write(entry.length)
        out.write(' ')
        out.write(entry.offset)
        out.write(' ')
        out.write(filename)
        out.write('\n')


#=================================================================
class CDX09(object):
    def _write_header(self):
        self.out.write(' CDX N b a m s k r V g\n')

    def write_cdx_line(self, out, entry, filename):
        out.write(entry.key)
        out.write(' ')
        out.write(entry.timestamp)
        out.write(' ')
        out.write(entry.url)
        out.write(' ')
        out.write(entry.mime)
        out.write(' ')
        out.write(entry.status)
        out.write(' ')
        out.write(entry.digest)
        out.write(' - ')
        out.write(entry.offset)
        out.write(' ')
        out.write(filename)
        out.write('\n')


#=================================================================
class CDX11(object):
    def _write_header(self):
        self.out.write(' CDX N b a m s k r M S V g\n')

    def write_cdx_line(self, out, entry, filename):
        out.write(entry.key)
        out.write(' ')
        out.write(entry.timestamp)
        out.write(' ')
        out.write(entry.url)
        out.write(' ')
        out.write(entry.mime)
        out.write(' ')
        out.write(entry.status)
        out.write(' ')
        out.write(entry.digest)
        out.write(' - - ')
        out.write(entry.length)
        out.write(' ')
        out.write(entry.offset)
        out.write(' ')
        out.write(filename)
        out.write('\n')


#=================================================================
class SortedCDXWriter(BaseCDXWriter):
    def __enter__(self):
        self.sortlist = []
        res = super(SortedCDXWriter, self).__enter__()
        self.actual_out = self.out
        return res

    def write(self, entry, filename):
        self.out = BytesIO()
        super(SortedCDXWriter, self).write(entry, filename)
        line = self.out.getvalue()
        if line:
            insort(self.sortlist, line)

    def __exit__(self, *args):
        self.actual_out.write(''.join(self.sortlist))
        return False


#=================================================================
ALLOWED_EXT = ('.arc', '.arc.gz', '.warc', '.warc.gz')


#=================================================================
def iter_file_or_dir(inputs, recursive=True):
    for input_ in inputs:
        if not os.path.isdir(input_):
            yield input_, os.path.basename(input_)

        elif not recursive:
            for filename in os.listdir(input_):
                if filename.endswith(ALLOWED_EXT):
                    yield os.path.join(input_, filename), filename

        else:
            for root, dirs, files in os.walk(input_):
                for filename in files:
                    if filename.endswith(ALLOWED_EXT):
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, input_)
                        rel_path = rel_path.replace(os.path.sep, '/')
                        yield full_path, rel_path


#=================================================================
def remove_ext(filename):
    for ext in ALLOWED_EXT:
        if filename.endswith(ext):
            filename = filename[:-len(ext)]
            break

    return filename


#=================================================================
def cdx_filename(filename):
    return remove_ext(filename) + '.cdx'


#=================================================================
def get_cdx_writer_cls(options):
    writer_cls = options.get('writer_cls')

    if writer_cls:
        if not options.get('writer_add_mixin'):
            return writer_cls
    elif options.get('sort'):
        writer_cls = SortedCDXWriter
    else:
        writer_cls = BaseCDXWriter

    if options.get('cdx09'):
        format_mixin = CDX09
    elif options.get('minimal'):
        format_mixin = CDX06
    else:
        format_mixin = CDX11

    class CDXWriter(writer_cls, format_mixin):
        pass

    return CDXWriter


#=================================================================
def write_multi_cdx_index(output, inputs, **options):
    recurse = options.get('recurse', False)

    # write one cdx per dir
    if output != '-' and os.path.isdir(output):
        for fullpath, filename in iter_file_or_dir(inputs, recurse):
            outpath = cdx_filename(filename)
            outpath = os.path.join(output, outpath)

            with open(outpath, 'wb') as outfile:
                with open(fullpath, 'rb') as infile:
                    return write_cdx_index(outfile, infile, filename,
                                           **options)

    # write to one cdx file
    else:
        if output == '-':
            outfile = sys.stdout
        else:
            outfile = open(output, 'wb')

        writer_cls = get_cdx_writer_cls(options)
        record_iter = DefaultRecordIter(**options)

        with writer_cls(outfile) as writer:
            for fullpath, filename in iter_file_or_dir(inputs, recurse):
                with open(fullpath, 'rb') as infile:
                    entry_iter = record_iter(infile)

                    for entry in entry_iter:
                        writer.write(entry, filename)

        return writer


#=================================================================
def write_cdx_index(outfile, infile, filename, **options):
    if type(filename) is unicode:
        filename = filename.encode(sys.getfilesystemencoding())

    writer_cls = get_cdx_writer_cls(options)

    with writer_cls(outfile) as writer:
        entry_iter = DefaultRecordIter(**options)(infile)

        for entry in entry_iter:
            writer.write(entry, filename)

    return writer


#=================================================================
def main(args=None):
    description = """
Generate .cdx index files for WARCs and ARCs
Compressed (.warc.gz / .arc.gz) or uncompressed (.warc / .arc) formats
are supported.
"""

    epilog = """
Some examples:

* Create "example.cdx" index from example.warc.gz
{0} ./cdx/example.cdx ./warcs/example.warc.gz

* Create "combined.cdx", a combined, sorted index of all warcs in ./warcs/
{0} --sort combined.cdx ./warcs/

* Create a sorted cdx per file in ./cdx/ for each archive file in ./warcs/
{0} --sort ./cdx/ ./warcs/
""".format(os.path.basename(sys.argv[0]))

    sort_help = """
sort the output to each file before writing to create a total ordering
"""

    unsurt_help = """
Convert SURT (Sort-friendly URI Reordering Transform) back to regular
urls for the cdx key. Default is to use SURT keys.
Not-recommended for new cdx, use only for backwards-compatibility.
"""

    cdx09_help = """
Use older 9-field cdx format, default is 11-cdx field
"""
    minimal_help = """
Use a minimal 6-field cdx format, outputing only the basic fields
needed to identiyfy record:
canonicalized url, timestamp, original url, archive offset, archive length
and archive filename.

This option skips record parsing and will not work with
POST append (-p) option
"""

    output_help = """output file or directory.
- If directory, each input file is written to a seperate output file
  with a .cdx extension
- If output is '-', output is written to stdout
"""

    input_help = """input file or directory
- If directory, all archive files from that directory are read
"""

    allrecords_help = """include all records.
currently includes the 'request' records in addition to all
response records"""

    post_append_help = """for POST requests, append
form query to url key. (Only applies to form url encoded posts)"""

    recurse_dirs_help = """recurse through all subdirectories
if input is a directory"""

    parser = ArgumentParser(description=description,
                            epilog=epilog,
                            formatter_class=RawTextHelpFormatter)

    parser.add_argument('-s', '--sort',
                        action='store_true',
                        help=sort_help)

    parser.add_argument('-a', '--allrecords',
                        action='store_true',
                        help=allrecords_help)

    parser.add_argument('-p', '--postappend',
                        action='store_true',
                        help=post_append_help)

    parser.add_argument('-r', '--recurse',
                        action='store_true',
                        help=recurse_dirs_help)

    parser.add_argument('-u', '--unsurt',
                        action='store_true',
                        help=unsurt_help)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-9', '--cdx09',
                        action='store_true',
                        help=cdx09_help)

    group.add_argument('-m', '--minimal',
                        action='store_true',
                        help=minimal_help)

    parser.add_argument('output', nargs='?', default='-', help=output_help)
    parser.add_argument('inputs', nargs='+', help=input_help)

    cmd = parser.parse_args(args=args)

    write_multi_cdx_index(cmd.output, cmd.inputs,
                          sort=cmd.sort,
                          surt_ordered=not cmd.unsurt,
                          include_all=cmd.allrecords,
                          append_post=cmd.postappend,
                          recurse=cmd.recurse,
                          cdx09=cmd.cdx09,
                          minimal=cmd.minimal)


if __name__ == '__main__':
    main()
