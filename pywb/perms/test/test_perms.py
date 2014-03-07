from pywb.cdx.cdxops import cdx_load
from pywb.cdx.query import CDXQuery
from pywb.cdx.cdxserver import CDXServer
from pywb.utils.wbexception import AccessException
from pywb.core.indexreader import IndexReader

#from pywb.perms.perms_filter import AllowAllPerms

from pytest import raises

from tests.fixture import testconfig


#================================================================
def test_excluded(testconfig):
    sources = testconfig.get('index_paths')
    perms_policy = testconfig.get('perms_policy')

    cdx_server = CDXServer(sources)
    index_reader = IndexReader(cdx_server, perms_policy)

    url = 'http://www.iana.org/_img/bookmark_icon.ico'

    params = dict(url=url)

    with raises(AccessException):
        cdxobjs = list(index_reader.load_cdx(None, params))
        print cdxobjs
