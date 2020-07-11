from .base_config_test import BaseConfigTest, CollsDirMixin, fmod

import os
import tempfile
import shutil
import sys

import webtest

import time
import gevent

from six import StringIO

import webtest
from pytest import raises
from mock import patch

from pywb import get_test_dir
from pywb.warcserver.test.testutils import BaseTestClass

from pywb.manager.autoindex import AutoIndexer
from pywb.manager.manager import main

from pywb.indexer.cdxindexer import main as cdxindexer_main
from pywb.warcserver.index.cdxobject import CDXObject

from pywb.apps.frontendapp import FrontEndApp


#=============================================================================
ARCHIVE_DIR = 'archive'
INDEX_DIR = 'indexes'
COLLECTIONS = '_test_colls'

INDEX_FILE = 'index.cdxj'
AUTOINDEX_FILE = 'autoindex.cdxj'


#=============================================================================
class TestManagedColls(CollsDirMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestManagedColls, cls).setup_class('config_test.yaml')

    def _check_dirs(self, base, dirlist):
        for dir_ in dirlist:
            assert os.path.isdir(os.path.join(base, dir_))

    def _get_sample_warc(self, name):
        return os.path.join(get_test_dir(), 'warcs', name)

    @patch('pywb.apps.cli.BaseCli.run_gevent', lambda *args, **kwargs: None)
    def test_run_cli(self):
        """ test new wayback cli interface
        test autoindex error before collections inited
        """
        from pywb.apps.cli import wayback

        wayback(['-p', '0'])

        # Nothing to auto-index.. yet
        with raises(SystemExit):
            wayback(['-a', '-p', '0'])

        colls = os.path.join(self.root_dir, COLLECTIONS)
        os.mkdir(colls)

        wayback(['-a', '-p', '0', '--auto-interval', '0'])

    def test_create_first_coll(self):
        """ Test first collection creation, with all required dirs
        """
        main(['init', 'test'])

        colls = os.path.join(self.root_dir, COLLECTIONS)
        assert os.path.isdir(colls)

        test = os.path.join(colls, 'test')
        assert os.path.isdir(test)

        self._check_dirs(test, [INDEX_DIR, ARCHIVE_DIR, 'static', 'templates'])

    def test_add_warcs(self):
        """ Test adding warc to new coll, check replay
        """
        warc1 = self._get_sample_warc('example.warc.gz')

        main(['add', 'test', warc1])

    def test_add_warcs_replay(self, fmod):
        resp = self.get('/test/20140103030321{0}/http://example.com/?example=1', fmod)
        assert resp.status_int == 200

    def test_another_coll(self):
        """ Test adding warc to a new coll, check replay
        """
        warc1 = self._get_sample_warc('example.warc.gz')

        main(['init', 'foo'])

        main(['add', 'foo', warc1])

    def test_another_coll_replay(self, fmod):
        resp = self.get('/foo/20140103030321{0}/http://example.com/?example=1', fmod)
        assert resp.status_int == 200

    def test_add_more_warcs(self):
        """ Test adding additional warcs, check replay of added content
        """
        warc1 = self._get_sample_warc('iana.warc.gz')
        warc2 = self._get_sample_warc('example-extra.warc')

        main(['add', 'test', warc1, warc2])

        # Spurrious file in collections
        with open(os.path.join(self.root_dir, COLLECTIONS, 'blah'), 'w+b') as fh:
            fh.write(b'foo\n')

        with raises(IOError):
            main(['add', 'test', 'non-existent-file.warc.gz'])

    def test_add_more_warcs_replay(self, fmod):
        # check new cdx
        resp = self.get('/test/20140126200624{0}/http://www.iana.org/', fmod)
        assert resp.status_int == 200

    def test_add_custom_nested_warcs(self):
        """ Test recursive indexing of custom created WARC hierarchy,
        warcs/A/..., warcs/B/sub/...
        Ensure CDX is relative to root archive dir, test replay
        """

        main(['init', 'nested'])

        nested_root = os.path.join(self.root_dir, COLLECTIONS, 'nested', ARCHIVE_DIR)
        nested_a = os.path.join(nested_root, 'A')
        nested_b = os.path.join(nested_root, 'B', 'sub')

        os.makedirs(nested_a)
        os.makedirs(nested_b)

        warc1 = self._get_sample_warc('iana.warc.gz')
        warc2 = self._get_sample_warc('example.warc.gz')

        shutil.copy2(warc1, nested_a)
        shutil.copy2(warc2, nested_b)

        main(['index',
              'nested',
              os.path.join(nested_a, 'iana.warc.gz'),
              os.path.join(nested_b, 'example.warc.gz')
             ])

        nested_cdx = os.path.join(self.root_dir, COLLECTIONS, 'nested', INDEX_DIR, INDEX_FILE)
        with open(nested_cdx) as fh:
            nested_cdx_index = fh.read()

        assert '1043' in nested_cdx_index
        assert '333' in nested_cdx_index
        assert 'B/sub/example.warc.gz' in nested_cdx_index

        assert '2258' in nested_cdx_index
        assert '334' in nested_cdx_index
        assert 'A/iana.warc.gz' in nested_cdx_index

    def test_nested_replay(self, fmod):
        resp = self.get('/nested/20140126200624{0}/http://www.iana.org/', fmod)
        assert resp.status_int == 200

        resp = self.get('/nested/20140103030321{0}/http://example.com/?example=1', fmod)
        assert resp.status_int == 200

    def test_merge_vs_reindex_equality(self):
        """ Test full reindex vs merged update when adding warcs
        to ensure equality of indexes
        """
        # ensure merged index is same as full reindex
        coll_dir = os.path.join(self.root_dir, COLLECTIONS, 'test', INDEX_DIR)
        orig = os.path.join(coll_dir, INDEX_FILE)
        bak = os.path.join(coll_dir, 'index.bak')

        shutil.copy(orig, bak)

        main(['reindex', 'test'])

        with open(orig) as orig_fh:
            merged_cdx = orig_fh.read()

        with open(bak) as bak_fh:
            reindex_cdx = bak_fh.read()

        assert len(reindex_cdx.splitlines()) == len(merged_cdx.splitlines())
        assert merged_cdx == reindex_cdx

    def test_add_static(self):
        """ Test adding static file to collection, check access
        """
        a_static = os.path.join(self.root_dir, COLLECTIONS, 'test', 'static', 'abc.js')

        with open(a_static, 'w+b') as fh:
            fh.write(b'/* Some JS File */')

        resp = self.testapp.get('/static/_/test/abc.js')
        assert resp.status_int == 200
        assert resp.content_type == 'application/javascript'
        resp.charset = 'utf-8'
        assert '/* Some JS File */' in resp.text

    def test_add_shared_static(self):
        """ Test adding shared static file to root static/ dir, check access
        """
        a_static = os.path.join(self.root_dir, 'static', 'foo.css')

        with open(a_static, 'w+b') as fh:
            fh.write(b'/* Some CSS File */')

        resp = self.testapp.get('/static/foo.css')
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'
        resp.charset = 'utf-8'
        assert '/* Some CSS File */' in resp.text

    def test_add_title_metadata_index_page(self):
        """ Test adding title metadata to a collection, test
        retrieval on default index page
        """
        main(['metadata', 'foo', '--set', 'title=Collection Title'])

        resp = self.testapp.get('/')
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        resp.charset = 'utf-8'
        assert '(Collection Title)' in resp.text

        # test cache
        resp = self.testapp.get('/')
        resp.charset = 'utf-8'
        assert '(Collection Title)' in resp.text

    def test_other_metadata_search_page(self):
        main(['metadata', 'foo', '--set',
              'desc=Some Description Text',
              'other=custom value'])

        with raises(ValueError):
            main(['metadata', 'foo', '--set', 'name_only'])

        resp = self.testapp.get('/foo/')
        resp.charset = 'utf-8'
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'

        assert 'Collection Title' in resp.text

        assert 'desc' in resp.text
        assert 'Some Description Text' in resp.text

        assert 'other' in resp.text
        assert 'custom value' in resp.text

    def test_custom_template_search(self):
        """ Test manually added custom search template search.html
        """
        custom_search = os.path.join(self.root_dir, COLLECTIONS, 'test',
                                      'templates', 'search.html')

        with open(custom_search, 'w+b') as fh:
            fh.write(b'pywb custom search page')

        resp = self.testapp.get('/test/')
        resp.charset = 'utf-8'
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert 'pywb custom search page' in resp.text

    def test_add_custom_banner(self):
        """ Test adding custom banner.html per-collection template
        """

        banner_file = os.path.join(self.root_dir, COLLECTIONS, 'test',
                                   'templates', 'banner.html')

        with open(banner_file, 'w+b') as fh:
            fh.write(b'<div>Custom Banner Here!</div>')
            fh.write(b'\n{{ metadata | tojson }}')

    def test_add_custom_banner_replay(self, fmod):
        resp = self.get('/test/20140103030321/http://example.com/?example=1', fmod)
        assert '<div>Custom Banner Here!</div>' in resp.text

    def test_more_custom_templates(self):
        """
        Test custom templates and metadata
        Template is relative to collection-specific dir
        Add custom metadata and test its presence in custom search page
        """
        custom_search = os.path.join(self.root_dir, COLLECTIONS, 'test',
                                      'templates', 'search.html')

        # add metadata
        main(['metadata', 'test', '--set', 'some=value'])

        with open(custom_search, 'w+b') as fh:
            fh.write(b'overriden search page: ')
            fh.write(b'{{ metadata | tojson }}\n')

        # force clear of jinja env cache to reload
        self.app.rewriterapp.jinja_env.jinja_env.cache = {}

        resp = self.testapp.get('/test/')
        resp.charset = 'utf-8'
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert 'overriden search page: ' in resp.text
        print(resp.text)
        assert '"some":"value"' in resp.text, resp.text

    def test_replay_banner_metadata(self, fmod):
        """ Test adding metadata in replay banner (both framed and non-frame)
        """
        resp = self.get('/test/20140103030321{0}/http://example.com/?example=1', fmod)
        assert '<div>Custom Banner Here!</div>' in resp.text
        assert '"some":"value"' in resp.text

    def test_more_custom_templates_replay(self, fmod):
        resp = self.get('/test/20140103030321{0}/http://example.com/?example=1', fmod)
        assert resp.status_int == 200

    def test_add_default_coll_templates(self):
        """ Test add default templates: collection,
        and overwrite collection template
        """
        # list
        main(['template', 'foo', '--list'])

        # Add collection template
        main(['template', 'foo', '--add', 'query_html'])
        assert os.path.isfile(os.path.join(self.root_dir, COLLECTIONS, 'foo', 'templates', 'query.html'))

        # overwrite -- force
        main(['template', 'foo', '--add', 'query_html', '-f'])

    def test_add_modify_home_template(self):
        # Add shared template
        main(['template', '--add', 'home_html'])

        filename = os.path.join(self.root_dir, 'templates', 'index.html')
        assert os.path.isfile(filename)

        with open(filename, 'r+b') as fh:
            buf = fh.read()
            buf = buf.replace(b'Pywb Wayback Machine', b'Custom Test Homepage')
            fh.seek(0)
            fh.write(buf)

        resp = self.testapp.get('/')
        resp.charset = 'utf-8'
        assert resp.content_type == 'text/html'
        assert 'Custom Test Homepage' in resp.text, resp.text

    @patch('pywb.manager.manager.get_input', lambda x: 'y')
    def test_add_template_input_yes(self):
        """ Test answer 'yes' to overwrite
        """
        main(['template', 'foo', '--add', 'query_html'])


    @patch('pywb.manager.manager.get_input', lambda x: 'n')
    def test_add_template_input_no(self):
        """ Test answer 'no' to overwrite
        """
        with raises(IOError):
            main(['template', 'foo', '--add', 'query_html'])

    @patch('pywb.manager.manager.get_input', lambda x: 'other')
    def test_add_template_input_other(self):
        """ Test answer 'other' to overwrite
        """
        with raises(IOError):
            main(['template', 'foo', '--add', 'query_html'])

    @patch('pywb.manager.manager.get_input', lambda x: 'no')
    def test_remove_not_confirm(self):
        """ Test answer 'no' to remove
        """
        # don't remove -- not confirmed
        with raises(IOError):
            main(['template', 'foo', '--remove', 'query_html'])

    @patch('pywb.manager.manager.get_input', lambda x: 'yes')
    def test_remove_confirm(self):
        # remove -- confirm
        main(['template', 'foo', '--remove', 'query_html'])

    def test_no_templates(self):
        """ Test removing templates dir, using default template again
        """
        shutil.rmtree(os.path.join(self.root_dir, COLLECTIONS, 'foo', 'templates'))

        resp = self.testapp.get('/foo/')
        resp.charset = 'utf-8'
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert 'pywb custom search page' not in resp.text

    def test_list_colls(self):
        """ Test collection listing, printed to stdout
        """
        orig_stdout = sys.stdout
        buff = StringIO()
        sys.stdout = buff

        try:
            main(['list'])
        finally:
            sys.stdout = orig_stdout

        output = sorted(buff.getvalue().splitlines())
        assert len(output) == 4
        assert 'Collections:' in output
        assert '- foo' in output
        assert '- nested' in output
        assert '- test' in output

    def test_convert_cdx(self):
        """ Create non-surt cdx, then convert to cdxj
        """
        migrate_dir = os.path.join(self.root_dir, '_migrate')

        os.mkdir(migrate_dir)

        cdxindexer_main(['-u', '-o', migrate_dir, self._get_sample_warc('')])

        # try one file with -9
        cdxindexer_main(['-u', '-9', '-o', migrate_dir, self._get_sample_warc('example.warc.gz')])

        cdxs = os.listdir(migrate_dir)
        assert all(x.endswith('.cdx') for x in cdxs)

        @patch('pywb.manager.manager.get_input', lambda x: 'blah')
        def do_migrate_no():
            main(['cdx-convert', migrate_dir])

        do_migrate_no()
        assert os.listdir(migrate_dir) == cdxs

        @patch('pywb.manager.manager.get_input', lambda x: 'y')
        def do_migrate_yes():
            main(['cdx-convert', migrate_dir])

        do_migrate_yes()
        cdxjs = os.listdir(migrate_dir)

        assert len(cdxs) == len(cdxjs)
        assert all(x.endswith('.cdxj') for x in cdxjs)

        with open(os.path.join(migrate_dir, 'iana.cdxj'), 'rb') as fh:
            cdx = CDXObject(fh.readline())
            assert cdx['urlkey'] == 'org,iana)/'
            assert cdx['timestamp'] == '20140126200624'
            assert cdx['url'] == 'http://www.iana.org/'
            #assert fh.readline().startswith('org,iana)/ 20140126200624 {"url": "http://www.iana.org/",')

        # Nothing else to migrate
        main(['cdx-convert', migrate_dir])

    def test_auto_index(self):
        main(['init', 'auto'])
        auto_dir = os.path.join(self.root_dir, COLLECTIONS, 'auto')
        archive_dir = os.path.join(auto_dir, ARCHIVE_DIR)

        archive_sub_dir = os.path.join(archive_dir, 'sub')
        os.makedirs(archive_sub_dir)

        def do_copy():
            try:
                time.sleep(1.0)
                shutil.copy(self._get_sample_warc('example.warc.gz'), archive_dir)
                shutil.copy(self._get_sample_warc('example-extra.warc'), archive_sub_dir)
                time.sleep(1.0)
            finally:
                indexer.interval = 0

        indexer = AutoIndexer(interval=0.25)
        indexer.start()

        ge = gevent.spawn(do_copy)
        ge.join()

        index_file = os.path.join(auto_dir, INDEX_DIR, AUTOINDEX_FILE)
        assert os.path.isfile(index_file)

        with open(index_file, 'r') as fh:
            index = fh.read()

        assert '"example.warc.gz' in index, index
        assert '"sub/example-extra.warc' in index, index

        mtime = os.path.getmtime(index_file)

        # Update
        indexer.interval = 0.25
        indexer.start()

        os.remove(index_file)

        #thread = threading.Thread(target=do_copy)
        #thread.daemon = True
        #thread.start()
        ge = gevent.spawn(do_copy)

        #wayback(['-p', '0', '-a', '--auto-interval', '0.25'])

        #thread.join()
        ge.join()

	# assert file was update
        assert os.path.getmtime(index_file) > mtime

    def test_err_template_remove(self):
        """ Test various error conditions for templates:
        invalid template name, no collection for collection template
        no template file found
        """
        # no such template
        with raises(KeyError):
            main(['template', 'foo', '--remove', 'blah_html'])

        # collection needed
        with raises(IOError):
            main(['template', '--remove', 'query_html'])

        # already removed
        with raises(IOError):
            main(['template', 'foo', '--remove', 'query_html'])

    def test_err_no_such_coll(self):
        """ Test error adding warc to non-existant collection
        """
        warc1 = self._get_sample_warc('example.warc.gz')

        with raises(IOError):
            main(['add', 'bar', warc1])

    def test_err_wrong_warcs(self):
        warc1 = self._get_sample_warc('example.warc.gz')
        invalid_warc = os.path.join(self.root_dir, COLLECTIONS, 'test', ARCHIVE_DIR, 'invalid.warc.gz')

        # Empty warc list, argparse calls exit
        with raises(SystemExit):
            main(['index', 'test'])

        # Wrong paths not in collection
        with raises(IOError):
            main(['index', 'test', warc1])

        # Non-existent
        with raises(IOError):
            main(['index', 'test', invalid_warc])

    def test_err_invalid_name(self):
        """ Invalid collection name
        """
        with raises(ValueError):
            main(['init', '../abc%'])

        with raises(ValueError):
            main(['init', '45^23'])

    def test_err_missing_dirs(self):
        """ Test various errors with missing warcs dir,
        missing cdx dir, non dir cdx file, and missing collections root
        """
        colls = os.path.join(self.root_dir, COLLECTIONS)

        # No Statics -- ignorable
        shutil.rmtree(os.path.join(colls, 'foo', 'static'))

        # No WARCS
        warcs_path = os.path.join(colls, 'foo', ARCHIVE_DIR)
        shutil.rmtree(warcs_path)

        with raises(IOError):
            main(['add', 'foo', 'somewarc'])

        # No CDX
        cdx_path = os.path.join(colls, 'foo', INDEX_DIR)
        shutil.rmtree(cdx_path)

        # CDX a file not a dir
        with open(cdx_path, 'w+b') as fh:
            fh.write(b'foo\n')

        shutil.rmtree(colls)

        # No Collections to list
        with raises(IOError):
            main(['list'])

        # No Collections
        resp = self.testapp.get('/test/', status=404)
        assert resp.status_int == 404

