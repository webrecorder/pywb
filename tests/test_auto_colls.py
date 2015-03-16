import os
import tempfile
import shutil
import sys

import webtest

from io import BytesIO

from pywb.webapp.pywb_init import create_wb_router
from pywb.manager.manager import main

from pywb import get_test_dir
from pywb.framework.wsgi_wrappers import init_app

from pytest import raises


#=============================================================================
root_dir = None
orig_cwd = None

def setup_module():
    global root_dir
    root_dir = tempfile.mkdtemp()

    global orig_cwd
    orig_cwd = os.getcwd()
    os.chdir(root_dir)

    # use actually set dir
    root_dir = os.getcwd()

def teardown_module():
    global root_dir
    shutil.rmtree(root_dir)

    global orig_cwd
    os.chdir(orig_cwd)


#=============================================================================
class TestManagedColls(object):
    def setup(self):
        global root_dir
        self.root_dir = root_dir

    def _create_app(self):
        self.app = init_app(create_wb_router)
        self.testapp = webtest.TestApp(self.app)

    def _check_dirs(self, base, dirlist):
        for dir_ in dirlist:
            assert os.path.isdir(os.path.join(base, dir_))

    def test_create_first_coll(self):
        """ Test first collection creation, with all required dirs
        """
        main(['init', 'test'])

        colls = os.path.join(self.root_dir, 'collections')
        assert os.path.isdir(colls)

        test = os.path.join(colls, 'test')
        assert os.path.isdir(test)

        self._check_dirs(test, ['cdx', 'warcs', 'static', 'templates'])

    def test_add_warcs(self):
        """ Test adding warc to new coll, check replay
        """
        warc1 = os.path.join(get_test_dir(), 'warcs', 'example.warc.gz')

        main(['add', 'test', warc1])

        self._create_app()
        resp = self.testapp.get('/test/20140103030321/http://example.com?example=1')
        assert resp.status_int == 200

    def test_another_coll(self):
        """ Test adding warc to a new coll, check replay
        """
        warc1 = os.path.join(get_test_dir(), 'warcs', 'example.warc.gz')

        main(['init', 'foo'])

        main(['add', 'foo', warc1])

        self._create_app()
        resp = self.testapp.get('/foo/20140103030321/http://example.com?example=1')
        assert resp.status_int == 200

    def test_add_more_warcs(self):
        """ Test adding additional warcs, check replay of added content
        """
        warc1 = os.path.join(get_test_dir(), 'warcs', 'iana.warc.gz')
        warc2 = os.path.join(get_test_dir(), 'warcs', 'example-extra.warc')

        main(['add', 'test', warc1, warc2])

        # Spurrious file in collections
        with open(os.path.join(self.root_dir, 'collections', 'blah'), 'w+b') as fh:
            fh.write('foo\n')

        with raises(IOError):
            main(['add', 'test', 'non-existent-file.warc.gz'])

        # check new cdx
        self._create_app()
        resp = self.testapp.get('/test/20140126200624/http://www.iana.org/')
        assert resp.status_int == 200

    def test_add_custom_nested_warcs(self):
        """ Test recursive indexing of custom created WARC hierarchy,
        warcs/A/..., warcs/B/sub/...
        Ensure CDX is relative to root archive dir, test replay
        """

        main(['init', 'nested'])

        nested_root = os.path.join(self.root_dir, 'collections', 'nested', 'warcs')
        nested_a = os.path.join(nested_root, 'A')
        nested_b = os.path.join(nested_root, 'B', 'sub')

        os.makedirs(nested_a)
        os.makedirs(nested_b)

        warc1 = os.path.join(get_test_dir(), 'warcs', 'iana.warc.gz')
        warc2 = os.path.join(get_test_dir(), 'warcs', 'example.warc.gz')

        shutil.copy2(warc1, nested_a)
        shutil.copy2(warc2, nested_b)

        main(['index',
              'nested',
              os.path.join(nested_a, 'iana.warc.gz'),
              os.path.join(nested_b, 'example.warc.gz')
             ])

        nested_cdx = os.path.join(self.root_dir, 'collections', 'nested', 'cdx', 'index.cdx')
        with open(nested_cdx) as fh:
            nested_cdx_index = fh.read()

        assert '- 1043 333 B/sub/example.warc.gz' in nested_cdx_index
        assert '- 2258 334 A/iana.warc.gz' in nested_cdx_index

        self._create_app()
        resp = self.testapp.get('/nested/20140126200624/http://www.iana.org/')
        assert resp.status_int == 200

        resp = self.testapp.get('/nested/20140103030321/http://example.com?example=1')
        assert resp.status_int == 200

    def test_merge_vs_reindex_equality(self):
        """ Test full reindex vs merged update when adding warcs
        to ensure equality of indexes
        """
        # ensure merged index is same as full reindex
        coll_dir = os.path.join(self.root_dir, 'collections', 'test', 'cdx')
        orig = os.path.join(coll_dir, 'index.cdx')
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
        a_static = os.path.join(self.root_dir, 'collections', 'test', 'static', 'abc.js')

        with open(a_static, 'w+b') as fh:
            fh.write('/* Some JS File */')

        self._create_app()
        resp = self.testapp.get('/static/test/abc.js')
        assert resp.status_int == 200
        assert resp.content_type == 'application/javascript'
        assert '/* Some JS File */' in resp.body

    def test_add_title_metadata_index_page(self):
        """ Test adding title metadata to a collection, test
        retrieval on default index page
        """
        main(['metadata', 'foo', '--set', 'title=Collection Title'])

        self._create_app()
        resp = self.testapp.get('/')
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert '(Collection Title)' in resp.body

    def test_other_metadata_search_page(self):
        main(['metadata', 'foo', '--set',
              'desc=Some Description Text',
              'other=custom value'])

        with raises(ValueError):
            main(['metadata', 'foo', '--set', 'name_only'])

        self._create_app()
        resp = self.testapp.get('/foo/')
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'

        assert 'Collection Title' in resp.body

        assert 'desc' in resp.body
        assert 'Some Description Text' in resp.body

        assert 'other' in resp.body
        assert 'custom value' in resp.body

    def test_custom_template_search(self):
        """ Test manually added custom search template search.html
        """
        a_static = os.path.join(self.root_dir, 'collections', 'test', 'templates', 'search.html')

        with open(a_static, 'w+b') as fh:
            fh.write('pywb custom search page')

        self._create_app()
        resp = self.testapp.get('/test/')
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert 'pywb custom search page' in resp.body

    def test_custom_config(self):
        """ Test custom created config.yaml which overrides auto settings
        Template relative to root dir, not collection-specific so far
        """
        config_path = os.path.join(self.root_dir, 'collections', 'test', 'config.yaml')
        with open(config_path, 'w+b') as fh:
            fh.write('search_html: ./custom_search.html\n')

        custom_search = os.path.join(self.root_dir, 'custom_search.html')
        with open(custom_search, 'w+b') as fh:
            fh.write('config.yaml overriden search page')

        self._create_app()
        resp = self.testapp.get('/test/')
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert 'config.yaml overriden search page' in resp.body

    def test_no_templates(self):
        """ Test removing templates dir, using default template again
        """
        shutil.rmtree(os.path.join(self.root_dir, 'collections', 'test', 'templates'))

        self._create_app()

        resp = self.testapp.get('/test/')
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert 'pywb custom search page' not in resp.body

    def test_list_colls(self):
        """ Test collection listing, printed to stdout
        """
        orig_stdout = sys.stdout
        buff = BytesIO()
        sys.stdout = buff
        main(['list'])
        sys.stdout = orig_stdout

        output = buff.getvalue().splitlines()
        assert len(output) == 4
        assert 'Collections' in output[0]
        assert 'foo' in output[1]
        assert 'nested' in output[2]
        assert 'test' in output[3]

    def test_err_no_such_coll(self):
        """ Test error adding warc to non-existant collection
        """
        warc1 = os.path.join(get_test_dir(), 'warcs', 'example.warc.gz')

        with raises(IOError):
            main(['add', 'bar', warc1])

    def test_err_wrong_warcs(self):
        warc1 = os.path.join(get_test_dir(), 'warcs', 'example.warc.gz')
        invalid_warc = os.path.join(self.root_dir, 'collections', 'test', 'warcs', 'invalid.warc.gz')

        # Empty warc list, argparse calls exit
        with raises(SystemExit):
            main(['index', 'test'])

        # Wrong paths not in collection
        with raises(IOError):
            main(['index', 'test', warc1])

        # Non-existent
        with raises(IOError):
            main(['index', 'test', invalid_warc])

    def test_err_missing_dirs(self):
        """ Test various errors with missing warcs dir,
        missing cdx dir, non dir cdx file, and missing collections root
        """
        colls = os.path.join(self.root_dir, 'collections')

        # No WARCS
        warcs_path = os.path.join(colls, 'foo', 'warcs')
        shutil.rmtree(warcs_path)

        with raises(IOError):
            main(['add', 'foo', 'somewarc'])

        # No CDX
        cdx_path = os.path.join(colls, 'foo', 'cdx')
        shutil.rmtree(cdx_path)

        with raises(Exception):
            self._create_app()

        # CDX a file not a dir
        with open(cdx_path, 'w+b') as fh:
            fh.write('foo\n')

        with raises(Exception):
            self._create_app()

        shutil.rmtree(colls)

        # No Collections
        self._create_app()
        resp = self.testapp.get('/test/', status=404)
        assert resp.status_int == 404

