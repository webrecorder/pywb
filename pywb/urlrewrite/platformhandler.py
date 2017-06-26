from gevent.monkey import patch_all; patch_all()

import requests

from pywb.framework.archivalrouter import Route

from pywb.rewrite.rewrite_content import RewriteContent
from pywb.rewrite.wburl import WbUrl
from warcio.recordloader import ArcWarcRecordLoader
from pywb.webapp.live_rewrite_handler import RewriteHandler
from pywb.utils.canonicalize import canonicalize
from warcio.timeutils import http_date_to_timestamp
from pywb.cdx.cdxobject import CDXObject

from io import BytesIO

from pywb.urlrewrite.rewriteinputreq import RewriteInputRequest

from six.moves.urllib.parse import quote


# ============================================================================
class PlatformRoute(Route):
    def apply_filters(self, wbrequest, matcher):
        wbrequest.matchdict = matcher.groupdict()


# ============================================================================
class PlatformHandler(RewriteHandler):
    def __init__(self, config):
        super(PlatformHandler, self).__init__(config)
        self.upstream_url = config.get('upstream_url')
        self.loader = ArcWarcRecordLoader()

        framed = config.get('framed_replay')
        self.content_rewriter = RewriteContent(is_framed_replay=framed)

    def render_content(self, wbrequest):
        if wbrequest.wb_url.mod == 'vi_':
            return self._get_video_info(wbrequest)

        ref_wburl_str = wbrequest.extract_referrer_wburl_str()
        if ref_wburl_str:
            wbrequest.env['HTTP_REFERER'] = WbUrl(ref_wburl_str).url

        urlkey = canonicalize(wbrequest.wb_url.url)
        url = wbrequest.wb_url.url

        inputreq = RewriteInputRequest(wbrequest.env, urlkey, url,
                                       self.content_rewriter)

        req_data = inputreq.reconstruct_request(url)

        headers = {'Content-Length': len(req_data),
                   'Content-Type': 'application/request'}

        if wbrequest.wb_url.is_latest_replay():
            closest = 'now'
        else:
            closest = wbrequest.wb_url.timestamp

        upstream_url = self.upstream_url.format(url=quote(url),
                                                closest=closest,
                                                #coll=wbrequest.coll,
                                                **wbrequest.matchdict)

        r = requests.post(upstream_url,
                          data=BytesIO(req_data),
                          headers=headers,
                          stream=True,
                          allow_redirects=False)

        r.raise_for_status()

        record = self.loader.parse_record_stream(r.raw)

        cdx = CDXObject()
        cdx['urlkey'] = urlkey
        cdx['timestamp'] = http_date_to_timestamp(r.headers.get('Memento-Datetime'))
        cdx['url'] = url

        head_insert_func = self.head_insert_view.create_insert_func(wbrequest)
        result = self.content_rewriter.rewrite_content(wbrequest.urlrewriter,
                                               record.http_headers,
                                               record.stream,
                                               head_insert_func,
                                               urlkey,
                                               cdx)

        status_headers, gen, is_rw = result
        return self._make_response(wbrequest, *result)


if __name__ == "__main__":
    from gevent.wsgi import WSGIServer
    from pywb.apps.wayback import application

    server = WSGIServer(('', 8090), application)
    server.serve_forever()
