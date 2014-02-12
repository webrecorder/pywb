import surt
from ..binsearch.binsearch import iter_exact, iter_prefix, FileReader
from cdxops import cdx_load

import itertools
import logging
import os
import urlparse


#=================================================================
class CDXFile:
    def __init__(self, filename):
        self.filename = filename

    def load_cdx(self, params):
        source = FileReader(self.filename)

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
class CDXException(Exception):
    def __init__(self, msg, url = None):
        Exception.__init__(self, msg)
        self.url = url

    def status(self):
        return '400 Bad Request'


#=================================================================
class CDXServer:
    """
    Top-level cdx server object which maintains a list of cdx sources,
    responds to queries and dispatches to the cdx ops for processing
    """

    def __init__(self, sources, surt_ordered = True):
        self.sources = []
        self.surt_ordered = surt_ordered
        logging.debug('CDX Surt-Ordered? ' + str(surt_ordered))

        for src in sources:
            if os.path.isdir(src):
                for file in os.listdir(src):
                    self.add_cdx_loader(src + file)
            else:
                self.add_cdx_loader(src)

        if len(self.sources) == 0:
            logging.exception('No CDX Sources Found!')

    def add_cdx_loader(self, filename):
        source = self.create_cdx_loader(filename)
        if not source:
            return

        logging.debug('Adding CDX Source: ' + str(source))
        self.sources.append(source)

    @staticmethod
    def create_cdx_loader(filename):
        if filename.endswith('.cdx'):
            return CDXFile(filename)
        return None
        #TODO: support zipnum
        #elif filename.endswith('.summary')
        #    return ZipNumCDXSource(filename)
        #elif filename.startswith('redis://')
        #    return RedisCDXSource(filename)


    def load_cdx(self, **params):
        # canonicalize to surt (canonicalization is part of surt conversion)
        try:
            url = params['url']
        except KeyError:
            raise CDXException('The url= param must be specified to query the cdx server')

        try:
            key = surt.surt(url)
        except Exception as e:
            raise CDXException('Invalid url: ', url)

        # if not surt, unsurt the surt to get canonicalized non-surt url
        if not self.surt_ordered:
            key = unsurt(key)

        params['key'] = key

        return cdx_load(self.sources, params)


    def load_cdx_from_request(self, env):
        #url = wbrequest.wb_url.url

        # use url= param to get actual url
        params = urlparse.parse_qs(env['QUERY_STRING'])

        if not 'output' in params:
            params['output'] = 'text'

        # parse_qs produces arrays for single values
        # cdxreader expects singleton params for all except filters, so convert here
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
    >>> unsurt('suffix,domain,sub,subsub,another,subdomain)/path/file/index.html?a=b?c=)/')
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


