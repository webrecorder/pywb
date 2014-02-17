from pywb.utils.binsearch import iter_exact, iter_prefix
from pywb.utils.loaders import SeekableTextFileReader

import urllib
import urllib2


#=================================================================
class CDXSource(object):
    """
    Represents any cdx index source
    """
    def load_cdx(self, params):
        raise NotImplementedError('Implement in subclass')


#=================================================================
class CDXFile(CDXSource):
    """
    Represents a local plain-text .cdx file
    """
    def __init__(self, filename):
        self.filename = filename

    def load_cdx(self, params):
        source = SeekableTextFileReader(self.filename)

        match_type = params.get('match_type')

        if match_type == 'prefix':
            iter_func = iter_prefix
        else:
            iter_func = iter_exact

        key = params.get('key')

        return iter_func(source, key)

    def __str__(self):
        return 'CDX File - ' + self.filename


#=================================================================
class RemoteCDXSource(CDXSource):
    """
    Represents a remote cdx server, to which requests will be proxied.

    Only url and match type params are proxied at this time,
    the stream is passed through all other filters locally.
    """
    def __init__(self, filename, cookie=None, proxy_all=True):
        self.remote_url = filename
        self.cookie = cookie
        self.proxy_all = proxy_all

    def load_cdx(self, proxy_params):
        if self.proxy_all:
            params = proxy_params
            params['proxy_all'] = True
        else:
            # Only send url and matchType params to remote
            params = {}
            params['url'] = proxy_params['url']
            match_type = proxy_params.get('match_type')

            if match_type:
                proxy_params['matchType'] = match_type

        urlparams = urllib.urlencode(params, True)

        try:
            request = urllib2.Request(self.remote_url, urlparams)

            if self.cookie:
                request.add_header('Cookie', self.cookie)

            response = urllib2.urlopen(request)

        except urllib2.HTTPError as e:
            if e.code == 403:
                exc_msg = e.read()
                msg = ('Blocked By Robots' if 'Blocked By Robots' in exc_msg
                       else 'Excluded')

                raise AccessException(msg)
            else:
                raise

        return iter(response)

    def __str__(self):
        return 'Remote CDX Server: ' + self.remote_url
