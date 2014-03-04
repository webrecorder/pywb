from pywb.utils.wbexception import AccessException
from pywb.cdx.cdxops import cdx_load
from pywb.cdx.query import CDXQuery

from pytest import raises

KEY = 'com,example)/'

#================================================================
def raise_access_exception(cdx_iter, query):
    if query.key == KEY:
        raise AccessException

    for cdx in cdx_iter:
        yield

#================================================================
def lazy_cdx_load(**params):
    """
    # Verify that an op 'short-circuits' further evaluation.. eg, a bad cdx source is not even loaded
    # as soon as exception is thrown

    Exception is thrown on first .next() access, not on the cdx_load
    """
    params['custom_ops'] = [raise_access_exception]

    cdx_iter = cdx_load(['bogus ignored'],
                        CDXQuery(**params),
                        process=True)

    # exception happens on first access attempt
    with raises(AccessException):
        cdx_iter.next()


def test_no_process():
    lazy_cdx_load(key=KEY)

def test_reverse():
    lazy_cdx_load(key=KEY, reverse=True)

def test_closest():
    lazy_cdx_load(key=KEY, closest='2013')

def test_limit():
    lazy_cdx_load(key=KEY, limit=10)

def test_multi_ops():
    lazy_cdx_load(key=KEY,
                  resolveRevisits=True,
                  filters=['=filename:A'],
                  collapseTime=10,
                  reverse=True,
                  closest='2013',
                  limit=5,
                  fields='timestamp,filename',
                  output='text')



