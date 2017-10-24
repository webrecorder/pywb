#!/usr/bin/env python
# -*- coding: utf-8 -*-

u"""
# Replay Urls
# ======================
>>> repr(WbUrl('20131010000506/example.com'))
"('replay', '20131010000506', '', 'http://example.com', '20131010000506/http://example.com')"

>>> repr(WbUrl('20130102im_/https://example.com'))
"('replay', '20130102', 'im_', 'https://example.com', '20130102im_/https://example.com')"

>>> repr(WbUrl('20130102im_/https:/example.com'))
"('replay', '20130102', 'im_', 'https://example.com', '20130102im_/https://example.com')"

>>> repr(WbUrl('20130102$cbr:test-foo.123/https:/example.com'))
"('replay', '20130102', '$cbr:test-foo.123', 'https://example.com', '20130102$cbr:test-foo.123/https://example.com')"

# Protocol agnostic convert to http
>>> repr(WbUrl('20130102im_///example.com'))
"('replay', '20130102', 'im_', 'http://example.com', '20130102im_/http://example.com')"

>>> repr(WbUrl('cs_/example.com'))
"('latest_replay', '', 'cs_', 'http://example.com', 'cs_/http://example.com')"

>>> repr(WbUrl('cs_/example.com/?foo=http://example.com/'))
"('latest_replay', '', 'cs_', 'http://example.com/?foo=http://example.com/', 'cs_/http://example.com/?foo=http://example.com/')"

>>> repr(WbUrl('im_/20130102.org'))
"('latest_replay', '', 'im_', 'http://20130102.org', 'im_/http://20130102.org')"

>>> repr(WbUrl('$cbr:test-foo.123/https:/example.com'))
"('latest_replay', '', '$cbr:test-foo.123', 'https://example.com', '$cbr:test-foo.123/https://example.com')"

>>> repr(WbUrl('20130102.example.com'))
"('latest_replay', '', '', 'http://20130102.example.com', 'http://20130102.example.com')"

>>> repr(WbUrl('20130102.org/1'))
"('latest_replay', '', '', 'http://20130102.org/1', 'http://20130102.org/1')"

>>> repr(WbUrl('20130102/1.com'))
"('replay', '20130102', '', 'http://1.com', '20130102/http://1.com')"

>>> repr(WbUrl('https://example.com/xyz'))
"('latest_replay', '', '', 'https://example.com/xyz', 'https://example.com/xyz')"

>>> repr(WbUrl('https:/example.com/xyz'))
"('latest_replay', '', '', 'https://example.com/xyz', 'https://example.com/xyz')"

>>> repr(WbUrl('https://example.com/xyz?a=%2f&b=%2E'))
"('latest_replay', '', '', 'https://example.com/xyz?a=%2f&b=%2E', 'https://example.com/xyz?a=%2f&b=%2E')"

>>> repr(WbUrl('http://example.com?example=2'))
"('latest_replay', '', '', 'http://example.com?example=2', 'http://example.com?example=2')"

>>> repr(WbUrl('http://example.com/xyz##abc'))
"('latest_replay', '', '', 'http://example.com/xyz##abc', 'http://example.com/xyz##abc')"

# support urn: prefix
>>> repr(WbUrl('urn:X-wpull:log'))
"('latest_replay', '', '', 'urn:X-wpull:log', 'urn:X-wpull:log')"

# Test scheme partially encoded urls
>>> repr(WbUrl('https%3A//example.com/'))
"('latest_replay', '', '', 'https://example.com/', 'https://example.com/')"

>>> repr(WbUrl('2014/http%3A%2F%2Fexample.com/'))
"('replay', '2014', '', 'http://example.com/', '2014/http://example.com/')"

# ===== Test IDNs

To URI
>>> print(WbUrl.to_uri(u'https://пример.испытание'))
https://xn--e1afmkfd.xn--80akhbyknj4f

>>> print(WbUrl.to_uri(u'пример.испытание'))
xn--e1afmkfd.xn--80akhbyknj4f

>>> print(WbUrl.to_uri('http://' + quote_plus(u'пример.испытание'.encode('utf-8'))))
http://xn--e1afmkfd.xn--80akhbyknj4f

>>> print(WbUrl.to_uri(u'//пример.испытание/abc/испытание'))
//xn--e1afmkfd.xn--80akhbyknj4f/abc/%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5

>>> print(WbUrl.to_uri('//' + quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc/' + quote_plus(u'пример'.encode('utf-8'))))
//xn--e1afmkfd.xn--80akhbyknj4f/abc/%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80

>>> print(WbUrl.to_uri('https://xn--e1afmkfd.xn--80akhbyknj4f/foo/bar?abc=def'))
https://xn--e1afmkfd.xn--80akhbyknj4f/foo/bar?abc=def

>>> print(WbUrl.to_uri('somescheme://test?foo=bar%9F'))
somescheme://test?foo=bar%9F

>>> print(WbUrl.to_uri('/test/foo=bar%9F'))
/test/foo=bar%9F

# SKIP TRUNC
# truncated
#>>> print(WbUrl.to_uri('http://' + quote_plus(to_native_str(u'пример.испытание', 'utf-8'))[1:]))
#http://xn--d0-olcluwd.xn--80akhbyknj4f


# To %-encoded host uri -- instead of punycode, %-encode host

>>> print(to_uri_pencode(u'https://пример.испытание'))
https://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5

>>> print(to_uri_pencode(u'пример.испытание'))
http://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5

>>> print(to_uri_pencode('http://' + quote_plus(u'пример.испытание'.encode('utf-8'))))
http://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5

>>> print(to_uri_pencode(u'//пример.испытание/abc/испытание'))
http://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/abc/%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5

>>> print(to_uri_pencode(quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc/' + quote_plus(u'пример'.encode('utf-8'))))
http://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/abc/%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80

>>> print(to_uri_pencode('https://xn--e1afmkfd.xn--80akhbyknj4f/foo/bar?abc=def'))
https://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/foo/bar?abc=def

# SKIP TRUNC
#>>> print(to_uri_pencode('http://' + quote_plus(u'пример.испытание'.encode('utf-8'))[1:]))
http://d0%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5

# invalid
>>> print(to_uri_pencode('http://xn--abcd'))
http://xn--abcd

# some bizzare input, ensure exception is caught
>>> print(WbUrl.to_uri('%20' * 100))
<BLANKLINE>

# IRI representation
>>> repr(WbUrl(u'http://пример.испытание'))
"('latest_replay', '', '', 'http://xn--e1afmkfd.xn--80akhbyknj4f', 'http://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5')"

>>> x = WbUrl(u'http://пример.испытание'); x._do_percent_encode = False; repr(x)
"('latest_replay', '', '', 'http://xn--e1afmkfd.xn--80akhbyknj4f', 'http://xn--e1afmkfd.xn--80akhbyknj4f')"

>>> repr(WbUrl(u'https://пример.испытание/abc/def_ghi/'))
"('latest_replay', '', '', 'https://xn--e1afmkfd.xn--80akhbyknj4f/abc/def_ghi/', 'https://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/abc/def_ghi/')"

>>> repr(WbUrl(u'//пример.испытание/abc/'))
"('latest_replay', '', '', 'http://xn--e1afmkfd.xn--80akhbyknj4f/abc/', 'http://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/abc/')"

>>> repr(WbUrl(u'2014id_/https://пример.испытание/abc'))
"('replay', '2014', 'id_', 'https://xn--e1afmkfd.xn--80akhbyknj4f/abc', '2014id_/https://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/abc')"

# percent-encoded form (as sent by browser usually)
>>> repr(WbUrl('2014id_/http://' + quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc'))
"('replay', '2014', 'id_', 'http://xn--e1afmkfd.xn--80akhbyknj4f/abc', '2014id_/http://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/abc')"

# percent-encoded form -- scheme relative
>>> repr(WbUrl('2014id_///' + quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc'))
"('replay', '2014', 'id_', 'http://xn--e1afmkfd.xn--80akhbyknj4f/abc', '2014id_/http://%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5/abc')"

# SKIP TRUNC
# invalid: truncated and superfluous '%', ignore invalid (no exception)
#>>> repr(WbUrl('2014id_/http://' + quote_plus(u'пример.испытание'.encode('utf-8'))[1:] + '%' + '/abc'))
"('replay', '2014', 'id_', 'http://xn--d0-olcluwd.xn--%-7sbpkb3ampk3g/abc', '2014id_/http://d0%D1%80%D0%B8%D0%BC%D0%B5%D1%80.%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5%25/abc')"


# Query Urls
# ======================
>>> repr(WbUrl('*/http://example.com/abc?def=a'))
"('query', '', '', 'http://example.com/abc?def=a', '*/http://example.com/abc?def=a')"

>>> repr(WbUrl('*/http://example.com/abc?def=a*'))
"('url_query', '', '', 'http://example.com/abc?def=a', '*/http://example.com/abc?def=a*')"

>>> repr(WbUrl('2010*/http://example.com/abc?def=a'))
"('query', '2010', '', 'http://example.com/abc?def=a', '2010*/http://example.com/abc?def=a')"

# timestamp range query
>>> repr(WbUrl('2010-/http://example.com/abc?def=a'))
"('query', '2010', '', 'http://example.com/abc?def=a', '2010*/http://example.com/abc?def=a')"

>>> repr(WbUrl('2009-2015/http://example.com/abc?def=a'))
"('query', '2009', '', 'http://example.com/abc?def=a', '2009*2015/http://example.com/abc?def=a')"

>>> repr(WbUrl('2009*2015/http://example.com/abc?def=a'))
"('query', '2009', '', 'http://example.com/abc?def=a', '2009*2015/http://example.com/abc?def=a')"

>>> repr(WbUrl('2009*/http://example.com/abc?def=a'))
"('query', '2009', '', 'http://example.com/abc?def=a', '2009*/http://example.com/abc?def=a')"

>>> repr(WbUrl('-2015/http://example.com/abc?def=a'))
"('query', '', '', 'http://example.com/abc?def=a', '*2015/http://example.com/abc?def=a')"

>>> repr(WbUrl('*2015/http://example.com/abc?def=a'))
"('query', '', '', 'http://example.com/abc?def=a', '*2015/http://example.com/abc?def=a')"

>>> repr(WbUrl('json/*/http://example.com/abc?def=a'))
"('query', '', 'json', 'http://example.com/abc?def=a', 'json/*/http://example.com/abc?def=a')"

>>> repr(WbUrl('timemap-link/2011*/http://example.com/abc?def=a'))
"('query', '2011', 'timemap-link', 'http://example.com/abc?def=a', 'timemap-link/2011*/http://example.com/abc?def=a')"

# strip off repeated, likely scheme-agnostic, slashes altogether
>>> repr(WbUrl('///example.com'))
"('latest_replay', '', '', 'http://example.com', 'http://example.com')"

>>> repr(WbUrl('//example.com/'))
"('latest_replay', '', '', 'http://example.com/', 'http://example.com/')"

>>> repr(WbUrl('/example.com/'))
"('latest_replay', '', '', 'http://example.com/', 'http://example.com/')"

# Is_ Tests
>>> u = WbUrl('*/http://example.com/abc?def=a*')
>>> u.is_url_query()
True

>>> u.is_query()
True

>>> u2 = WbUrl('20130102im_/https:/example.com')
>>> u2.is_embed
True

>>> u2.is_replay()
True


# Error Urls
# ======================
# no longer rejecting this here
#>>> x = WbUrl('/#$%#/')"
Traceback (most recent call last):
Exception: Bad Request Url: http://#$%#/

#>>> x = WbUrl('/http://example.com:abc/')
#Traceback (most recent call last):
#Exception: Bad Request Url: http://example.com:abc/

>>> x = WbUrl('')
Traceback (most recent call last):
Exception: ('Invalid WbUrl: ', '')

# considered blank
>>> x = WbUrl('https:/')
>>> x = WbUrl('https:///')
>>> x = WbUrl('http://')
"""

from pywb.rewrite.wburl import WbUrl
from six.moves.urllib.parse import quote_plus, unquote_plus

from warcio.utils import to_native_str

from io import StringIO


def to_uri_pencode(url):
    return WbUrl(url).get_url()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
