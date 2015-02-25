import os
import shutil
import sys
import logging

from pywb.utils.loaders import load_yaml_config
from pywb.warc.cdxindexer import main as cdxindexer_main
from argparse import ArgumentParser, RawTextHelpFormatter


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
        try:
            os.mkdir(dirname)
        except:
            pass

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
            raise Exception('Directory ' + warcdir + ' does not exist')

        if not warcs:
            print('No WARCs specified')
            return

        for filename in warcs:
            shutil.copy2(filename, self.warc_dir)
            logging.info('Copied ' + filename + ' to ' + self.warc_dir)

        self.reindex()

    def reindex(self):
        cdx_file = os.path.join(self.cdx_dir, 'index.cdx')
        logging.info('Indexing ' + self.warc_dir + ' to ' + cdx_file)
        cdxindexer_main(['-p', '-s', '-r', cdx_file, self.warc_dir])

def main():
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

    parser.add_argument('name')
    parser.add_argument('files', nargs='*')

    r = parser.parse_args()

    m = CollectionsManager(r.name)
    if r.init:
        m.add_collection()
    elif r.addwarc:
        m.add_warcs(r.files)
    elif r.reindex:
        m.reindex()


if __name__ == "__main__":
    main()
