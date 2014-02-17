import surt
from cdxops import cdx_load

import itertools
import logging
import os
import urlparse

from cdxsource import CDXSource, CDXFile, RemoteCDXSource


#=================================================================
class CDXException(Exception):
    def status(self):
        return '400 Bad Request'


#=================================================================
class AccessException(CDXException):
    def status(self):
        return '403 Bad Request'


#=================================================================
class CDXServer:
    """
    Top-level cdx server object which maintains a list of cdx sources,
    responds to queries and dispatches to the cdx ops for processing
    """

    @staticmethod
    def create_from_config(config):
        paths = config.get('index_paths')
        surt_ordered = config.get('surt_ordered', True)
        return CDXServer(paths, surt_ordered)

    def __init__(self, sources, surt_ordered=True):
        self.sources = []
        self.surt_ordered = surt_ordered

        logging.debug('CDX Surt-Ordered? ' + str(surt_ordered))

        if not isinstance(sources, list):
            sources = [sources]

        for src in sources:
            if isinstance(src, CDXSource):
                self.add_cdx_source(src)
            elif isinstance(src, str):
                if os.path.isdir(src):
                    for file in os.listdir(src):
                        self.add_cdx_source(src + file)
                else:
                    self.add_cdx_source(src)

        if len(self.sources) == 0:
            logging.exception('No CDX Sources Found from: ' + str(sources))

    def add_cdx_source(self, source):
        if not isinstance(source, CDXSource):
            source = self.create_cdx_source(source)
            if not source:
                return

        logging.debug('Adding CDX Source: ' + str(source))
        self.sources.append(source)

    @staticmethod
    def create_cdx_source(filename):
        if filename.startswith('http://') or filename.startswith('https://'):
            return RemoteCDXSource(filename)

        if filename.endswith('.cdx'):
            return CDXFile(filename)

        return None
        #TODO: support zipnum
        #elif filename.endswith('.summary')
        #    return ZipNumCDXSource(filename)
        #elif filename.startswith('redis://')
        #    return RedisCDXSource(filename)

    def load_cdx(self, **params):
        # if key not set, assume 'url' is set and needs canonicalization
        if not params.get('key'):
            params['key'] = self._canonicalize(params)

        self._convert_old_style(params)

        return cdx_load(self.sources, params)

    def _canonicalize(self, params):
        """
        Canonicalize url and convert to surt
        If no surt-mode, convert back to url form
        as surt conversion is currently part of canonicalization
        """
        try:
            url = params['url']
        except KeyError:
            msg = 'A url= param must be specified to query the cdx server'
            raise CDXException(msg)

        try:
            key = surt.surt(url)
        except Exception as e:
            raise CDXException('Invalid Url: ' + url)

        # if not surt, unsurt the surt to get canonicalized non-surt url
        if not self.surt_ordered:
            key = unsurt(key)

        return key

    def _convert_old_style(self, params):
        """
        Convert old-style CDX Server param semantics
        """
        collapse_time = params.get('collapseTime')
        if collapse_time:
            params['collapse_time'] = collapse_time

        resolve_revisits = params.get('resolveRevisits')
        if resolve_revisits:
            params['resolve_revisits'] = resolve_revisits

        if params.get('sort') == 'reverse':
            params['reverse'] = True

    def load_cdx_from_request(self, env):
        #url = wbrequest.wb_url.url

        # use url= param to get actual url
        params = urlparse.parse_qs(env['QUERY_STRING'])

        if not 'output' in params:
            params['output'] = 'text'

        # parse_qs produces arrays for single values
        # cdx processing expects singleton params for all params,
        # except filters, so convert here
        # use first value of the list
        for name, val in params.iteritems():
            if name != 'filter':
                params[name] = val[0]

        cdx_lines = self.load_cdx(**params)
        return cdx_lines

    def __str__(self):
        return 'load cdx indexes from ' + str(self.sources)


#=================================================================
def unsurt(surt):
    """
    # Simple surt
    >>> unsurt('com,example)/')
    'example.com)/'

    # Broken surt
    >>> unsurt('com,example)')
    'com,example)'

    # Long surt
    >>> unsurt('suffix,domain,sub,subsub,another,subdomain)/path/file/\
index.html?a=b?c=)/')
    'subdomain.another.subsub.sub.domain.suffix)/path/file/index.html?a=b?c=)/'
    """

    try:
        index = surt.index(')/')
        parts = surt[0:index].split(',')
        parts.reverse()
        host = '.'.join(parts)
        host += surt[index:]
        return host

    except ValueError:
        # May not be a valid surt
        return surt


if __name__ == "__main__":
    import doctest
    doctest.testmod()
