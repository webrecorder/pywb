from pywb.utils.wbexception import AccessException
from pywb.warcserver.index.cdxops import cdx_load
from pywb.warcserver.index.query import CDXQuery

from pytest import raises

import six


URL = 'http://example.com/'


#================================================================
def raise_access_exception(cdx_iter, query):
    if query.url == URL:
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
                        CDXQuery(params),
                        process=True)

    # exception happens on first access attempt
    with raises(AccessException):
        six.next(cdx_iter)


def test_no_process():
    lazy_cdx_load(url=URL)

def test_reverse():
    lazy_cdx_load(url=URL, reverse=True)

def test_closest():
    lazy_cdx_load(url=URL, closest='2013')

def test_limit():
    lazy_cdx_load(url=URL, limit=10)

def test_limit_1_reverse():
    lazy_cdx_load(url=URL, limit=1, reverse=True)

def test_multi_ops():
    lazy_cdx_load(url=URL,
                  resolveRevisits=True,
                  filters=['=filename:A'],
                  collapseTime=10,
                  reverse=True,
                  closest='2013',
                  limit=5,
                  fields='timestamp,filename',
                  output='text')



