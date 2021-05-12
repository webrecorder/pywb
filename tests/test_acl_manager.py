import os

from .base_config_test import BaseConfigTest, CollsDirMixin, fmod
from pywb.manager.manager import main as wb_manager
from pytest import raises


# ============================================================================
class TestACLManager(CollsDirMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestACLManager, cls).setup_class('config_test_access.yaml')

        cls.acl_filename = os.path.join(cls.root_dir, 'acl', 'test.aclj')

    @classmethod
    def teardown_class(cls):
        super(TestACLManager, cls).teardown_class()
        try:
            os.remove(cls.acl_filename)
        except:
            pass

    def test_acl_add_err_wrong_access(self):
        with raises(SystemExit):
            wb_manager(['acl', 'add', self.acl_filename, 'http://example.com/', 'access'])

    def test_acl_add(self):
        wb_manager(['acl', 'add', self.acl_filename, 'http://example.com/', 'allow'])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example)/ - {"access": "allow", "url": "http://example.com/"}
"""

    def test_acl_add_surt(self):
        wb_manager(['acl', 'add', self.acl_filename, 'com,example,', 'exclude'])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example, - {"access": "exclude", "url": "com,example,"}
com,example)/ - {"access": "allow", "url": "http://example.com/"}
"""

    def test_acl_add_with_user(self):
        wb_manager(['acl', 'add', self.acl_filename, 'http://example.com/', 'block', '-u', 'public'])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example, - {"access": "exclude", "url": "com,example,"}
com,example)/ - {"access": "block", "url": "http://example.com/", "user": "public"}
com,example)/ - {"access": "allow", "url": "http://example.com/"}
"""

    def test_acl_list(self, capsys):
        wb_manager(['acl', 'list', self.acl_filename])

        out, err = capsys.readouterr()

        assert out == """\
Rules for %s from %s:

com,example, - {"access": "exclude", "url": "com,example,"}
com,example)/ - {"access": "block", "url": "http://example.com/", "user": "public"}
com,example)/ - {"access": "allow", "url": "http://example.com/"}

""" % (self.acl_filename, self.acl_filename)


    def test_acl_list_err_no_such_file(self):
        with raises(SystemExit):
            wb_manager(['acl', 'list', self.acl_filename + '2'])


    def test_acl_match(self, capsys):
        wb_manager(['acl', 'match', self.acl_filename, 'http://abc.example.com/foo'])

        out, err = capsys.readouterr()

        assert out == """\
Matched rule:

    com,example, - {"access": "exclude", "url": "com,example,"}

"""

    def test_acl_match_user(self, capsys):
        wb_manager(['acl', 'match', self.acl_filename, 'http://example.com/foo', '-u', 'public'])

        out, err = capsys.readouterr()

        assert out == """\
Matched rule:

    com,example)/ - {"access": "block", "url": "http://example.com/", "user": "public"}

"""

    def test_acl_match_unknown_user(self, capsys):
        wb_manager(['acl', 'match', self.acl_filename, 'http://example.com/foo', '-u', 'data'])

        out, err = capsys.readouterr()

        assert out == """\
Matched rule:

    com,example)/ - {"access": "allow", "url": "http://example.com/"}

"""

    def test_acl_match_default_user(self, capsys):
        wb_manager(['acl', 'match', self.acl_filename, 'http://example.com/foo'])

        out, err = capsys.readouterr()

        assert out == """\
Matched rule:

    com,example)/ - {"access": "allow", "url": "http://example.com/"}

"""

    def test_remove_acl(self):
        wb_manager(['acl', 'remove', self.acl_filename, 'com,example,'])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example)/ - {"access": "block", "url": "http://example.com/", "user": "public"}
com,example)/ - {"access": "allow", "url": "http://example.com/"}
"""

    def test_remove_acl_user(self):
        wb_manager(['acl', 'remove', self.acl_filename, 'com,example)/', '-u', 'public'])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example)/ - {"access": "allow", "url": "http://example.com/"}
"""



    def test_acl_add_exact(self):
        wb_manager(['acl', 'add', '--exact-match', self.acl_filename, 'example.com', 'block'])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example)/### - {"access": "block", "url": "example.com"}
com,example)/ - {"access": "allow", "url": "http://example.com/"}
"""

    def test_remove_acl_exact(self):
        wb_manager(['acl', 'remove', '-e', self.acl_filename, 'https://example.com/'])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example)/ - {"access": "allow", "url": "http://example.com/"}
"""

    def test_validate_and_sort_acl(self):
        with open(self.acl_filename, 'at') as fh:
            fh.write('com,example)/subpath - {"access": "block", "url": "http://example.com/subpath"}\n')

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example)/ - {"access": "allow", "url": "http://example.com/"}
com,example)/subpath - {"access": "block", "url": "http://example.com/subpath"}
"""

        wb_manager(['acl', 'validate', self.acl_filename])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
com,example)/subpath - {"access": "block", "url": "http://example.com/subpath"}
com,example)/ - {"access": "allow", "url": "http://example.com/"}
"""

    def test_importtxt_acl(self, capsys):
        name = os.path.join(self.root_dir, 'excludes.txt')
        with open(name, 'wt') as exc:
            exc.write('http://iana.org/\n')
            exc.write('http://example.com/subpath/another\n')
            exc.write('http://example.co/foo/\n')
            exc.write('http://example.com/\n')

        wb_manager(['acl', 'importtxt', self.acl_filename, name, 'exclude'])

        with open(self.acl_filename, 'rt') as fh:
            assert fh.read() == """\
org,iana)/ - {"access": "exclude", "url": "http://iana.org/"}
com,example)/subpath/another - {"access": "exclude", "url": "http://example.com/subpath/another"}
com,example)/subpath - {"access": "block", "url": "http://example.com/subpath"}
com,example)/ - {"access": "exclude", "url": "http://example.com/"}
co,example)/foo - {"access": "exclude", "url": "http://example.co/foo/"}
"""

        out, err = capsys.readouterr()

        assert 'Added or replaced 4 rules from {0}'.format(name) in out, out

        os.remove(name)

    def test_import_errors(self):
        # missing access mode
        with raises(SystemExit):
            wb_manager(['acl', 'importtxt', self.acl_filename, 'foo'])

        # no such file
        with raises(SystemExit):
            wb_manager(['acl', 'importtxt', self.acl_filename, 'foo', 'exclude'])


