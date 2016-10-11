#!/usr/bin/python

"""
WbUrl represents the standard wayback archival url format.
A regular url is a subset of the WbUrl (latest replay).

The WbUrl expresses the common interface for interacting
with the wayback machine.

There WbUrl may represent one of the following forms:

query form: [/modifier]/[timestamp][-end_timestamp]*/<url>

modifier, timestamp and end_timestamp are optional

*/example.com
20101112030201*/http://example.com
2009-2015*/http://example.com
/cdx/*/http://example.com

url query form: used to indicate query across urls
same as query form but with a final *
*/example.com*
20101112030201*/http://example.com*


replay form:
20101112030201/http://example.com
20101112030201im_/http://example.com

latest_replay: (no timestamp)
http://example.com

Additionally, the BaseWbUrl provides the base components
(url, timestamp, end_timestamp, modifier, type) which
can be used to provide a custom representation of the
wayback url format.

"""

import re
import six

from six.moves.urllib.parse import urlsplit, urlunsplit
from six.moves.urllib.parse import quote_plus, quote, unquote_plus

from pywb.utils.loaders import to_native_str


#=================================================================
class BaseWbUrl(object):
    QUERY = 'query'
    URL_QUERY = 'url_query'
    REPLAY = 'replay'
    LATEST_REPLAY = 'latest_replay'

    def __init__(self, url='', mod='',
                 timestamp='', end_timestamp='', type=None):

        self.url = url
        self.timestamp = timestamp
        self.end_timestamp = end_timestamp
        self.mod = mod
        self.type = type

    def is_replay(self):
        return self.is_replay_type(self.type)

    def is_latest_replay(self):
        return (self.type == BaseWbUrl.LATEST_REPLAY)

    def is_query(self):
        return self.is_query_type(self.type)

    def is_url_query(self):
        return (self.type == BaseWbUrl.URL_QUERY)

    @staticmethod
    def is_replay_type(type_):
        return (type_ == BaseWbUrl.REPLAY or
                type_ == BaseWbUrl.LATEST_REPLAY)

    @staticmethod
    def is_query_type(type_):
        return (type_ == BaseWbUrl.QUERY or
                type_ == BaseWbUrl.URL_QUERY)


#=================================================================
class WbUrl(BaseWbUrl):
    # Regexs
    # ======================
    QUERY_REGEX = re.compile('^(?:([\w\-:]+)/)?(\d*)[*-](\d*)/?(.+)$')
    REPLAY_REGEX = re.compile('^(\d*)([a-z]+_|[$][a-z0-9:.-]+)?/{1,3}(.+)$')
    #LATEST_REPLAY_REGEX = re.compile('^\w_)')

    DEFAULT_SCHEME = 'http://'

    FIRST_PATH = re.compile('(?<![:/])[/?](?![/])')

    SCHEME_RX = re.compile('[a-zA-Z0-9+-.]+(:/)')


    @staticmethod
    def percent_encode_host(url):
        """ Convert the host of uri formatted with to_uri()
        to have a %-encoded host instead of punycode host
        The rest of url should be unchanged
        """

        # only continue if punycode encoded
        if 'xn--' not in url:
            return url

        parts = urlsplit(url)
        domain = parts.netloc.encode('utf-8')
        try:
            domain = domain.decode('idna')
            if six.PY2:
                domain = domain.encode('utf-8', 'ignore')
        except:
            # likely already encoded, so use as is
            pass

        domain = quote(domain)#, safe=r':\/')

        return urlunsplit((parts[0], domain, parts[2], parts[3], parts[4]))


    @staticmethod
    def to_uri(url):
        """ Converts a url to an ascii %-encoded form
        where:
        - scheme is ascii,
        - host is punycode,
        - and remainder is %-encoded
        Not using urlsplit to also decode partially encoded
        scheme urls
        """
        parts = WbUrl.FIRST_PATH.split(url, 1)

        sep = url[len(parts[0])] if len(parts) > 1 else None

        scheme_dom = unquote_plus(parts[0])

        if six.PY2 and isinstance(scheme_dom, six.binary_type):
            if scheme_dom == parts[0]:
                return url

            scheme_dom = scheme_dom.decode('utf-8', 'ignore')

        scheme_dom = scheme_dom.rsplit('/', 1)
        domain = scheme_dom[-1]

        try:
            domain = to_native_str(domain.encode('idna'), 'utf-8')
        except UnicodeError:
            # the url is invalid and this is probably not a domain
            pass

        if len(scheme_dom) > 1:
            url = to_native_str(scheme_dom[0], 'utf-8') + '/' + domain
        else:
            url = domain

        if len(parts) > 1:
            url += sep

            rest = parts[1]
            try:
                rest.encode('ascii')
            except UnicodeEncodeError:
                rest = quote(to_native_str(rest, 'utf-8'))

            url += rest

        return url

    # ======================

    def __init__(self, orig_url):
        super(WbUrl, self).__init__()

        if six.PY2 and isinstance(orig_url, six.text_type):
            orig_url = orig_url.encode('utf-8')
            orig_url = quote(orig_url)

        self._original_url = orig_url

        if not self._init_query(orig_url):
            if not self._init_replay(orig_url):
                raise Exception('Invalid WbUrl: ', orig_url)

        new_uri = WbUrl.to_uri(self.url)

        self._do_percent_encode = True

        self.url = new_uri

        if self.url.startswith('urn:'):
            return

        # protocol agnostic url -> http://
        # no protocol -> http://
        #inx = self.url.find('://')
        inx = -1
        m = self.SCHEME_RX.match(self.url)
        if m:
            inx = m.span(1)[0]

        #if inx < 0:
            # check for other partially encoded variants
        #    m = self.PARTIAL_ENC_RX.match(self.url)
        #    if m:
        #        len_ = len(m.group(0))
        #        self.url = (urllib.unquote_plus(self.url[:len_]) +
        #                    self.url[len_:])
        #        inx = self.url.find(':/')

        if inx < 0:
            self.url = self.DEFAULT_SCHEME + self.url
        else:
            inx += 2
            if inx < len(self.url) and self.url[inx] != '/':
                self.url = self.url[:inx] + '/' + self.url[inx:]

    # Match query regex
    # ======================
    def _init_query(self, url):
        query = self.QUERY_REGEX.match(url)
        if not query:
            return None

        res = query.groups('')

        self.mod = res[0]
        self.timestamp = res[1]
        self.end_timestamp = res[2]
        self.url = res[3]
        if self.url.endswith('*'):
            self.type = self.URL_QUERY
            self.url = self.url[:-1]
        else:
            self.type = self.QUERY
        return True

    # Match replay regex
    # ======================
    def _init_replay(self, url):
        replay = self.REPLAY_REGEX.match(url)
        if not replay:
            if not url:
                return None

            self.timestamp = ''
            self.mod = ''
            self.url = url
            self.type = self.LATEST_REPLAY
            return True

        res = replay.groups('')

        self.timestamp = res[0]
        self.mod = res[1]
        self.url = res[2]

        if self.timestamp:
            self.type = self.REPLAY
        else:
            self.type = self.LATEST_REPLAY

        return True

    def set_replay_timestamp(self, timestamp):
        self.timestamp = timestamp
        self.type = self.REPLAY

    def deprefix_url(self, prefix):
        rex_query = '=' + re.escape(prefix) + '([0-9])*([\w]{2}_)?/?'
        self.url = re.sub(rex_query, '=', self.url)

        rex_query = '=(' + quote_plus(prefix) + '.*?)((?:https?%3A)?%2F%2F[^&]+)'
        self.url = re.sub(rex_query, '=\\2', self.url)

        return self.url

    def get_url(self, url=None):
        if url is not None:
            url = WbUrl.to_uri(url)
        else:
            url = self.url

        if self._do_percent_encode:
            url = WbUrl.percent_encode_host(url)

        return url


    # Str Representation
    # ====================
    def to_str(self, **overrides):
        type_ = overrides.get('type', self.type)
        mod = overrides.get('mod', self.mod)
        timestamp = overrides.get('timestamp', self.timestamp)
        end_timestamp = overrides.get('end_timestamp', self.end_timestamp)

        url = self.get_url(overrides.get('url', self.url))

        return self.to_wburl_str(url=url,
                                 type=type_,
                                 mod=mod,
                                 timestamp=timestamp,
                                 end_timestamp=end_timestamp)

    @staticmethod
    def to_wburl_str(url, type=BaseWbUrl.LATEST_REPLAY,
                     mod='', timestamp='', end_timestamp=''):

        if WbUrl.is_query_type(type):
            tsmod = ''
            if mod:
                tsmod += mod + "/"

            tsmod += timestamp
            tsmod += '*'
            tsmod += end_timestamp

            tsmod += "/" + url
            if type == BaseWbUrl.URL_QUERY:
                tsmod += "*"
            return tsmod
        else:
            tsmod = timestamp + mod
            if len(tsmod) > 0:
                return tsmod + "/" + url
            else:
                return url

    @property
    def is_embed(self):
        return (self.mod and
                self.mod not in ('id_', 'mp_', 'tf_', 'bn_'))

    @property
    def is_banner_only(self):
        return (self.mod == 'bn_')

    @property
    def is_url_rewrite_only(self):
        return (self.mod == 'uo_')

    @property
    def is_identity(self):
        return (self.mod == 'id_')

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return str((self.type, self.timestamp, self.mod, self.url, str(self)))
