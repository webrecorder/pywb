import os
import shutil
import sys
import logging

from pywb.utils.loaders import load_yaml_config
from pywb.utils.timeutils import timestamp20_now
from pywb.warc.cdxindexer import main as cdxindexer_main

from argparse import ArgumentParser, RawTextHelpFormatter
import heapq


#=============================================================================
class CollectionsManager(object):
    """ This utility is designed to
simplify the creation and management of web archive collections

It may be used via cmdline to setup and maintain the
directory structure expected by pywb
    """
    def __init__(self, coll_name, root_dir='collections'):
        self.root_dir = root_dir
        self.default_config = load_yaml_config('pywb/default_config.yaml')
        self.coll_name = coll_name

        self.coll_dir = os.path.join(self.root_dir, coll_name)

        self.warc_dir = self._get_dir('archive_paths')
        self.cdx_dir = self._get_dir('index_paths')
        self.static_dir = self._get_dir('static_path')
        self.templates_dir = self._get_dir('templates_dir')

    def _get_dir(self, name):
        return os.path.join(self.coll_dir,
                            self.default_config['paths'][name])

    def _create_dir(self, dirname):
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

        logging.info('Created Dir: ' + dirname)

    def add_collection(self):
        os.makedirs(self.coll_dir)
        logging.info('Created directory: ' + self.coll_dir)

        self._create_dir(self.warc_dir)
        self._create_dir(self.cdx_dir)
        self._create_dir(self.static_dir)
        self._create_dir(self.templates_dir)

    def add_warcs(self, warcs):
        if not os.path.isdir(self.warc_dir):
            if not os.path.isdir(self.coll_dir):
                raise IOError('Collection {0} does not exist'.
                              format(self.coll_name))
            else:
                raise IOError('Directory {0} does not exist'.
                              format(self.warc_dir))

        if not warcs:
            logging.info('No WARCs specified')
            return

        full_paths = []
        for filename in warcs:
            shutil.copy2(filename, self.warc_dir)
            full_paths.append(os.path.join(self.warc_dir, filename))
            logging.info('Copied ' + filename + ' to ' + self.warc_dir)

        self._index_merge_warcs(full_paths)

    def reindex(self):
        cdx_file = os.path.join(self.cdx_dir, 'index.cdx')
        logging.info('Indexing ' + self.warc_dir + ' to ' + cdx_file)
        cdxindexer_main(['-p', '-s', '-r', cdx_file, self.warc_dir])

    def index_merge(self, filelist):
        wrongdir = 'Skipping {0}, must be in {1} archive directory'
        notfound = 'Skipping {0}, file not found'

        filtered_warcs = []

        # Check that warcs are actually in warcs dir
        abs_warc_dir = os.path.abspath(self.warc_dir)

        for f in filelist:
            abs_filepath = os.path.abspath(f)
            prefix = os.path.commonprefix([abs_warc_dir, abs_filepath])

            if prefix != abs_warc_dir:
                raise IOError(wrongdir.format(abs_filepath, abs_warc_dir))
            elif not os.path.isfile(abs_filepath):
                raise IOError(notfound.format(f))
            else:
                filtered_warcs.append(abs_filepath.split(prefix)[1])

        self._index_merge_warcs(filtered_warcs)

    def _index_merge_warcs(self, new_warcs):
        if not new_warcs:
            return

        cdx_file = os.path.join(self.cdx_dir, 'index.cdx')

        # no existing file, just reindex all
        if not os.path.isfile(cdx_file):
            return self.reindex()

        temp_file = cdx_file + '.tmp.' + timestamp20_now()
        args = ['-p', '-s', '-r', temp_file]
        args.extend(new_warcs)
        cdxindexer_main(args)

        merged_file = temp_file + '.merged'

        last_line = None

        with open(cdx_file) as orig_index:
            with open(temp_file) as new_index:
                with open(merged_file, 'w+b') as merged:
                    for line in heapq.merge(orig_index, new_index):
                        if last_line != line:
                            merged.write(line)
                            last_line = line

        os.rename(merged_file, cdx_file)
        os.remove(temp_file)


def main(args=None):
    description = """
Create manage file based web archive collections
"""

    epilog = """
Some examples:

* Create new collection 'my_coll'
{0} create my_coll

* Add warc mywarc1.warc.gz to my_coll (The warc will be copied to the collecton directory)
{0} add my_coll mywarc1.warc.gz

""".format(os.path.basename(sys.argv[0]))

    logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                        level=logging.DEBUG)

    parser = ArgumentParser(description=description,
                            epilog=epilog,
                            formatter_class=RawTextHelpFormatter)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--init', action='store_true')
    group.add_argument('--addwarc', action='store_true')
    group.add_argument('--reindex', action='store_true')
    group.add_argument('--index-warcs', action='store_true')

    parser.add_argument('name')
    parser.add_argument('files', nargs='*')

    r = parser.parse_args(args=args)

    m = CollectionsManager(r.name)
    if r.init:
        m.add_collection()
    elif r.addwarc:
        m.add_warcs(r.files)
    elif r.index_warcs:
        m.index_merge(r.files)
    elif r.reindex:
        m.reindex()


if __name__ == "__main__":
    main()
