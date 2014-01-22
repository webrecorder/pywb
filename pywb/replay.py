import StringIO
from urllib2 import URLError
import chardet
import redis
import copy

import indexreader, archiveloader
from wbrequestresponse import WbResponse, StatusAndHeaders
from wbarchivalurl import ArchivalUrl
import utils

from url_rewriter import ArchivalUrlRewriter
from header_rewriter import HeaderRewriter
import html_rewriter
import regex_rewriters

import wbexceptions

#=================================================================
class WBHandler:
    def __init__(self, query, replay, htmlquery = None):
        self.query = query
        self.replay = replay
        self.htmlquery = htmlquery

    def __call__(self, wbrequest):
        with utils.PerfTimer(wbrequest.env.get('X_PERF'), 'query') as t:
            query_response = self.query(wbrequest)

        if (wbrequest.wb_url.type == wbrequest.wb_url.QUERY) or (wbrequest.wb_url.type == wbrequest.wb_url.URL_QUERY):
            return self.htmlquery(wbrequest, query_response) if self.htmlquery else query_response

        with utils.PerfTimer(wbrequest.env.get('X_PERF'), 'replay') as t:
            return self.replay(wbrequest, query_response, self.query)


#=================================================================
class ReplayHandler(object):
    def __init__(self, resolvers, archiveloader):
        self.resolvers = resolvers
        self.archiveloader = archiveloader

    def __call__(self, wbrequest, query_response, query):
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

                response = self.doReplay(cdx, wbrequest, query, failedFiles)

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


    def doReplay(self, cdx, wbrequest, query, failedFiles):
        hasCurr = (cdx['filename'] != '-')
        hasOrig = (cdx.get('orig.filename','-') != '-')

        # load headers record from cdx['filename'] unless it is '-' (rare)
        headersRecord = self._load(cdx, False, failedFiles) if hasCurr else None

        # two index lookups
        # Case 1: if mimetype is still warc/revisit
        if cdx['mimetype'] == 'warc/revisit' and headersRecord:
            payloadRecord = self._load_different_url_payload(wbrequest, query, cdx, headersRecord, failedFiles)

        # single lookup cases
        # case 2: non-revisit
        elif (hasCurr and not hasOrig):
            payloadRecord = headersRecord

        # case 3: identical url revisit, load payload from orig.filename
        elif (hasOrig):
            payloadRecord = self._load(cdx, True, failedFiles)

        # special case: set header to payload if old-style revisit with missing header
        if not headersRecord:
            headersRecord = payloadRecord
        elif headersRecord != payloadRecord:
            # close remainder of stream as this record only used for (already parsed) headers
            headersRecord.stream.close()

            # special case: check if headers record is actually empty (eg empty revisit), then use headers from revisit
            if not headersRecord.status_headers.headers:
                headersRecord = payloadRecord


        if not headersRecord or not payloadRecord:
            raise wbexceptions.CaptureException('Invalid CDX' + str(cdx))


        return WbResponse.stream_response(headersRecord.status_headers, payloadRecord.stream)



    # Handle the case where a duplicate of a capture with same digest exists at a different url
    # Must query the index at that url filtering by matching digest
    # Raise exception if no matches found
    def _load_different_url_payload(self, wbrequest, query, cdx, headersRecord, failedFiles):
        ref_target_uri = headersRecord.rec_headers.getHeader('WARC-Refers-To-Target-URI')

        # Check for unresolved revisit error, if refers to target uri not present or same as the current url
        if not ref_target_uri or (ref_target_uri == headersRecord.rec_headers.getHeader('WARC-Target-URI')):
            raise wbexceptions.CaptureException('Missing Revisit Original' + str(cdx))

        ref_target_date = headersRecord.rec_headers.getHeader('WARC-Refers-To-Date')

        if not ref_target_date:
            ref_target_date = cdx['timestamp']
        else:
            ref_target_date = utils.iso_date_to_timestamp(ref_target_date)

        # clone WbRequest
        orig_wbreq = copy.copy(wbrequest)
        orig_wbreq.wb_url = copy.copy(orig_wbreq.wb_url)

        orig_wbreq.wb_url.url = ref_target_uri
        orig_wbreq.wb_url.timestamp = ref_target_date

        # Must also match digest
        orig_wbreq.queryFilter.append('digest:' + cdx['digest'])

        orig_cdxlines = query(orig_wbreq).body

        for cdx in orig_cdxlines:
            try:
                cdx = indexreader.CDXCaptureResult(cdx)
                #print cdx
                payloadRecord = self._load(cdx, False, failedFiles)
                return payloadRecord

            except wbexceptions.CaptureException as e:
                pass

        raise wbexceptions.CaptureException('Original for revisit could not be loaded')


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

    def __init__(self, resolvers, archiveloader, headInsert = None, headerRewriter = None, redir_to_exact = True, buffer_response = False):
        ReplayHandler.__init__(self, resolvers, archiveloader)
        self.headInsert = headInsert
        if not headerRewriter:
            headerRewriter = HeaderRewriter()
        self.headerRewriter = headerRewriter
        self.redir_to_exact = redir_to_exact

        # buffer or stream rewritten response
        self.buffer_response = buffer_response


    def _textContentType(self, contentType):
        for ctype, mimelist in self.REWRITE_TYPES.iteritems():
            if any ((mime in contentType) for mime in mimelist):
                return ctype

        return None


    def __call__(self, wbrequest, query_response, query):
        urlrewriter = ArchivalUrlRewriter(wbrequest.wb_url, wbrequest.wb_prefix)
        wbrequest.urlrewriter = urlrewriter

        response = ReplayHandler.__call__(self, wbrequest, query_response, query)

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

        # handle transfer-encoding: chunked
        if (rewrittenHeaders.containsRemovedHeader('transfer-encoding', 'chunked')):
            stream = archiveloader.ChunkedLineReader(stream)

        # special case -- need to ungzip the body
        if (rewrittenHeaders.containsRemovedHeader('content-encoding', 'gzip')):
            stream = archiveloader.LineReader(stream, decomp = utils.create_decompressor())

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
        #if rewrittenHeaders.textType == 'html':
        #    return self._rewriteHtml(encoding, urlrewriter, stream, rewrittenHeaders.status_headers, firstBuff)
        #else:
        #    return self._rewriteOther(rewrittenHeaders.textType, encoding, urlrewriter, stream, rewrittenHeaders.status_headers, firstBuff)

        textType = rewrittenHeaders.textType
        status_headers = rewrittenHeaders.status_headers

        if textType == 'html':
            rewriter = html_rewriter.WBHtml(urlrewriter, outstream = None, headInsert = self.headInsert)
        elif textType == 'css':
            rewriter = regex_rewriters.CSSRewriter(urlrewriter)
        elif textType == 'js':
            rewriter = regex_rewriters.JSRewriter(urlrewriter)
        elif textType == 'xml':
            rewriter = regex_rewriters.XMLRewriter(urlrewriter)
        else:
            raise Exception('Unknown Text Type for Rewrite: ' + textType)


        if self.buffer_response:
            return self._buffer_rewrite_response(rewriter, encoding, stream, status_headers, firstBuff)
        else:
            return self._stream_rewrite_response(rewriter, encoding, stream, status_headers, firstBuff)


    # Buffer rewrite response, and serve with full Content-Length
    def _buffer_rewrite_response(self, rewriter, encoding, stream, status_headers, firstBuff = None):
        out = StringIO.StringIO()

        try:
            buff = firstBuff if firstBuff else stream.read()
            while buff:
                if encoding:
                    buff = self._decodeBuff(buff, stream, encoding)

                out.write(rewriter.rewrite(buff))
                buff = stream.read()

            # Close rewriter if gracefully made it to end
            rewriter.close()

        finally:
            content = out.getvalue()

            if encoding:
                content = content.encode(encoding)

            value = [content]
            contentLengthStr = str(len(content))
            status_headers.headers.append(('Content-Length', contentLengthStr))
            out.close()

        return WbResponse(status_headers, value = value)

    # Stream rewrite response from record (no Content-Length), may even be chunked by front-end
    def _stream_rewrite_response(self, rewriter, encoding, stream, status_headers, firstBuff = None):
        def doRewrite(buff):
            if encoding:
                buff = self._decodeBuff(buff, stream, encoding)

            buff = rewriter.rewrite(buff)

            if encoding:
                buff = buff.encode(encoding)

            return buff

        def doFinish():
            return rewriter.close()

        return WbResponse.stream_response(status_headers, stream, rewrite_func = doRewrite, final_read_func = doFinish, first_buff = firstBuff)


    def _decodeBuff(self, buff, stream, encoding):
        try:
            buff = buff.decode(encoding)
        except UnicodeDecodeError, e:
            # chunk may have cut apart unicode bytes -- add 1-3 bytes and retry
            for i in range(3):
                buff += stream.read(1)
                try:
                    buff = buff.decode(encoding)
                    break
                except UnicodeDecodeError:
                    pass
            else:
                raise

        return buff


    def _detectCharset(self, stream):
        buff = stream.read(8192)
        result = chardet.detect(buff)
        print "chardet result: " + str(result)
        return (result['encoding'], buff)


    def _checkRedir(self, wbrequest, cdx):
        if self.redir_to_exact and cdx and (cdx['timestamp'] != wbrequest.wb_url.timestamp):
            newUrl = wbrequest.urlrewriter.getTimestampUrl(cdx['timestamp'], cdx['original'])
            raise wbexceptions.InternalRedirect(newUrl)
            #return WbResponse.better_timestamp_response(wbrequest, cdx['timestamp'])

        return None


    def doReplay(self, cdx, wbrequest, query, failedFiles):
        wbresponse = ReplayHandler.doReplay(self, cdx, wbrequest, query, failedFiles)

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
