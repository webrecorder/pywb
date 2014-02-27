from pywb.utils.canonicalize import UrlCanonicalizer, calc_search_range

from cdxops import cdx_load
from cdxsource import CDXSource, CDXFile, RemoteCDXSource, RedisCDXSource
from zipnum import ZipNumCluster
from cdxobject import CDXObject, CaptureNotFoundException, CDXException
from cdxdomainspecific import load_domain_specific_cdx_rules

from pywb.utils.loaders import is_http

from itertools import chain
import logging
import os
import urlparse


#=================================================================
class BaseCDXServer(object):
    def __init__(self, **kwargs):
        ds_rules_file = kwargs.get('ds_rules_file')
        surt_ordered = kwargs.get('surt_ordered', True)

        # load from domain-specific rules
        if ds_rules_file:
            self.url_canon, self.fuzzy_query = (
                load_domain_specific_cdx_rules(ds_rules_file, surt_ordered))
        # or custom passed in canonicalizer
        else:
            self.url_canon = kwargs.get('url_canon')
            self.fuzzy_query = kwargs.get('fuzzy_query')

        # set default canonicalizer if none set thus far
        if not self.url_canon:
            self.url_canon = UrlCanonicalizer(surt_ordered)

        # set perms checker, if any
        self.perms_checker = kwargs.get('perms_checker')

    def _check_cdx_iter(self, cdx_iter, params):
        """ Check cdx iter semantics
        If iter is empty (no matches), check if fuzzy matching
        is allowed, and try it -- otherwise,
        throw CaptureNotFoundException
        """

        cdx_iter = self.peek_iter(cdx_iter)

        if cdx_iter:
            return cdx_iter

        url = params['url']

        # check if fuzzy is allowed and ensure that its an
        # exact match
        if (self.fuzzy_query and params.get('allowFuzzy') and
            params.get('matchType', 'exact') == 'exact'):

            fuzzy_params = self.fuzzy_query(params)
            if fuzzy_params:
                return self.load_cdx(**fuzzy_params)

        msg = 'No Captures found for: ' + url
        raise CaptureNotFoundException(msg)

    def load_cdx(self, **params):
        raise NotImplementedError('Implement in subclass')

    @staticmethod
    def peek_iter(iterable):
        try:
            first = next(iterable)
        except StopIteration:
            return None

        return chain([first], iterable)


#=================================================================
class CDXServer(BaseCDXServer):
    """
    Top-level cdx server object which maintains a list of cdx sources,
    responds to queries and dispatches to the cdx ops for processing
    """

    def __init__(self, paths, **kwargs):
        super(CDXServer, self).__init__(**kwargs)
        self.sources = create_cdx_sources(paths, kwargs.get('config'))

    def load_cdx(self, **params):
        # if key not set, assume 'url' is set and needs canonicalization
        if not params.get('key'):
            try:
                url = params['url']
            except KeyError:
                msg = 'A url= param must be specified to query the cdx server'
                raise CDXException(msg)

            match_type = params.get('matchType', 'exact')

            key, end_key = calc_search_range(url=url,
                                             match_type=match_type,
                                             url_canon=self.url_canon)
            params['key'] = key
            params['end_key'] = end_key

        cdx_iter = cdx_load(self.sources, params, self.perms_checker)

        return self._check_cdx_iter(cdx_iter, params)

    def __str__(self):
        return 'CDX server serving from ' + str(self.sources)


#=================================================================
class RemoteCDXServer(BaseCDXServer):
    """
    A special cdx server that uses a single RemoteCDXSource
    It simply proxies the query params to the remote source
    and performs no local processing/filtering
    """
    def __init__(self, source, **kwargs):
        super(RemoteCDXServer, self).__init__(**kwargs)

        if isinstance(source, RemoteCDXSource):
            self.source = source
        elif (isinstance(source, str) and
              any(source.startswith(x) for x in ['http://', 'https://'])):
            self.source = RemoteCDXSource(source)
        else:
            raise Exception('Invalid remote cdx source: ' + str(source))

    def load_cdx(self, **params):
        remote_iter = self.source.load_cdx(params)

        # if need raw, convert to raw format here
        if params.get('output') == 'raw':
            remote_iter = (CDXObject(cdx) for cdx in remote_iter)

        return self._check_cdx_iter(remote_iter, params)

    def __str__(self):
        return 'Remote CDX server serving from ' + str(self.sources[0])


#=================================================================
def create_cdx_server(config, ds_rules_file=None):
    if hasattr(config, 'get'):
        paths = config.get('index_paths')
        surt_ordered = config.get('surt_ordered', True)
        perms_checker = config.get('perms_checker')
        pass_config = config
    else:
        paths = config
        surt_ordered = True
        perms_checker = None
        pass_config = None

    logging.debug('CDX Surt-Ordered? ' + str(surt_ordered))

    if isinstance(paths, str) and is_http(paths):
        server_cls = RemoteCDXServer
    else:
        server_cls = CDXServer

    return server_cls(paths,
                      config=pass_config,
                      surt_ordered=surt_ordered,
                      ds_rules_file=ds_rules_file,
                      perms_checker=perms_checker)


#=================================================================
def create_cdx_sources(paths, config=None):
    sources = []

    if not isinstance(paths, list):
        paths = [paths]

    for path in paths:
        if isinstance(path, CDXSource):
            add_cdx_source(sources, path, config)
        elif isinstance(path, str):
            if os.path.isdir(path):
                for file in os.listdir(path):
                    add_cdx_source(sources, path + file, config)
            else:
                add_cdx_source(sources, path, config)

    if len(sources) == 0:
        logging.exception('No CDX Sources Found from: ' + str(sources))

    return sources


#=================================================================
def add_cdx_source(sources, source, config):
    if not isinstance(source, CDXSource):
        source = create_cdx_source(source, config)
        if not source:
            return

    logging.debug('Adding CDX Source: ' + str(source))
    sources.append(source)


#=================================================================
def create_cdx_source(filename, config):
    if is_http(filename):
        return RemoteCDXSource(filename)

    if filename.startswith('redis://'):
        return RedisCDXSource(filename, config)

    if filename.endswith('.cdx'):
        return CDXFile(filename)

    if filename.endswith('.summary'):
        return ZipNumCluster(filename, config)

    return None


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
