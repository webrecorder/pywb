#!/usr/bin/env python
# -*- coding: utf-8 -*-

ur"""
# Replay Urls
# ======================
>>> repr(WbUrl('20131010000506/example.com'))
"('replay', '20131010000506', '', 'http://example.com', '20131010000506/http://example.com')"

>>> repr(WbUrl('20130102im_/https://example.com'))
"('replay', '20130102', 'im_', 'https://example.com', '20130102im_/https://example.com')"

>>> repr(WbUrl('20130102im_/https:/example.com'))
"('replay', '20130102', 'im_', 'https://example.com', '20130102im_/https://example.com')"

# Protocol agnostic convert to http
>>> repr(WbUrl('20130102im_///example.com'))
"('replay', '20130102', 'im_', 'http://example.com', '20130102im_/http://example.com')"

>>> repr(WbUrl('cs_/example.com'))
"('latest_replay', '', 'cs_', 'http://example.com', 'cs_/http://example.com')"

>>> repr(WbUrl('https://example.com/xyz'))
"('latest_replay', '', '', 'https://example.com/xyz', 'https://example.com/xyz')"

>>> repr(WbUrl('https:/example.com/xyz'))
"('latest_replay', '', '', 'https://example.com/xyz', 'https://example.com/xyz')"

>>> repr(WbUrl('https://example.com/xyz?a=%2f&b=%2E'))
"('latest_replay', '', '', 'https://example.com/xyz?a=%2f&b=%2E', 'https://example.com/xyz?a=%2f&b=%2E')"

# Test scheme partially encoded urls
>>> repr(WbUrl('https%3A//example.com/'))
"('latest_replay', '', '', 'https://example.com/', 'https://example.com/')"

>>> repr(WbUrl('2014/http%3A%2F%2Fexample.com/'))
"('replay', '2014', '', 'http://example.com/', '2014/http://example.com/')"

# Test IDNs
>>> repr(WbUrl(u'http://пример.испытание'))
"('latest_replay', '', '', 'http://xn--e1afmkfd.xn--80akhbyknj4f', 'http://xn--e1afmkfd.xn--80akhbyknj4f')"

>>> repr(WbUrl(u'https://пример.испытание/abc/'))
"('latest_replay', '', '', 'https://xn--e1afmkfd.xn--80akhbyknj4f/abc/', 'https://xn--e1afmkfd.xn--80akhbyknj4f/abc/')"

>>> repr(WbUrl(u'//пример.испытание/abc/'))
"('latest_replay', '', '', 'http://xn--e1afmkfd.xn--80akhbyknj4f/abc/', 'http://xn--e1afmkfd.xn--80akhbyknj4f/abc/')"

>>> repr(WbUrl(u'2014id_/https://пример.испытание/abc'))
"('replay', '2014', 'id_', 'https://xn--e1afmkfd.xn--80akhbyknj4f/abc', '2014id_/https://xn--e1afmkfd.xn--80akhbyknj4f/abc')"

# percent-encoded form (as sent by browser usually)
>>> repr(WbUrl('2014id_/http://' + quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc'))
"('replay', '2014', 'id_', 'http://xn--e1afmkfd.xn--80akhbyknj4f/abc', '2014id_/http://xn--e1afmkfd.xn--80akhbyknj4f/abc')"

# percent-encoded form -- scheme relative
>>> repr(WbUrl('2014id_///' + quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc'))
"('replay', '2014', 'id_', 'http://xn--e1afmkfd.xn--80akhbyknj4f/abc', '2014id_/http://xn--e1afmkfd.xn--80akhbyknj4f/abc')"

# invalid: truncated and superfluous '%', ignore invalid (no exception)
>>> repr(WbUrl('2014id_/http://' + quote_plus(u'пример.испытание'.encode('utf-8'))[1:] + '%' + '/abc'))
"('replay', '2014', 'id_', 'http://xn--d0-olcluwd.xn--%-7sbpkb3ampk3g/abc', '2014id_/http://xn--d0-olcluwd.xn--%-7sbpkb3ampk3g/abc')"


# Query Urls
# ======================
>>> repr(WbUrl('*/http://example.com/abc?def=a'))
"('query', '', '', 'http://example.com/abc?def=a', '*/http://example.com/abc?def=a')"

>>> repr(WbUrl('*/http://example.com/abc?def=a*'))
"('url_query', '', '', 'http://example.com/abc?def=a', '*/http://example.com/abc?def=a*')"

>>> repr(WbUrl('2010*/http://example.com/abc?def=a'))
"('query', '2010', '', 'http://example.com/abc?def=a', '2010*/http://example.com/abc?def=a')"

# timestamp range query
>>> repr(WbUrl('2009-2015*/http://example.com/abc?def=a'))
"('query', '2009', '', 'http://example.com/abc?def=a', '2009-2015*/http://example.com/abc?def=a')"

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
#>>> x = WbUrl('/#$%#/')
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
from urllib import quote_plus

if __name__ == "__main__":
    import doctest
    doctest.testmod()
