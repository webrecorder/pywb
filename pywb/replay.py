import StringIO
from urllib2 import URLError
import chardet
import redis

import indexreader
from wbrequestresponse import WbResponse, StatusAndHeaders
from wbarchivalurl import ArchivalUrl
import utils

from url_rewriter import ArchivalUrlRewriter
from header_rewriter import HeaderRewriter
import html_rewriter
import regex_rewriters

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

        # List of already failed w/arcs
        failedFiles = []

        # Iterate over the cdx until find one that works
        # The cdx should already be sorted in closest-to-timestamp order (from the cdx server)
        for cdx in cdxlist:
            try:
                cdx = indexreader.CDXCaptureResult(cdx)

                # ability to intercept and redirect
                if first:
                    self._checkRedir(wbrequest, cdx)
                    first = False

                response = self.doReplay(cdx, wbrequest, failedFiles)

                if response:
                    response.cdx = cdx
                    return response

            except wbexceptions.CaptureException as ce:
                import traceback
                traceback.print_exc()
                last_e = ce
                pass

        if last_e:
            raise last_e
        else:
            raise wbexceptions.UnresolvedArchiveFileException()

    def _checkRedir(self, wbrequest, cdx):
        return None

    def _load(self, cdx, revisit, failedFiles):
        if revisit:
            (filename, offset, length) = (cdx['orig.filename'], cdx['orig.offset'], cdx['orig.length'])
        else:
            (filename, offset, length) = (cdx['filename'], cdx['offset'], cdx['length'])

        #optimization: if same file already failed this request, don't try again
        if failedFiles and filename in failedFiles:
            raise wbexceptions.ArchiveLoadFailed(filename, 'Skipping Already Failed')

        try:
            return self.archiveloader.load(self.resolveFull(filename), offset, length)

        except URLError as ue:
            if failedFiles:
                failedFiles.append(filename)

            raise wbexceptions.ArchiveLoadFailed(filename, ue.reason)


    def doReplay(self, cdx, wbrequest, failedFiles):
        hasCurr = (cdx['filename'] != '-')
        hasOrig = (cdx['orig.filename'] != '-')

        # Case 1: non-revisit
        if (hasCurr and not hasOrig):
            headersRecord = self._load(cdx, False, failedFiles)
            payloadRecord = headersRecord
            isRevisit = False

        # Case 2: old-style revisit, load headers from original payload
        elif (not hasCurr and hasOrig):
            payloadRecord = self._load(cdx, False, failedFiles)
            headersRecord = payloadRecord
            isRevisit = True

        # Case 3: modern revisit, load headers from curr, payload from original
        elif (hasCurr and hasOrig):
            headersRecord = self._load(cdx, False, failedFiles)
            payloadRecord = self._load(cdx, True, failedFiles)

            # Case 4: if headers record is actually empty (eg empty revisit), then use headers from revisit
            if not headersRecord.status_headers.headers:
                headersRecord.stream.close()
                headersRecord = payloadRecord
            else:
                headersRecord.stream.close()


            isRevisit = True

        else:
            raise wbexceptions.CaptureException('Invalid CDX' + cdx)

        return WbResponse.stream_response(headersRecord.status_headers, payloadRecord.stream)


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

    def __init__(self, resolvers, archiveloader, headInsert = None, headerRewriter = None):
        ReplayHandler.__init__(self, resolvers, archiveloader)
        self.headInsert = headInsert
        if not headerRewriter:
            headerRewriter = HeaderRewriter()
        self.headerRewriter = headerRewriter


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


        rewrittenHeaders = self.headerRewriter.rewrite(response.status_headers, urlrewriter)

        # non-text content type, just send through with rewritten headers
        if rewrittenHeaders.textType is None:
            response.status_headers = rewrittenHeaders.status_headers
            return response

        # Handle text rewriting
        # TODO: better way to pass this?
        stream = response._stream

        # special case -- need to ungzip the body
        if (rewrittenHeaders.containsRemovedHeader('content-encoding', 'gzip')):
            stream = archiveloader.LineStream(stream, decomp = utils.create_decompressor())

        # TODO: is this right?
        if rewrittenHeaders.charset:
            encoding = rewrittenHeaders.charset
            firstBuff = None
        else:
            (encoding, firstBuff) = self._detectCharset(stream)

            # if chardet thinks its ascii, use utf-8
            if encoding == 'ascii':
                #encoding = None
                encoding = 'utf-8'

        # Buffering response for html, streaming for others?
        if rewrittenHeaders.textType == 'html':
            return self._rewriteHtml(encoding, urlrewriter, stream, rewrittenHeaders.status_headers, firstBuff)
        else:
            return self._rewriteOther(rewrittenHeaders.textType, encoding, urlrewriter, stream, rewrittenHeaders.status_headers, firstBuff)


    def _rewriteHtml(self, encoding, urlrewriter, stream, status_headers, firstBuff = None):
        out = StringIO.StringIO()
        htmlrewriter = html_rewriter.WBHtml(urlrewriter, out, self.headInsert)

        try:
            buff = firstBuff if firstBuff else stream.read()
            while buff:
                if encoding:
                    buff = buff.decode(encoding)
                htmlrewriter.feed(buff)
                buff = stream.read()

            # Close rewriter if gracefully made it to end
            htmlrewriter.close()

        finally:
                content = out.getvalue()
                if encoding:
                    content = content.encode(encoding)

                value = [content]
                contentLengthStr = str(len(content))
                status_headers.headers.append(('Content-Length', contentLengthStr))
                out.close()

        return WbResponse(status_headers, value = value)


    def _rewriteOther(self, textType, encoding, urlrewriter, stream, status_headers, firstBuff = None):
        if textType == 'css':
            rewriter = regex_rewriters.CSSRewriter(urlrewriter)
        elif textType == 'js':
            rewriter = regex_rewriters.JSRewriter(urlrewriter)
        elif textType == 'xml':
            rewriter = regex_rewriters.XMLRewriter(urlrewriter)


        def doRewrite(buff):
            if encoding:
                buff = buff.decode(encoding)
            buff = rewriter.replaceAll(buff)
            if encoding:
                buff = buff.encode(encoding)

            return buff

        return WbResponse.stream_response(status_headers, stream, doRewrite, firstBuff)

    def _detectCharset(self, stream):
        buff = stream.read(8192)
        result = chardet.detect(buff)
        print "chardet result: " + str(result)
        return (result['encoding'], buff)

    def _checkRedir(self, wbrequest, cdx):
        if cdx and (cdx['timestamp'] != wbrequest.wb_url.timestamp):
            newUrl = wbrequest.urlrewriter.getTimestampUrl(cdx['timestamp'], cdx['original'])
            raise wbexceptions.InternalRedirect(newUrl)
            #return WbResponse.better_timestamp_response(wbrequest, cdx['timestamp'])

        return None


    def doReplay(self, cdx, wbrequest, failedFiles):
        wbresponse = ReplayHandler.doReplay(self, cdx, wbrequest, failedFiles)

        # Check for self redirect
        if wbresponse.status_headers.statusline.startswith('3'):
            if self.isSelfRedirect(wbrequest, wbresponse.status_headers):
                raise wbexceptions.CaptureException('Self Redirect: ' + str(cdx))

        return wbresponse

    def isSelfRedirect(self, wbrequest, status_headers):
        requestUrl = wbrequest.wb_url.url.lower()
        locationUrl = status_headers.getHeader('Location').lower()
        #return requestUrl == locationUrl
        return (ArchivalUrlRewriter.stripProtocol(requestUrl) == ArchivalUrlRewriter.stripProtocol(locationUrl))


#======================================
# PrefixResolver - convert cdx file entry to url with prefix if url contains specified string
#======================================
def PrefixResolver(prefix, contains):
    def makeUrl(url):
        return prefix + url if (contains in url) else None

    return makeUrl

#======================================
class RedisResolver:
    def __init__(self, redisUrl, keyPrefix = 'w:'):
        self.redisUrl = redisUrl
        self.keyPrefix = keyPrefix
        self.redis = redis.StrictRedis.from_url(redisUrl)

    def __call__(self, filename):
        try:
            return self.redis.hget(self.keyPrefix + filename, 'path')
        except Exception as e:
            print e
            return None
