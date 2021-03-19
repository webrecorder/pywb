from mock import patch
import shutil
import os

from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.access_checker import FileAccessIndexSource, AccessChecker, DirectoryAccessSource

from pywb.warcserver.test.testutils import to_path, TempDirTests, BaseTestClass
from pywb import get_test_dir

TEST_EXCL_PATH = to_path(get_test_dir() + '/access/')


# ============================================================================
class TestAccess(TempDirTests, BaseTestClass):
    def test_allows_only_default_block(self):
        agg = SimpleAggregator({'source': FileAccessIndexSource(TEST_EXCL_PATH + 'allows.aclj')})
        access = AccessChecker(agg, default_access='block')

        edx = access.find_access_rule('http://example.net')
        assert edx['urlkey'] == 'net,'

        edx = access.find_access_rule('http://foo.example.net/abc')
        assert edx['urlkey'] == 'net,'

        edx = access.find_access_rule('https://example.net/test/')
        assert edx['urlkey'] == 'net,example)/test'

        edx = access.find_access_rule('https://example.org/')
        assert edx['urlkey'] == ''
        assert edx['access'] == 'block'

        edx = access.find_access_rule('https://abc.domain.net/path')
        assert edx['urlkey'] == 'net,domain,'

        edx = access.find_access_rule('https://domain.neta/path')
        assert edx['urlkey'] == ''
        assert edx['access'] == 'block'

    def test_blocks_only(self):
        agg = SimpleAggregator({'source': FileAccessIndexSource(TEST_EXCL_PATH + 'blocks.aclj')})
        access = AccessChecker(agg)

        edx = access.find_access_rule('https://example.com/foo')
        assert edx['urlkey'] == 'com,example)/foo'
        assert edx['access'] == 'exclude'

        edx = access.find_access_rule('https://example.com/food')
        assert edx['urlkey'] == 'com,example)/foo'
        assert edx['access'] == 'exclude'

        edx = access.find_access_rule('https://example.com/foo/path')
        assert edx['urlkey'] == 'com,example)/foo'
        assert edx['access'] == 'exclude'

        edx = access.find_access_rule('https://example.net/abc/path')
        assert edx['urlkey'] == 'net,example)/abc/path'
        assert edx['access'] == 'block'

        edx = access.find_access_rule('https://example.net/abc/path/other')
        assert edx['urlkey'] == 'net,example)/abc/path'
        assert edx['access'] == 'block'

        edx = access.find_access_rule('https://example.net/fo')
        assert edx['urlkey'] == ''
        assert edx['access'] == 'allow'

    def test_single_file_combined(self):
        agg = SimpleAggregator({'source': FileAccessIndexSource(TEST_EXCL_PATH + 'list1.aclj')})
        access = AccessChecker(agg, default_access='block')

        edx = access.find_access_rule('http://example.com/abc/page.html')
        assert edx['urlkey'] == 'com,example)/abc/page.html'
        assert edx['access'] == 'allow'

        edx = access.find_access_rule('http://example.com/abc/page.htm')
        assert edx['urlkey'] == 'com,example)/abc'
        assert edx['access'] == 'block'

        edx = access.find_access_rule('http://example.com/abc/')
        assert edx['urlkey'] == 'com,example)/abc'
        assert edx['access'] == 'block'

        edx = access.find_access_rule('http://foo.example.com/')
        assert edx['urlkey'] == 'com,example,'
        assert edx['access'] == 'exclude'

        edx = access.find_access_rule('http://example.com/')
        assert edx['urlkey'] == 'com,'
        assert edx['access'] == 'allow'

        edx = access.find_access_rule('foo.net')
        assert edx['urlkey'] == ''
        assert edx['access'] == 'block'

        edx = access.find_access_rule('https://example.net/abc/path/other')
        assert edx['urlkey'] == ''
        assert edx['access'] == 'block'

    def test_excludes_dir(self):
        agg = DirectoryAccessSource(TEST_EXCL_PATH)

        access = AccessChecker(agg, default_access='block')

        edx = access.find_access_rule('http://example.com/')
        assert edx['urlkey'] == 'com,example)/'
        assert edx['access'] == 'allow'

        edx = access.find_access_rule('http://example.bo')
        assert edx['urlkey'] == 'bo,example)/'
        assert edx['access'] == 'exclude'

        edx = access.find_access_rule('https://example.com/foo/path')
        assert edx['urlkey'] == 'com,example)/foo'
        assert edx['access'] == 'exclude'

        edx = access.find_access_rule('https://example.net/abc/path/other')
        assert edx['urlkey'] == 'net,example)/abc/path'
        assert edx['access'] == 'block'

        # exact-only match
        edx = access.find_access_rule('https://www.iana.org/')
        assert edx['urlkey'] == 'org,iana)/###'
        assert edx['access'] == 'allow'

        edx = access.find_access_rule('https://www.iana.org/any/other')
        assert edx['urlkey'] == 'org,iana)/'
        assert edx['access'] == 'exclude'

        edx = access.find_access_rule('https://www.iana.org/x')
        assert edx['urlkey'] == 'org,iana)/'
        assert edx['access'] == 'exclude'

        # exact-only match, first line in *.aclj file
        edx = access.find_access_rule('https://www.iana.org/exact/match/first/line/aclj/')
        assert edx['urlkey'] == 'org,iana)/exact/match/first/line/aclj###'
        assert edx['access'] == 'allow'

        # exact-only match, single rule in *.aclj file
        edx = access.find_access_rule('https://www.lonesome-rule.org/')
        assert edx['urlkey'] == 'org,lonesome-rule)/###'
        assert edx['access'] == 'allow'
