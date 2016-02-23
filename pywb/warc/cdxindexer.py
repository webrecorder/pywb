import os
import sys

# Use ujson if available
try:
    from ujson import dumps as ujson_dumps

    try:
        assert (ujson_dumps('http://example.com/',
                            escape_forward_slashes=False) ==
                '"http://example.com/"')
    except Exception as e:  # pragma: no cover
        sys.stderr.write('ujson w/o forward-slash escaping not available,\
defaulting to regular json\n')
        raise

    def json_encode(obj):
        return ujson_dumps(obj, escape_forward_slashes=False)

except:  # pragma: no cover
    from json import dumps as json_encode

try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict


from argparse import ArgumentParser, RawTextHelpFormatter
from bisect import insort

from six import StringIO

from pywb.warc.archiveiterator import DefaultRecordParser
import codecs
import six


#=================================================================
class BaseCDXWriter(object):
    def __init__(self, out):
        self.out = codecs.getwriter('utf-8')(out)
        #self.out = out

    def __enter__(self):
        self._write_header()
        return self

    def write(self, entry, filename):
        if not entry.get('url') or not entry.get('urlkey'):
            return

        if entry.record.rec_type == 'warcinfo':
            return

        self.write_cdx_line(self.out, entry, filename)

    def __exit__(self, *args):
        return False


#=================================================================
class CDXJ(object):
    def _write_header(self):
        pass

    def write_cdx_line(self, out, entry, filename):
        out.write(entry['urlkey'])
        out.write(' ')
        out.write(entry['timestamp'])
        out.write(' ')

        outdict = OrderedDict()

        for n, v in six.iteritems(entry):
            if n in ('urlkey', 'timestamp'):
                continue

            if n.startswith('_'):
                continue

            if not v or v == '-':
                continue

            outdict[n] = v

        outdict['filename'] = filename
        out.write(json_encode(outdict))
        out.write('\n')


#=================================================================
class CDX09(object):
    def _write_header(self):
        self.out.write(' CDX N b a m s k r V g\n')

    def write_cdx_line(self, out, entry, filename):
        out.write(entry['urlkey'])
        out.write(' ')
        out.write(entry['timestamp'])
        out.write(' ')
        out.write(entry['url'])
        out.write(' ')
        out.write(entry['mime'])
        out.write(' ')
        out.write(entry['status'])
        out.write(' ')
        out.write(entry['digest'])
        out.write(' - ')
        out.write(entry['offset'])
        out.write(' ')
        out.write(filename)
        out.write('\n')


#=================================================================
class CDX11(object):
    def _write_header(self):
        self.out.write(' CDX N b a m s k r M S V g\n')

    def write_cdx_line(self, out, entry, filename):
        out.write(entry['urlkey'])
        out.write(' ')
        out.write(entry['timestamp'])
        out.write(' ')
        out.write(entry['url'])
        out.write(' ')
        out.write(entry['mime'])
        out.write(' ')
        out.write(entry['status'])
        out.write(' ')
        out.write(entry['digest'])
        out.write(' - - ')
        out.write(entry['length'])
        out.write(' ')
        out.write(entry['offset'])
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
        self.out = StringIO()
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
def _resolve_rel_path(path, rel_root):
    path = os.path.relpath(path, rel_root)
    if os.path.sep != '/':  #pragma: no cover
        path = path.replace(os.path.sep, '/')
    return path


#=================================================================
def iter_file_or_dir(inputs, recursive=True, rel_root=None):
    for input_ in inputs:
        if not os.path.isdir(input_):
            if not rel_root:
                filename = os.path.basename(input_)
            else:
                filename = _resolve_rel_path(input_, rel_root)

            yield input_, filename

        elif not recursive:
            for filename in os.listdir(input_):
                if filename.endswith(ALLOWED_EXT):
                    full_path = os.path.join(input_, filename)
                    if rel_root:
                        filename = _resolve_rel_path(full_path, rel_root)
                    yield full_path, filename

        else:
            for root, dirs, files in os.walk(input_):
                for filename in files:
                    if filename.endswith(ALLOWED_EXT):
                        full_path = os.path.join(root, filename)
                        if not rel_root:
                            rel_root = input_
                        rel_path = _resolve_rel_path(full_path, rel_root)
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
    if options.get('minimal'):
        options['cdxj'] = True

    writer_cls = options.get('writer_cls')
    if writer_cls:
        if not options.get('writer_add_mixin'):
            return writer_cls
    elif options.get('sort'):
        writer_cls = SortedCDXWriter
    else:
        writer_cls = BaseCDXWriter

    if options.get('cdxj'):
        format_mixin = CDXJ
    elif options.get('cdx09'):
        format_mixin = CDX09
    else:
        format_mixin = CDX11

    class CDXWriter(writer_cls, format_mixin):
        pass

    return CDXWriter


#=================================================================
def write_multi_cdx_index(output, inputs, **options):
    recurse = options.get('recurse', False)
    rel_root = options.get('rel_root')

    # write one cdx per dir
    if output != '-' and os.path.isdir(output):
        for fullpath, filename in iter_file_or_dir(inputs,
                                                   recurse,
                                                   rel_root):
            outpath = cdx_filename(filename)
            outpath = os.path.join(output, outpath)

            with open(outpath, 'wb') as outfile:
                with open(fullpath, 'rb') as infile:
                    writer = write_cdx_index(outfile, infile, filename,
                                             **options)

        return writer

    # write to one cdx file
    else:
        if output == '-':
            if hasattr(sys.stdout, 'buffer'):
                outfile = sys.stdout.buffer
            else:
                outfile = sys.stdout
        else:
            outfile = open(output, 'wb')

        writer_cls = get_cdx_writer_cls(options)
        record_iter = DefaultRecordParser(**options)

        with writer_cls(outfile) as writer:
            for fullpath, filename in iter_file_or_dir(inputs,
                                                       recurse,
                                                       rel_root):
                with open(fullpath, 'rb') as infile:
                    entry_iter = record_iter(infile)

                    for entry in entry_iter:
                        writer.write(entry, filename)

        return writer


#=================================================================
def write_cdx_index(outfile, infile, filename, **options):
    #filename = filename.encode(sys.getfilesystemencoding())

    writer_cls = get_cdx_writer_cls(options)

    with writer_cls(outfile) as writer:
        entry_iter = DefaultRecordParser(**options)(infile)

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
Sort the output to each file before writing to create a total ordering
"""

    unsurt_help = """
Convert SURT (Sort-friendly URI Reordering Transform) back to regular
urls for the cdx key. Default is to use SURT keys.
Not-recommended for new cdx, use only for backwards-compatibility.
"""

    verify_help = """
Verify HTTP protocol (1.0/1.1) status in response records and http verb
on request records, ensuring the protocol or verb matches the expected list.
Raise an exception on failure. (This was previously the default behavior).
"""

    cdx09_help = """
Use older 9-field cdx format, default is 11-cdx field
"""
    minimal_json_help = """
CDX JSON output, but with minimal fields only, available  w/o parsing
http record. The fields are: canonicalized url, timestamp,
original url, digest, archive offset, archive length
and archive filename. mimetype is included to indicate warc/revisit only.

This option skips record parsing and will not work with
POST append (-p) option
"""

    json_help = """
Output CDX JSON format per line, with url timestamp first,
followed by a json dict for all other fields:
url timestamp { ... }
"""

    output_help = """
Output file or directory.
- If directory, each input file is written to a seperate output file
  with a .cdx extension
- If output is '-', output is written to stdout
"""

    input_help = """
Input file or directory.
- If directory, all archive files from that directory are read
"""

    allrecords_help = """
Include All records.
currently includes the 'request' records in addition to all
response records
"""

    post_append_help = """
For POST requests, append form query to url key.
(Only applies to form url encoded posts)
"""

    recurse_dirs_help = """
Recurse through all subdirectories if the input is a directory
"""

    dir_root_help = """
Make CDX filenames relative to specified root directory,
instead of current working directory
"""

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

    parser.add_argument('-d', '--dir-root',
                        help=dir_root_help)

    parser.add_argument('-u', '--unsurt',
                        action='store_true',
                        help=unsurt_help)

    parser.add_argument('-v', '--verify',
                        action='store_true',
                        help=verify_help)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-9', '--cdx09',
                        action='store_true',
                        help=cdx09_help)

    group.add_argument('-j', '--cdxj',
                        action='store_true',
                        help=json_help)

    parser.add_argument('-mj', '--minimal-cdxj',
                        action='store_true',
                        help=minimal_json_help)

    parser.add_argument('output', nargs='?', default='-', help=output_help)
    parser.add_argument('inputs', nargs='+', help=input_help)

    cmd = parser.parse_args(args=args)

    write_multi_cdx_index(cmd.output, cmd.inputs,
                          sort=cmd.sort,
                          surt_ordered=not cmd.unsurt,
                          include_all=cmd.allrecords,
                          append_post=cmd.postappend,
                          recurse=cmd.recurse,
                          rel_root=cmd.dir_root,
                          verify_http=cmd.verify,
                          cdx09=cmd.cdx09,
                          cdxj=cmd.cdxj,
                          minimal=cmd.minimal_cdxj)


if __name__ == '__main__':
    main()
