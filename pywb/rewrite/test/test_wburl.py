#!/usr/bin/env python
# -*- coding: utf-8 -*-

ur"""
# Replay Urls
# ======================
>>> repr_unicode(WbUrl('20131010000506/example.com'))
('replay', '20131010000506', '', 'http://example.com', '20131010000506/http://example.com')

>>> repr_unicode(WbUrl('20130102im_/https://example.com'))
('replay', '20130102', 'im_', 'https://example.com', '20130102im_/https://example.com')

>>> repr_unicode(WbUrl('20130102im_/https:/example.com'))
('replay', '20130102', 'im_', 'https://example.com', '20130102im_/https://example.com')

# Protocol agnostic convert to http
>>> repr_unicode(WbUrl('20130102im_///example.com'))
('replay', '20130102', 'im_', 'http://example.com', '20130102im_/http://example.com')

>>> repr_unicode(WbUrl('cs_/example.com'))
('latest_replay', '', 'cs_', 'http://example.com', 'cs_/http://example.com')

>>> repr_unicode(WbUrl('https://example.com/xyz'))
('latest_replay', '', '', 'https://example.com/xyz', 'https://example.com/xyz')

>>> repr_unicode(WbUrl('https:/example.com/xyz'))
('latest_replay', '', '', 'https://example.com/xyz', 'https://example.com/xyz')

>>> repr_unicode(WbUrl('https://example.com/xyz?a=%2f&b=%2E'))
('latest_replay', '', '', 'https://example.com/xyz?a=/&b=.', 'https://example.com/xyz?a=/&b=.')

# Test scheme partially encoded urls
>>> repr_unicode(WbUrl('https%3A//example.com/'))
('latest_replay', '', '', 'https://example.com/', 'https://example.com/')

>>> repr_unicode(WbUrl('2014/http%3A%2F%2Fexample.com/'))
('replay', '2014', '', 'http://example.com/', '2014/http://example.com/')

# Test IDNs

To IRI
>>> print(WbUrl.to_iri(u'https://пример.испытание'))
https://пример.испытание

>>> print(WbUrl.to_iri(u'пример.испытание'))
пример.испытание

>>> print(WbUrl.to_iri('http://' + quote_plus(u'пример.испытание'.encode('utf-8'))))
http://пример.испытание

>>> print(WbUrl.to_iri(u'//пример.испытание/abc/испытание'))
//пример.испытание/abc/испытание

>>> print(WbUrl.to_iri(quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc/' + quote_plus(u'пример'.encode('utf-8'))))
пример.испытание/abc/пример

>>> print(WbUrl.to_iri('https://xn--e1afmkfd.xn--80akhbyknj4f'))
https://пример.испытание


To URI
>>> print(WbUrl.to_uri(u'https://пример.испытание'))
https://xn--e1afmkfd.xn--80akhbyknj4f

>>> print(WbUrl.to_uri(u'пример.испытание'))
xn--e1afmkfd.xn--80akhbyknj4f

>>> print(WbUrl.to_uri('http://' + quote_plus(u'пример.испытание'.encode('utf-8'))))
http://xn--e1afmkfd.xn--80akhbyknj4f

>>> print(WbUrl.to_uri(u'//пример.испытание/abc/испытание'))
//xn--e1afmkfd.xn--80akhbyknj4f/abc%2F%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B5

>>> print(WbUrl.to_uri('//' + quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc/' + quote_plus(u'пример'.encode('utf-8'))))
//xn--e1afmkfd.xn--80akhbyknj4f/abc/%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80

>>> print(WbUrl.to_uri('https://xn--e1afmkfd.xn--80akhbyknj4f/abc/'))
https://xn--e1afmkfd.xn--80akhbyknj4f/abc/

>>> print(WbUrl.to_uri('http://' + quote_plus(u'пример.испытание'.encode('utf-8'))[1:]))
http://xn--d0-olcluwd.xn--80akhbyknj4f

# IRI representation
>>> repr_unicode(WbUrl(u'http://пример.испытание'))
('latest_replay', '', '', 'http://пример.испытание', 'http://пример.испытание')

>>> repr_unicode(WbUrl(u'https://пример.испытание/abc/'))
('latest_replay', '', '', 'https://пример.испытание/abc/', 'https://пример.испытание/abc/')

>>> repr_unicode(WbUrl(u'//пример.испытание/abc/'))
('latest_replay', '', '', 'http://пример.испытание/abc/', 'http://пример.испытание/abc/')

>>> repr_unicode(WbUrl(u'2014id_/https://пример.испытание/abc'))
('replay', '2014', 'id_', 'https://пример.испытание/abc', '2014id_/https://пример.испытание/abc')

# percent-encoded form (as sent by browser usually)
>>> repr_unicode(WbUrl('2014id_/http://' + quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc'))
('replay', '2014', 'id_', 'http://пример.испытание/abc', '2014id_/http://пример.испытание/abc')

# percent-encoded form -- scheme relative
>>> repr_unicode(WbUrl('2014id_///' + quote_plus(u'пример.испытание'.encode('utf-8')) + '/abc'))
('replay', '2014', 'id_', 'http://пример.испытание/abc', '2014id_/http://пример.испытание/abc')

# invalid: truncated and superfluous '%', ignore invalid (no exception)
>>> repr_unicode(WbUrl('2014id_/http://' + quote_plus(u'пример.испытание'.encode('utf-8'))[1:] + '%' + '/abc'))
('replay', '2014', 'id_', 'http://d0ример.испытание%/abc', '2014id_/http://d0ример.испытание%/abc')


# Query Urls
# ======================
>>> repr_unicode(WbUrl('*/http://example.com/abc?def=a'))
('query', '', '', 'http://example.com/abc?def=a', '*/http://example.com/abc?def=a')

>>> repr_unicode(WbUrl('*/http://example.com/abc?def=a*'))
('url_query', '', '', 'http://example.com/abc?def=a', '*/http://example.com/abc?def=a*')

>>> repr_unicode(WbUrl('2010*/http://example.com/abc?def=a'))
('query', '2010', '', 'http://example.com/abc?def=a', '2010*/http://example.com/abc?def=a')

# timestamp range query
>>> repr_unicode(WbUrl('2009-2015*/http://example.com/abc?def=a'))
('query', '2009', '', 'http://example.com/abc?def=a', '2009-2015*/http://example.com/abc?def=a')

>>> repr_unicode(WbUrl('json/*/http://example.com/abc?def=a'))
('query', '', 'json', 'http://example.com/abc?def=a', 'json/*/http://example.com/abc?def=a')

>>> repr_unicode(WbUrl('timemap-link/2011*/http://example.com/abc?def=a'))
('query', '2011', 'timemap-link', 'http://example.com/abc?def=a', 'timemap-link/2011*/http://example.com/abc?def=a')

# strip off repeated, likely scheme-agnostic, slashes altogether
>>> repr_unicode(WbUrl('///example.com'))
('latest_replay', '', '', 'http://example.com', 'http://example.com')

>>> repr_unicode(WbUrl('//example.com/'))
('latest_replay', '', '', 'http://example.com/', 'http://example.com/')

>>> repr_unicode(WbUrl('/example.com/'))
('latest_replay', '', '', 'http://example.com/', 'http://example.com/')

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
from urllib import quote_plus, unquote_plus

from StringIO import StringIO


def repr_unicode(wburl):
    buff = StringIO()
    buff.write("('{0}', '{1}', '{2}', '".format(wburl.type, wburl.timestamp, wburl.mod))
    buff.write(WbUrl.to_iri(wburl.url))
    buff.write("', '")
    buff.write(wburl.to_str(iri=True))
    buff.write("')")
    print(buff.getvalue())


if __name__ == "__main__":
    import doctest
    doctest.testmod()
