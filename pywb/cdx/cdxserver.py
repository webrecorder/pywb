from canonicalize import UrlCanonicalizer, calc_search_range

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
        ds_rules = kwargs.get('ds_rules')
        surt_ordered = kwargs.get('surt_ordered', True)

        # load from domain-specific rules
        if ds_rules:
            self.url_canon, self.fuzzy_query = (
                load_domain_specific_cdx_rules(ds_rules, surt_ordered))
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

        if self.fuzzy_query and params.get('allowFuzzy'):
            if not 'key' in params:
                params['key'] = self.url_canon(url)

            params = self.fuzzy_query(params)
            if params:
                params['allowFuzzy'] = False
                return self.load_cdx(**params)

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
        # TODO: we could save config in member, so that other
        # methods can use it. it's bad for add_cdx_source to take
        # config argument.
        self._create_cdx_sources(paths, kwargs.get('config'))

    def load_cdx(self, **params):
        # if key not set, assume 'url' is set and needs canonicalization
        if not params.get('key'):
            try:
                url = params['url']
            except KeyError:
                msg = 'A url= param must be specified to query the cdx server'
                raise CDXException(msg)

            #params['key'] = self.url_canon(url)
            match_type = params.get('matchType', 'exact')

            key, end_key = calc_search_range(url=url,
                                             match_type=match_type,
                                             url_canon=self.url_canon)
            params['key'] = key
            params['end_key'] = end_key

        cdx_iter = cdx_load(self.sources, params, self.perms_checker)
        return self._check_cdx_iter(cdx_iter, params)

    def _create_cdx_sources(self, paths, config):
        """
        build CDXSource instances for each of path in :param paths:.
        :param paths: list of sources or single source.
        each source may be either string or CDXSource instance. value
        of any other types will be silently ignored.
        :param config: config object passed to :method:`add_cdx_source`.
        """
        self.sources = []

        if paths is not None:
            if not isinstance(paths, (list, tuple)):
                paths = [paths]

            for path in paths:
                self.add_cdx_source(path, config)

        if len(self.sources) == 0:
            logging.warn('No CDX Sources configured from paths=%s', paths)

    def _add_cdx_source(self, source):
        if source is None: return
        logging.debug('Adding CDX Source: %s', source)
        self.sources.append(source)

    def add_cdx_source(self, source, config):
        if source is None: return
        if isinstance(source, CDXSource):
            self._add_cdx_source(source)
        elif isinstance(source, str):
            if os.path.isdir(source):
                for fn in os.listdir(source):
                    self._add_cdx_source(self._create_cdx_source(
                            os.path.join(source, fn), config))
            else:
                self._add_cdx_source(self._create_cdx_source(
                        source, config))

    def _create_cdx_source(self, filename, config):
        if is_http(filename):
            return RemoteCDXSource(filename)

        if filename.startswith('redis://'):
            return RedisCDXSource(filename, config)

        if filename.endswith('.cdx'):
            return CDXFile(filename)

        if filename.endswith('.summary'):
            return ZipNumCluster(filename, config)

        logging.warn('skipping unrecognized URI:%s', filename)
        return None

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
        remote_iter = cdx_load((self.sources,), params, filter=False)
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
                      ds_rules=ds_rules_file,
                      perms_checker=perms_checker)

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
