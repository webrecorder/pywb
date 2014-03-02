from pywb.cdx.cdxops import cdx_load
from pywb.cdx.perms import AllowAllPerms
from pywb.cdx.query import CDXQuery
from pywb.cdx.cdxobject import AccessException

from pytest import raises

class BlockAllPerms(AllowAllPerms):
    def allow_url_lookup(self, urlkey, url):
        return False


def test_exclusion_short_circuit():
    """
    # Verify that exclusion check 'short-circuits' further evaluation.. eg, a bad cdx source is not even loaded
    # if exclusion check does not pass
    """
    cdx_iter = cdx_load(['bogus ignored'], CDXQuery(url='example.com', key='com,example)/'),
                        perms_checker=BlockAllPerms(), process=True)

    # exception happens on first access attempt
    with raises(AccessException):
        cdx_iter.next()





