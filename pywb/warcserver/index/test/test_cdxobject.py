#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pywb.warcserver.index.cdxobject import CDXObject, IDXObject, CDXException
from pytest import raises

def test_empty_cdxobject():
    x = CDXObject(b'')
    assert len(x) == 0

def test_invalid_cdx_format():
    with raises(CDXException):
        x = CDXObject(b'a b c')


def _make_line(fields):
    line = ' '.join(['-'] * fields)
    x = CDXObject(line.encode('utf-8'))
    assert len(x) == fields
    assert str(x) == line

def test_valid_cdx_formats():
    # Currently supported cdx formats, 9, 11, 12, 14 field
    # See CDXObject for more details
    _make_line(9)
    _make_line(12)

    _make_line(11)
    _make_line(14)

def test_unicode_url():
    x = CDXObject(u'com,example,cafe)/ 123 {"url": "http://example.com/café/path"}'.encode('utf-8'))
    assert x['urlkey'] == 'com,example,cafe)/'
    assert x['timestamp'] == '123'
    assert x['url'] == 'http://example.com/caf%C3%A9/path'

    assert x.to_cdxj() == 'com,example,cafe)/ 123 {"url": "http://example.com/caf%C3%A9/path"}\n'

def test_invalid_idx_format():
    with raises(CDXException):
        x = IDXObject(b'a b c')


def test_lt_le():
    A = CDXObject(b'ca,example)/ 2016 {"url": "http://example.com/"}')
    B = CDXObject(b'com,example)/ 2015 {"url": "http://example.com/"}')
    C = CDXObject(b'com,example)/ 2016 {"url": "http://example.com/"}')

    assert A < B
    assert B < C
    assert B >= A
    assert C >= A
    assert A < C


