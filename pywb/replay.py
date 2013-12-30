import StringIO

import indexreader
from wbrequestresponse import WbResponse
from wbarchivalurl import ArchivalUrl
import utils
from wburlrewriter import ArchivalUrlRewriter

import wbhtml
import regexmatch
import wbexceptions

#=================================================================
class FullHandler:
    def __init__(self, query, replay):
        self.query = query
        self.replay = replay

    def __call__(self, wbrequest, _):
        query_response = self.query(wbrequest, None)

        if (wbrequest.wb_url.type == ArchivalUrl.QUERY) or (wbrequest.wb_url.type == ArchivalUrl.URL_QUERY):
            return query_response

        return self.replay(wbrequest, query_response)


#=================================================================
class ReplayHandler(object):
    def __init__(self, resolvers, archiveloader):
        self.resolvers = resolvers
        self.archiveloader = archiveloader

    def __call__(self, wbrequest, query_response):
        cdxlist = query_response.body
        last_e = None
        first = True

        for cdx in cdxlist:
            try:
                cdx = indexreader.CDXCaptureResult(cdx)

                # ability to intercept and redirect
                if first:
                    self._checkRedir(wbrequest, cdx)
                    first = False

                response = self.doReplay(cdx, wbrequest)

                if response:
                    response.cdx = cdx
                    return response

            #except wbexceptions.InternalRedirect as ir:
            #    raise ir

            except wbexceptions.CaptureException as ce:
                import traceback
                traceback.print_exc()
                last_e = ce
                pass

        if last_e:
            raise last_e
        else:
            raise wbexceptions.ArchiveLoadFailed()

    def _checkRedir(self, wbrequest, cdx):
        return None

    def _load(self, cdx, revisit = False):
        if revisit:
            return self.archiveloader.load(self.resolveFull(cdx['orig.filename']), cdx['orig.offset'], cdx['orig.length'])
        else:
            return self.archiveloader.load(self.resolveFull(cdx['filename']), cdx['offset'], cdx['length'])


    def doReplay(self, cdx, wbrequest):
        hasCurr = (cdx['filename'] != '-')
        hasOrig = (cdx['orig.filename'] != '-')

        # Case 1: non-revisit
        if (hasCurr and not hasOrig):
            headersRecord = self._load(cdx, False)
            payloadRecord = headersRecord
            isRevisit = False

        # Case 2: old-style revisit, load headers from original payload
        elif (not hasCurr and hasOrig):
            payloadRecord = self._load(cdx, False)
            headersRecord = payloadRecord
            isRevisit = True

        # Case 3: modern revisit, load headers from curr, payload from original
        elif (hasCurr and hasOrig):
            headersRecord = self._load(cdx, False)
            payloadRecord = self._load(cdx, True)

            # Case 4: if headers record is actually empty (eg empty revisit), then use headers from revisit
            if not headersRecord.httpHeaders:
                headersRecord.close()
                headersRecord = payloadRecord

            isRevisit = True

        else:
            raise wbexceptions.CaptureException('Invalid CDX' + cdx)

        return WbResponse.stream_response(headersRecord.statusline, headersRecord.httpHeaders, payloadRecord.stream)


    def resolveFull(self, filename):
        # Attempt to resolve cdx file to full path
        fullUrl = None
        for resolver in self.resolvers:
            fullUrl = resolver(filename)
            if fullUrl:
                return fullUrl

        raise wbexceptions.UnresolvedArchiveFileException('Archive File Not Found: ' + filename)


#=================================================================
class RewritingReplayHandler(ReplayHandler):


    REWRITE_TYPES = {
        'html': ['text/html', 'application/xhtml'],
        'css':  ['text/css'],
        'js':   ['text/javascript', 'application/javascript', 'application/x-javascript'],
        'xml':  ['/xml', '+xml', '.xml', '.rss'],
    }


    PROXY_HEADERS = ('content-type', 'content-disposition')

    URL_REWRITE_HEADERS = ('location', 'content-location', 'content-base')

    ENCODING_HEADERS = ('content-encoding', 'transfer-encoding')


    def __init__(self, resolvers, archiveloader, headerPrefix = 'X-Archive-Orig-', headInsert = None):
        ReplayHandler.__init__(self, resolvers, archiveloader)
        self.headerPrefix = headerPrefix
        self.headInsert = headInsert


    def _textContentType(self, contentType):
        for ctype, mimelist in self.REWRITE_TYPES.iteritems():
            if any ((mime in contentType) for mime in mimelist):
                return ctype

        return None


    def __call__(self, wbrequest, query_response):
        urlrewriter = ArchivalUrlRewriter(wbrequest.wb_url, wbrequest.wb_prefix)
        wbrequest.urlrewriter = urlrewriter

        response = ReplayHandler.__call__(self, wbrequest, query_response)

        if response and response.cdx:
            self._checkRedir(wbrequest, response.cdx)

        # Transparent!
        if wbrequest.wb_url.mod == 'id_':
            return response

        contentType = utils.get_header(response.headersList, 'Content-Type')
        
        textType = self._textContentType(contentType) if contentType else None
        
        (newHeaders, remHeaders) = self._rewriteHeaders(response.headersList, urlrewriter, textType is not None)

        # binary type, just send through
        if textType is None:
            response.headersList = newHeaders
            return response

        # Handle text rewriting
        # TODO: better way to pass this
        stream = response._stream

        # special case -- need to ungzip the body
        if (utils.contains_header(remHeaders, ('Content-Encoding', 'gzip'))):
            stream = archiveloader.LineStream(stream, decomp = zlib.decompressobj(16 + zlib.MAX_WBITS))

        return self._rewriteContent(textType, urlrewriter, stream, newHeaders, response)

    # TODO: first non-streaming attempt, probably want to stream
    def _rewriteContent(self, textType, urlrewriter, stream, newHeaders, origResponse, encoding = 'utf-8'):
        if textType == 'html':
            out = StringIO.StringIO()
            htmlrewriter = wbhtml.WBHtml(urlrewriter, out, self.headInsert)

            try:
                buff = stream.read()#.decode(encoding)
                while buff:
                    htmlrewriter.feed(buff)
                    buff = stream.read()#.decode(encoding)

                htmlrewriter.close()

            #except Exception as e:
            #    print e

            finally:
                value = [out.getvalue()]
                newHeaders.append(('Content-Length', str(len(value[0]))))
                out.close()

        else:
            if textType == 'css':
                rewriter = regexmatch.CSSRewriter(urlrewriter)
            elif textType == 'js':
                rewriter = regexmatch.JSRewriter(urlrewriter)

            def gen():
                try:
                    buff = stream.read()
                    while buff:
                        yield rewriter.replaceAll(buff)
                        buff = stream.read()

                finally:
                    stream.close()

            value = gen()

        return WbResponse(status = origResponse.status, headersList = newHeaders, value = value)



    def _rewriteHeaders(self, headers, urlrewriter, stripEncoding = False):
        newHeaders = []
        removedHeaders = []

        for (name, value) in headers:
            lowername = name.lower()
            if lowername in self.PROXY_HEADERS:
                newHeaders.append((name, value))
            elif lowername in self.URL_REWRITE_HEADERS:
                newHeaders.append((name, urlrewriter.rewrite(value)))
            elif lowername in self.ENCODING_HEADERS:
                if stripEncoding:
                    removedHeaders.append((name, value))
                else:
                    newHeaders.append((name, value))
            else:
                newHeaders.append((self.headerPrefix + name, value))

        return (newHeaders, removedHeaders)


    def _checkRedir(self, wbrequest, cdx):
        if cdx and (cdx['timestamp'] != wbrequest.wb_url.timestamp):
            newUrl = wbrequest.urlrewriter.getTimestampUrl(cdx['timestamp'], cdx['original'])
            raise wbexceptions.InternalRedirect(newUrl)
            #return WbResponse.better_timestamp_response(wbrequest, cdx['timestamp'])

        return None


    def doReplay(self, cdx, wbrequest):
        wbresponse = ReplayHandler.doReplay(self, cdx, wbrequest)

        # Check for self redirect
        if wbresponse.status.startswith('3'):
            if self.isSelfRedirect(wbrequest, wbresponse.headersList):
                raise wbexceptions.CaptureException('Self Redirect: ' + str(cdx))

        return wbresponse

    def isSelfRedirect(self, wbrequest, httpHeaders):
        requestUrl = wbrequest.wb_url.url.lower()
        locationUrl = utils.get_header(httpHeaders, 'Location').lower()
        #return requestUrl == locationUrl
        return (ArchivalUrlRewriter.stripProtocol(requestUrl) == ArchivalUrlRewriter.stripProtocol(locationUrl))


#======================================
# PrefixResolver - convert cdx file entry to url with prefix if url contains specified string
#======================================
def PrefixResolver(prefix, contains):
    def makeUrl(url):
        return prefix + url if (contains in url) else None

    return makeUrl
