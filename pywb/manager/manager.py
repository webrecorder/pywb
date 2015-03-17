import os
import shutil
import sys
import logging

from pywb.utils.loaders import load_yaml_config
from pywb.utils.timeutils import timestamp20_now
from pywb.warc.cdxindexer import main as cdxindexer_main
from pywb.webapp.pywb_init import DEFAULT_CONFIG

from distutils.util import strtobool
from pkg_resources import resource_string

from argparse import ArgumentParser, RawTextHelpFormatter
import heapq
import yaml


#=============================================================================
# to allow testing by mocking get_input
def get_input(msg):  #pragma: no cover
    return raw_input(msg)


#=============================================================================
class CollectionsManager(object):
    """ This utility is designed to
simplify the creation and management of web archive collections

It may be used via cmdline to setup and maintain the
directory structure expected by pywb
    """
    def __init__(self, coll_name, root_dir='collections', must_exist=True):
        self.root_dir = root_dir
        self.default_config = load_yaml_config('pywb/default_config.yaml')
        self.coll_name = coll_name

        self.coll_dir = os.path.join(self.root_dir, coll_name)

        self.warc_dir = self._get_dir('archive_paths')
        self.cdx_dir = self._get_dir('index_paths')
        self.static_dir = self._get_dir('static_path')
        self.templates_dir = self._get_dir('templates_dir')
        if must_exist:
            self._assert_coll_exists()

    def list_colls(self):
        print('Collections:')
        for d in os.listdir(self.root_dir):
            if os.path.isdir(os.path.join(self.root_dir, d)):
                print('- ' + d)

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

    def _assert_coll_exists(self):
        if not os.path.isdir(self.coll_dir):
            raise IOError('Collection {0} does not exist'.
                          format(self.coll_name))

    def add_warcs(self, warcs):
        if not os.path.isdir(self.warc_dir):
            raise IOError('Directory {0} does not exist'.
                          format(self.warc_dir))

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

    def set_metadata(self, namevalue_pairs):
        metadata_yaml = os.path.join(self.coll_dir, 'metadata.yaml')
        metadata = None
        if os.path.isfile(metadata_yaml):
            with open(metadata_yaml) as fh:
                metadata = yaml.safe_load(fh)

        if not metadata:
            metadata = {}

        msg = 'Metadata params must be in the form "name=value"'
        for pair in namevalue_pairs:
            v = pair.split('=', 1)
            if len(v) != 2:
                raise ValueError(msg)

            print('Set {0}={1}'.format(v[0], v[1]))
            metadata[v[0]] = v[1]

        with open(metadata_yaml, 'w+b') as fh:
            fh.write(yaml.dump(metadata, default_flow_style=False))

    def _load_templates_map(self):
        defaults = load_yaml_config(DEFAULT_CONFIG)

        # Coll Templates
        templates = defaults['paths']['template_files']

        for name, _ in templates.iteritems():
            templates[name] = defaults[name]


        # Shared Templates
        shared_templates = defaults['paths']['shared_template_files']

        for name, _ in shared_templates.iteritems():
            shared_templates[name] = defaults[name]

        return templates, shared_templates

    def list_templates(self):
        templates, shared_templates = self._load_templates_map()

        print('Shared Templates')
        for n, v in shared_templates.iteritems():
            print('- {0}: (pywb/{1})'.format(n, v))

        print('')

        print('Collection Templates')
        for n, v in templates.iteritems():
            print('- {0}: (pywb/{1})'.format(n, v))

    def _confirm_overwrite(self, full_path, msg):
        if not os.path.isfile(full_path):
            return True

        res = get_input(msg)
        try:
            res = strtobool(res)
        except ValueError:
            res = False

        if not res:
            raise IOError('Skipping, {0} already exists'.format(full_path))

    def _get_template_path(self, template_name, verb):
        templates, shared_templates = self._load_templates_map()

        try:
            filename = templates[template_name]
            if not self.coll_name:
                msg = ('To {1} a "{0}" template, you must specify ' +
                       'a collection name: template <coll> --{1} {0}')
                raise IOError(msg.format(template_name, verb))

            full_path = os.path.join(self.templates_dir, os.path.basename(filename))

        except KeyError:
            try:
                filename = shared_templates[template_name]
                full_path = os.path.join(os.getcwd(), filename)

                # Create templates dir on demand
                dir_ = os.path.dirname(full_path)
                if not os.path.isdir(dir_):
                    os.makedirs(dir_)
            except KeyError:
                msg = 'template name must be one of {0} or {1}'
                msg = msg.format(templates.keys(), shared_templates.keys())
                raise KeyError(msg)

        return full_path, filename

    def add_template(self, template_name, force=False):
        full_path, filename = self._get_template_path(template_name, 'add')

        msg = ('Template file "{0}" ({1}) already exists. ' +
               'Overwrite with default template? (y/n) ')
        msg = msg.format(full_path, template_name)

        if not force:
            self._confirm_overwrite(full_path, msg)

        data = resource_string('pywb', filename)
        with open(full_path, 'w+b') as fh:
            fh.write(data)

        full_path = os.path.abspath(full_path)
        print('Copied default template "{0}" to "{1}"'.format(filename, full_path))

    def remove_template(self, template_name, force=False):
        full_path, filename = self._get_template_path(template_name, 'remove')

        if not os.path.isfile(full_path):
            msg = 'Template "{0}" does not exist.'
            raise IOError(msg.format(full_path))

        msg = 'Delete template file "{0}" ({1})? (y/n) '
        msg = msg.format(full_path, template_name)

        if not force:
            self._confirm_overwrite(full_path, msg)

        os.remove(full_path)
        print('Removed template file "{0}"'.format(full_path))

#=============================================================================
def main(args=None):
    description = """
Create manage file based web archive collections
"""
    #format(os.path.basename(sys.argv[0]))

    logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                        level=logging.DEBUG)

    parser = ArgumentParser(description=description,
                            #epilog=epilog,
                            formatter_class=RawTextHelpFormatter)

    subparsers = parser.add_subparsers(dest='type')

    # Init Coll
    def do_init(r):
        m = CollectionsManager(r.coll_name, must_exist=False)
        m.add_collection()

    init_help = 'Init new collection, create all collection directories'
    init = subparsers.add_parser('init', help=init_help)
    init.add_argument('coll_name')
    init.set_defaults(func=do_init)

    # List Colls
    def do_list(r):
        m = CollectionsManager('', must_exist=False)
        m.list_colls()

    list_help = 'List Collections'
    listcmd = subparsers.add_parser('list', help=list_help)
    listcmd.set_defaults(func=do_list)

    # Add Warcs
    def do_add(r):
        m = CollectionsManager(r.coll_name)
        m.add_warcs(r.files)

    addwarc_help = 'Copy ARCS/WARCS to collection directory and reindex'
    addwarc = subparsers.add_parser('add', help=addwarc_help)
    addwarc.add_argument('coll_name')
    addwarc.add_argument('files', nargs='+')
    addwarc.set_defaults(func=do_add)


    # Reindex All
    def do_reindex(r):
        m = CollectionsManager(r.coll_name)
        m.reindex()

    reindex_help = 'Re-Index entire collection'
    reindex = subparsers.add_parser('reindex', help=reindex_help)
    reindex.add_argument('coll_name')
    reindex.set_defaults(func=do_reindex)

    # Index warcs
    def do_index(r):
        m = CollectionsManager(r.coll_name)
        m.index_merge(r.files)

    indexwarcs_help = 'Index specified ARC/WARC files in the collection'
    indexwarcs = subparsers.add_parser('index', help=indexwarcs_help)
    indexwarcs.add_argument('coll_name')
    indexwarcs.add_argument('files', nargs='+')
    indexwarcs.set_defaults(func=do_index)

    # Set metadata
    def do_metadata(r):
        m = CollectionsManager(r.coll_name)
        m.set_metadata(r.set)

    metadata_help = 'Set Metadata'
    metadata = subparsers.add_parser('metadata', help=metadata_help)
    metadata.add_argument('coll_name')
    metadata.add_argument('--set', nargs='+')
    metadata.set_defaults(func=do_metadata)

    # Add default template
    def do_add_template(r):
        m = CollectionsManager(r.coll_name)
        if r.add:
            m.add_template(r.add, r.force)
        elif r.remove:
            m.remove_template(r.remove, r.force)
        elif r.list:
            m.list_templates()

    template_help = 'Add default html template for customization'
    template = subparsers.add_parser('template')
    template.add_argument('coll_name', nargs='?', default='')
    template.add_argument('-f', '--force', action='store_true')
    template.add_argument('--add')
    template.add_argument('--remove')
    template.add_argument('--list', action='store_true')
    template.set_defaults(func=do_add_template)

    r = parser.parse_args(args=args)
    r.func(r)


# special wrapper for cli to avoid printing stack trace
def main_wrap_exc():  #pragma: no cover
    try:
        main()
    except Exception as e:
        print('Error: ' + str(e))
        sys.exit(2)


if __name__ == "__main__":
    main_wrap_exc()
