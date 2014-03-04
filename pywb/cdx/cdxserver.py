from pywb.utils.canonicalize import UrlCanonicalizer, calc_search_range

from cdxops import cdx_load
from cdxsource import CDXSource, CDXFile, RemoteCDXSource, RedisCDXSource
from zipnum import ZipNumCluster
from cdxobject import CDXObject, CaptureNotFoundException, CDXException
from query import CDXQuery
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
        #self.perms_checker = kwargs.get('perms_checker')

    def _check_cdx_iter(self, cdx_iter, query):
        """ Check cdx iter semantics
        If `cdx_iter` is empty (no matches), check if fuzzy matching
        is allowed, and try it -- otherwise,
        throw :exc:`~pywb.cdx.cdxobject.CaptureNotFoundException`
        """

        cdx_iter = self.peek_iter(cdx_iter)

        if cdx_iter:
            return cdx_iter

        # check if fuzzy is allowed and ensure that its an
        # exact match
        if (self.fuzzy_query and
            query.allow_fuzzy and
            query.is_exact):

            fuzzy_query_params = self.fuzzy_query(query)
            if fuzzy_query_params:
                return self.load_cdx_query(fuzzy_query_params)

        msg = 'No Captures found for: ' + query.url
        raise CaptureNotFoundException(msg)

    def load_cdx(self, **params):
        return self.load_cdx_query(CDXQuery(**params))

    def load_cdx_query(self, query):
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

    def load_cdx_query(self, query):
        """
        load CDX for query parameters ``params``.
        ``key`` (or ``url``) parameter specifies URL to query,
        ``matchType`` parameter specifies matching method for ``key``
        (default ``exact``).
        other parameters are passed down to :func:`cdx_load`.
        raises :exc:`~pywb.cdx.cdxobject.CaptureNotFoundException`
        if no captures are found.

        :param query: query parameters
        :type query: :class:`~pywb.cdx.query.CDXQuery`
        :rtype: iterator on :class:`~pywb.cdx.cdxobject.CDXObject`
        """
        url = query.url
        key, end_key = calc_search_range(url=url,
                                         match_type=query.match_type,
                                         url_canon=self.url_canon)
        query.set_key(key, end_key)

        cdx_iter = cdx_load(self.sources,
                            query)
                            #perms_checker=self.perms_checker)

        return self._check_cdx_iter(cdx_iter, query)

    def _create_cdx_sources(self, paths, config):
        """
        build CDXSource instances for each of path in ``paths``.

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
        if source is None:
            return

        logging.debug('Adding CDX Source: %s', source)
        self.sources.append(source)

    def add_cdx_source(self, source, config):
        if source is None:
            return

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

        if filename.endswith(('.summary', '.idx')):
            return ZipNumCluster(filename, config)

        logging.warn('skipping unrecognized URI:%s', filename)
        return None

    def __str__(self):
        return 'CDX server serving from ' + str(self.sources)


#=================================================================
class RemoteCDXServer(BaseCDXServer):
    """
    A special cdx server that uses a single
    :class:`~pywb.cdx.cdxsource.RemoteCDXSource`.
    It simply proxies the query params to the remote source
    and performs no local processing/filtering
    """
    def __init__(self, source, **kwargs):
        super(RemoteCDXServer, self).__init__(**kwargs)

        if isinstance(source, RemoteCDXSource):
            self.source = source
        elif (isinstance(source, str) and is_http(source)):
            self.source = RemoteCDXSource(source, remote_processing=True)
        else:
            raise Exception('Invalid remote cdx source: ' + str(source))

    def load_cdx_query(self, query):
        remote_iter = cdx_load([self.source], query, process=False)
        return self._check_cdx_iter(remote_iter, query)

    def __str__(self):
        return 'Remote CDX server serving from ' + str(self.sources[0])


#=================================================================
def create_cdx_server(config, ds_rules_file=None):
    if hasattr(config, 'get'):
        paths = config.get('index_paths')
        surt_ordered = config.get('surt_ordered', True)
        pass_config = config
    else:
        paths = config
        surt_ordered = True
        pass_config = None

    logging.debug('CDX Surt-Ordered? ' + str(surt_ordered))

    if isinstance(paths, str) and is_http(paths):
        server_cls = RemoteCDXServer
    else:
        server_cls = CDXServer

    return server_cls(paths,
                      config=pass_config,
                      surt_ordered=surt_ordered,
                      ds_rules_file=ds_rules_file)
