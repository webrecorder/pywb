import os
import pytest

import yaml

@pytest.fixture
def testconfig():
    config = yaml.load(open('test_config.yaml'))
    assert config
    if 'index_paths' not in config:
        # !!! assumes this module is in a sub-directory of project root.
        config['index_paths'] = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '../sample_archive/cdx')
    return config

#================================================================
# Reporter callback for replay view
class PrintReporter:
    """Reporter callback for replay view.
    """
    def __call__(self, wbrequest, cdx, response):
        print wbrequest
        print cdx
        pass

#================================================================
class TestExclusionPerms:
    """
    Perm Checker fixture which can block one URL.
    """
    # sample_archive has captures for this URLKEY
    URLKEY_EXCLUDED = 'org,iana)/_img/bookmark_icon.ico'

    def allow_url_lookup(self, urlkey, url):
        """
        Return true/false if url or urlkey (canonicalized url)
        should be allowed
        """
        print "allow_url_lookup:urlkey={}".format(urlkey)
        if urlkey == self.URLKEY_EXCLUDED:
            return False

        return True

    def allow_capture(self, cdx):
        """
        Return True if specified capture (cdx) is allowed.
        """
        return True

    def filter_fields(self, cdx):
        """
        Filter out any forbidden cdx fields from cdx object
        """
        return cdx
