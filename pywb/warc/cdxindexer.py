import os
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from bisect import insort

from io import BytesIO

from archiveiterator import create_index_iter


#=================================================================
class CDXWriter(object):
    def __init__(self, out):
        self.out = out

    def __enter__(self):
        self.out.write(' CDX N b a m s k r M S V g\n')
        return self

    def write(self, entry, filename):
        self.write_cdx_line(self.out, entry, filename)

    def __exit__(self, *args):
        return False

    @staticmethod
    def write_cdx_line(out, entry, filename):
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
class SortedCDXWriter(CDXWriter):
    def __init__(self, out):
        super(SortedCDXWriter, self).__init__(out)
        self.sortlist = []

    def write(self, entry, filename):
        outbuff = BytesIO()
        self.write_cdx_line(outbuff, entry, filename)

        insort(self.sortlist, outbuff.getvalue())

    def __exit__(self, *args):
        self.out.write(''.join(self.sortlist))
        return False


#=================================================================
def iter_file_or_dir(inputs):
    for input_ in inputs:
        if not os.path.isdir(input_):
            yield input_, os.path.basename(input_)
        else:
            for filename in os.listdir(input_):
                yield os.path.join(input_, filename), filename


#=================================================================
def index_to_file(inputs, output, sort,
                  surt_ordered, include_all, append_post_query):
    if output == '-':
        outfile = sys.stdout
    else:
        outfile = open(output, 'w')

    if sort:
        writer_cls = SortedCDXWriter
    else:
        writer_cls = CDXWriter

    with writer_cls(outfile) as writer:
        for fullpath, filename in iter_file_or_dir(inputs):
            with open(fullpath, 'r') as infile:
                write_index(writer, filename, infile,
                            surt_ordered, append_post_query, include_all)

#=================================================================
def index_to_dir(inputs, output, sort,
                 surt_ordered, include_all, append_post_query):

    if sort:
        writer_cls = SortedCDXWriter
    else:
        writer_cls = CDXWriter

    for fullpath, filename in iter_file_or_dir(inputs):

        outpath = cdx_filename(filename)
        outpath = os.path.join(output, outpath)

        with open(outpath, 'w') as outfile:
            with writer_cls(outfile) as writer:
                with open(fullpath, 'r') as infile:
                    write_index(writer, filename, infile,
                                surt_ordered, append_post_query, include_all)

#=================================================================
def remove_ext(filename):
    for ext in ('.arc', '.arc.gz', '.warc', '.warc.gz'):
        if filename.endswith(ext):
            filename = filename[:-len(ext)]
            break

    return filename


#=================================================================
def cdx_filename(filename):
    return remove_ext(filename) + '.cdx'


#=================================================================
def write_index(writer, filename, infile,
                surt_ordered, append_post, include_all):

    entry_iter = create_index_iter(infile,
                                   surt_ordered=surt_ordered,
                                   append_post=append_post,
                                   include_all=include_all)

    for entry in entry_iter:
        writer.write(entry, filename)


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

    parser.add_argument('-u', '--unsurt',
                        action='store_true',
                        help=unsurt_help)

    parser.add_argument('output', nargs='?', default='-', help=output_help)
    parser.add_argument('inputs', nargs='+', help=input_help)

    cmd = parser.parse_args(args=args)
    if cmd.output != '-' and os.path.isdir(cmd.output):
        index_to_dir(cmd.inputs, cmd.output, cmd.sort,
                     not cmd.unsurt, cmd.allrecords, cmd.postappend)
    else:
        index_to_file(cmd.inputs, cmd.output, cmd.sort,
                      not cmd.unsurt, cmd.allrecords, cmd.postappend)


if __name__ == '__main__':
    main()
