import os
import pytest

import yaml

from pywb.perms.perms_filter import AllowAllPerms, AllowAllPermsPolicy

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
class TestExclusionPerms(AllowAllPerms):
    """
    Perm Checker fixture to block a single url for testing
    """
    # sample_archive has captures for this URLKEY
    URLKEY_EXCLUDED = 'org,iana)/_img/bookmark_icon.ico'

    def allow_url_lookup(self, urlkey):
        """
        Return true/false if url (canonicalized url)
        should be allowed
        """
        if urlkey == self.URLKEY_EXCLUDED:
            return False

        return super(TestExclusionPerms, self).allow_url_lookup(urlkey)


#================================================================
class TestExclusionPermsPolicy(AllowAllPermsPolicy):
    def create_perms_checker(self, wbrequest):
        return TestExclusionPerms()
