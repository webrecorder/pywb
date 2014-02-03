import urllib
import urllib2
import wbexceptions
import itertools
import wbrequestresponse
import surt
from collections import OrderedDict

import binsearch
import cdxserve
import logging
import os

#=================================================================
class IndexReader:
    def load_for_request(self, wbrequest, parsed_cdx = True):
        wburl = wbrequest.wb_url

        # init standard params
        params = self.get_query_params(wburl)

        # add any custom filter from the request
        if wbrequest.query_filter:
            params['filter'] = wbrequest.query_filter

        if wbrequest.custom_params:
            params.update(wbrequest.custom_params)

        cdxlines = self.load_cdx(wburl.url, params, parsed_cdx)

        cdxlines = utils.peek_iter(cdxlines)

        if cdxlines is None:
            raise wbexceptions.NotFoundException('WB Does Not Have Url: ' + wburl.url)

        cdxlines = self.filter_cdx(wbrequest, cdxlines)

        return cdxlines

    def filter_cdx(self, wbrequest, cdxlines):
        # Subclasses may wrap cdxlines iterator in a filter
        return cdxlines

    def load_cdx(self, url, params = {}, parsed_cdx = True):
        raise NotImplementedError('Override in subclasses')

    @staticmethod
    def make_best_cdx_source(paths, **config):
        # may be a string or list
        surt_ordered = config.get('surt_ordered', True)

        # support mixed cdx streams and remote servers?
        # for now, list implies local sources
        if isinstance(paths, list):
            if len(paths) > 1:
                return LocalCDXServer(paths, surt_ordered)
            else:
                # treat as non-list
                paths = paths[0]

        # a single uri
        uri = paths

        # Check for remote cdx server
        if (uri.startswith('http://') or uri.startswith('https://')) and not uri.endswith('.cdx'):
            cookie = config.get('cookie', None)
            return RemoteCDXServer(uri, cookie = cookie)
        else:
            return LocalCDXServer([uri], surt_ordered)




#=================================================================
class LocalCDXServer(IndexReader):
    """
    >>> x = LocalCDXServer([test_dir]).load_cdx('example.com', parsed_cdx = True, limit = 1)
    >>> pprint(x.next().items())
    [('urlkey', 'com,example)/'),
     ('timestamp', '20140127171200'),
     ('original', 'http://example.com'),
     ('mimetype', 'text/html'),
     ('statuscode', '200'),
     ('digest', 'B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A'),
     ('redirect', '-'),
     ('robotflags', '-'),
     ('length', '1046'),
     ('offset', '334'),
     ('filename', 'dupes.warc.gz')]

    """

    def __init__(self, sources, surt_ordered = True):
        self.sources = []
        self.surt_ordered = surt_ordered
        logging.info('CDX Surt-Ordered? ' + str(surt_ordered))

        for src in sources:
            if os.path.isdir(src):
                for file in os.listdir(src):
                    if file.endswith('.cdx'):
                        full = src + file
                        logging.info('Adding CDX: ' + full)
                        self.sources.append(full)
            else:
                logging.info('Adding CDX: ' + src)
                self.sources.append(src)


    def load_cdx(self, url, params = {}, parsed_cdx = True, **kwvalues):
        # canonicalize to surt (canonicalization is part of surt conversion)
        try:
            key = surt.surt(url)
        except Exception as e:
            raise wbexceptions.BadUrlException('Bad Request Url: ' + url)

        # if not surt, unsurt the surt to get canonicalized non-surt url
        if not self.surt_ordered:
            key = utils.unsurt(key)

        match_func = binsearch.iter_exact

        params.update(**kwvalues)
        params['output'] = 'raw' if parsed_cdx else 'text'

        return cdxserve.cdx_serve(key, params, self.sources, match_func)


    def get_query_params(self, wburl, limit = 150000, collapse_time = None, replay_closest = 10):

        if wburl.type == wburl.URL_QUERY:
            raise NotImplementedError('Url Query Not Yet Supported')

        return {

            wburl.QUERY:
                {'collapse_time': collapse_time, 'filter': '!statuscode:(500|502|504)', 'limit': limit},

            wburl.URL_QUERY:
                {},
#                raise Exception('Not Yet Implemented')
#                {'collapse': 'urlkey', 'matchType': 'prefix', 'showGroupCount': True, 'showUniqCount': True, 'lastSkipTimestamp': True, 'limit': limit,
#                 'fl': 'urlkey,original,timestamp,endtimestamp,groupcount,uniqcount',
#                },

            wburl.REPLAY:
                {'filter': '!statuscode:(500|502|504)', 'limit': replay_closest, 'closest_to': wburl.timestamp, 'resolve_revisits': True},

           wburl.LATEST_REPLAY:
                {'reverse': True, 'filter': 'statuscode:[23]..', 'limit': '1', 'resolve_revisits': True}

        }[wburl.type]


    def __str__(self):
        return 'load cdx indexes from ' + str(self.sources)



#=================================================================
class RemoteCDXServer(IndexReader):
    """
    >>> x = RemoteCDXServer('http://web.archive.org/cdx/search/cdx').load_cdx('example.com', parsed_cdx = True, limit = '2')
    >>> pprint(x.next().items())
    [('urlkey', 'com,example)/'),
     ('timestamp', '20020120142510'),
     ('original', 'http://example.com:80/'),
     ('mimetype', 'text/html'),
     ('statuscode', '200'),
     ('digest', 'HT2DYGA5UKZCPBSFVCV3JOBXGW2G5UUA'),
     ('length', '1792')]
    """

    def __init__(self, server_url, cookie = None):
        self.server_url = server_url
        self.auth_cookie = cookie

    def load_cdx(self, url, params = {}, parsed_cdx = True, **kwvalues):
        #url is required, must be passed explicitly!
        params['url'] = url
        params.update(**kwvalues)

        urlparams = urllib.urlencode(params, True)

        try:
            request = urllib2.Request(self.server_url, urlparams)

            if self.auth_cookie:
                request.add_header('Cookie', self.auth_cookie)

            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            if e.code == 403:
                exc_msg = e.read()
                msg = 'Blocked By Robots' if 'Blocked By Robots' in exc_msg else 'Excluded'
                raise wbexceptions.AccessException(msg)
            else:
                raise e

        if parsed_cdx:
            return (CDXCaptureResult(cdx) for cdx in response)
        else:
            return iter(response)


    # Note: this params are designed to make pywb compatible with the original Java wayback-cdx-server API:
    # https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    # Soon, this will be switched over to support the native pywb cdx server

    # BUG: Setting replayClosest to high number for now, as cdx server sometimes returns wrong result
    # with lower values if there are too many captures. Ideally, should be around 10-20
    # The replayClosest is the max number of cdx lines, so max number of retry attempts that WB will make

    def get_query_params(self, wburl, limit = '150000', collapse_time = '10', replay_closest = '4000'):
        return {

            wburl.QUERY:
                {'collapseTime': collapse_time, 'filter': '!statuscode:(500|502|504)', 'limit': limit},

            wburl.URL_QUERY:
                {'collapse': 'urlkey', 'matchType': 'prefix', 'showGroupCount': True, 'showUniqCount': True, 'lastSkipTimestamp': True, 'limit': limit,
                 'fl': 'urlkey,original,timestamp,endtimestamp,groupcount,uniqcount',
                },

            wburl.REPLAY:
                {'sort': 'closest', 'filter': '!statuscode:(500|502|504)', 'limit': replay_closest, 'closest': wburl.timestamp, 'resolveRevisits': True},

            # BUG: resolveRevisits currently doesn't work for this type of query
            # This is not an issue in archival mode, as there is a redirect to the actual timestamp query
            # but may be an issue in proxy mode
            wburl.LATEST_REPLAY:
                {'sort': 'reverse', 'filter': 'statuscode:[23]..', 'limit': '1', 'resolveRevisits': True}

        }[wburl.type]


    def __str__(self):
        return 'server cdx from ' + self.server_url


#=================================================================
class CDXCaptureResult(OrderedDict):
    CDX_FORMATS = [
        # Public CDX Format
        ["urlkey","timestamp","original","mimetype","statuscode","digest","length"],

        # CDX 11 Format
        ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","robotflags","length","offset","filename"],

        # CDX 9 Format
        ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","offset","filename"],

        # CDX 11 Format + 3 revisit resolve fields
        ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","robotflags","length","offset","filename",
         "orig.length","orig.offset","orig.filename"],

        # CDX 9 Format + 3 revisit resolve fields
        ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","offset","filename",
         "orig.length","orig.offset","orig.filename"]
        ]

    def __init__(self, cdxline):
        OrderedDict.__init__(self)

        cdxline = cdxline.rstrip()
        fields = cdxline.split(' ')

        cdxformat = None
        for i in CDXCaptureResult.CDX_FORMATS:
            if len(i) == len(fields):
                cdxformat = i

        if not cdxformat:
            raise wbexceptions.InvalidCDXException('unknown {0}-field cdx format'.format(len(fields)))

        for header, field in itertools.izip(cdxformat, fields):
            self[header] = field

        self.cdxline = cdxline

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)

        # force regen on next __str__ call
        self.cdxline = None


    def __str__(self):
        if self.cdxline:
            return self.cdxline

        li = itertools.imap(lambda (n, val): val, self.items())
        return ' '.join(li)



# Testing

import utils
if __name__ == "__main__" or utils.enable_doctests():
    from pprint import pprint

    test_dir = utils.test_data_dir() + 'cdx/'

    import doctest
    doctest.testmod()
