import surt
from cdxops import cdx_load

import itertools
import logging
import os
import urlparse

from cdxsource import CDXSource, CDXFile, RemoteCDXSource
from cdxobject import CDXObject


#=================================================================
class CDXException(Exception):
    def status(self):
        return '400 Bad Request'


#=================================================================
class AccessException(CDXException):
    def status(self):
        return '403 Bad Request'


#=================================================================
class CDXServer(object):
    """
    Top-level cdx server object which maintains a list of cdx sources,
    responds to queries and dispatches to the cdx ops for processing
    """

    def __init__(self, paths, surt_ordered=True):
        self.sources = create_cdx_sources(paths)
        self.surt_ordered = surt_ordered

    def load_cdx(self, **params):
        # if key not set, assume 'url' is set and needs canonicalization
        if not params.get('key'):
            params['key'] = self._canonicalize(params)

        convert_old_style_params(params)

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

    def __str__(self):
        return 'CDX server serving from ' + str(self.sources)


#=================================================================
class RemoteCDXServer(object):
    """
    A special cdx server that uses a single RemoteCDXSource
    It simply proxies the query params to the remote source
    and performs no local processing/filtering
    """
    def __init__(self, source):
        if isinstance(source, RemoteCDXSource):
            self.source = source
        elif (isinstance(source, str) and
              any(source.startswith(x) for x in ['http://', 'https://'])):
            self.source = RemoteCDXSource(source)
        else:
            raise Exception('Invalid remote cdx source: ' + str(source))

    def load_cdx(self, **params):
        remote_iter = remote.load_cdx(**params)
        # if need raw, convert to raw format here
        if params.get('output') == 'raw':
            return (CDXObject(cdx) for cdx in remote_iter)
        else:
            return remote_iter

    def __str__(self):
        return 'Remote CDX server serving from ' + str(self.sources[0])


#=================================================================
def create_cdx_server(config):
    if hasattr(config, 'get'):
        paths = config.get('index_paths')
        surt_ordered = config.get('surt_ordered', True)
    else:
        paths = config
        surt_ordered = True

    logging.debug('CDX Surt-Ordered? ' + str(surt_ordered))

    if (isinstance(paths, str) and
        any(paths.startswith(x) for x in ['http://', 'https://'])):
        return RemoteCDXServer(paths)
    else:
        return CDXServer(paths)


#=================================================================
def create_cdx_sources(paths):
    sources = []

    if not isinstance(paths, list):
        paths = [paths]

    for path in paths:
        if isinstance(path, CDXSource):
            add_cdx_source(sources, path)
        elif isinstance(path, str):
            if os.path.isdir(path):
                for file in os.listdir(path):
                    add_cdx_source(sources, path + file)
            else:
                add_cdx_source(sources, path)

    if len(sources) == 0:
        logging.exception('No CDX Sources Found from: ' + str(sources))

    return sources


#=================================================================
def add_cdx_source(sources, source):
    if not isinstance(source, CDXSource):
        source = create_cdx_source(source)
        if not source:
            return

    logging.debug('Adding CDX Source: ' + str(source))
    sources.append(source)


#=================================================================
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


#=================================================================
def convert_old_style_params(params):
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

    return params


#=================================================================
def extract_params_from_wsgi_env(env):
    """ utility function to extract params from the query
    string of a WSGI environment dictionary
    """
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

    return params


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
