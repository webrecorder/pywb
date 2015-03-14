import os
import tempfile
import shutil

import webtest

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
        main(['--init', 'test'])

        colls = os.path.join(self.root_dir, 'collections')
        assert os.path.isdir(colls)

        test = os.path.join(colls, 'test')
        assert os.path.isdir(test)

        self._check_dirs(test, ['cdx', 'warcs', 'static', 'templates'])

    def test_add_warcs(self):
        warc1 = os.path.join(get_test_dir(), 'warcs', 'example.warc.gz')

        main(['--addwarc', 'test', warc1])

        self._create_app()
        resp = self.testapp.get('/test/20140103030321/http://example.com?example=1')
        assert resp.status_int == 200

    def test_add_more_warcs(self):
        warc1 = os.path.join(get_test_dir(), 'warcs', 'iana.warc.gz')
        warc2 = os.path.join(get_test_dir(), 'warcs', 'example-extra.warc')

        main(['--addwarc', 'test', warc1, warc2])

        # Spurrious file in collections
        with open(os.path.join(self.root_dir, 'collections', 'blah'), 'w+b') as fh:
            fh.write('foo\n')

        with raises(IOError):
            main(['--addwarc', 'test', 'non-existent-file.warc.gz'])

        main(['--addwarc', 'test'])

        main(['--reindex', 'test'])

        self._create_app()
        resp = self.testapp.get('/test/20140103030321/http://example.com?example=1')
        assert resp.status_int == 200

    def test_add_static(self):
        a_static = os.path.join(self.root_dir, 'collections', 'test', 'static', 'abc.js')

        with open(a_static, 'w+b') as fh:
            fh.write('/* Some JS File */')

        self._create_app()
        resp = self.testapp.get('/static/test/abc.js')
        assert resp.status_int == 200
        assert resp.content_type == 'application/javascript'
        assert '/* Some JS File */' in resp.body

    def test_custom_search(self):
        a_static = os.path.join(self.root_dir, 'collections', 'test', 'templates', 'search.html')

        with open(a_static, 'w+b') as fh:
            fh.write('pywb custom search page')

        self._create_app()
        resp = self.testapp.get('/test/')
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert 'pywb custom search page' in resp.body

    def test_no_templates(self):
        shutil.rmtree(os.path.join(self.root_dir, 'collections', 'test', 'templates'))

        self._create_app()

        resp = self.testapp.get('/test/')
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert 'pywb custom search page' not in resp.body

    def test_err_missing_dirs(self):
        colls = os.path.join(self.root_dir, 'collections')

        # No CDX
        cdx_path = os.path.join(colls, 'test', 'cdx')
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

