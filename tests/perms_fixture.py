"""
An example perms policy used as a testing fixture
this policy is enabled by adding the following setting to the
main config.yaml

perms_policy: !!python/name:pywb.perms.test.test_perms_policy.perms_policy
"""

from pywb.perms.perms_filter import Perms


#================================================================
class TestExclusionPerms(Perms):
    """
    Perm Checker fixture to block a single url for testing
    """
    # sample_archive has captures for this URLKEY
    URLKEY_EXCLUDED = b'org,iana)/_img/bookmark_icon.ico'

    def allow_url_lookup(self, urlkey):
        """
        Return true/false if url (canonicalized url)
        should be allowed
        """
        print(urlkey)
        if urlkey == self.URLKEY_EXCLUDED:
            return False

        return super(TestExclusionPerms, self).allow_url_lookup(urlkey)


#================================================================
def perms_policy(wbrequest):
    return TestExclusionPerms()
