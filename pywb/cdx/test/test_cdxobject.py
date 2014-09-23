from pywb.cdx.cdxobject import CDXObject, IDXObject, CDXException
from pytest import raises

def test_empty_cdxobject():
    x = CDXObject('')
    assert len(x) == 0

def test_invalid_cdx_format():
    with raises(CDXException):
        x = CDXObject('a b c')


def _make_line(fields):
    line = ' '.join(['-'] * fields)
    x = CDXObject(line)
    assert len(x) == fields
    assert str(x) == line

def test_valid_cdx_formats():
    # Currently supported cdx formats, 9, 11, 12, 14 field
    # See CDXObject for more details
    _make_line(9)
    _make_line(12)

    _make_line(11)
    _make_line(14)

def test_invalid_idx_format():
    with raises(CDXException):
        x = IDXObject('a b c')


