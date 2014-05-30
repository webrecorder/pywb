from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.archivalrouter import ArchivalRouter, Route

from pywb.rewrite.rewrite_live import LiveRewriter
from pywb.rewrite.wburl import WbUrl

from handlers import StaticHandler

from pywb.utils.canonicalize import canonicalize
from pywb.utils.timeutils import datetime_to_timestamp
from pywb.utils.statusandheaders import StatusAndHeaders

from pywb.rewrite.rewriterules import use_lxml_parser

import datetime

from views import J2TemplateView, HeadInsertView


#=================================================================
class RewriteHandler(WbUrlHandler):
    def __init__(self, config={}):
        #use_lxml_parser()
        self.rewriter = LiveRewriter(defmod='mp_')

        view = config.get('head_insert_view')
        if not view:
            head_insert = config.get('head_insert_html',
                                     'ui/head_insert.html')
            view = HeadInsertView.create_template(head_insert, 'Head Insert')

        self.head_insert_view = view

        view = config.get('frame_insert_view')
        if not view:
            frame_insert = config.get('frame_insert_html',
                                      'ui/frame_insert.html')

            view = J2TemplateView.create_template(frame_insert, 'Frame Insert')

        self.frame_insert_view = view

    def __call__(self, wbrequest):

        url = wbrequest.wb_url.url

        if not wbrequest.wb_url.mod:
            embed_url = wbrequest.wb_url.to_str(mod='mp_')
            timestamp = datetime_to_timestamp(datetime.datetime.utcnow())

            return self.frame_insert_view.render_response(embed_url=embed_url,
                                                          wbrequest=wbrequest,
                                                          timestamp=timestamp,
                                                          url=url)

        head_insert_func = self.head_insert_view.create_insert_func(wbrequest)

        ref_wburl_str = wbrequest.extract_referrer_wburl_str()
        if ref_wburl_str:
            wbrequest.env['REL_REFERER'] = WbUrl(ref_wburl_str).url

        result = self.rewriter.fetch_request(url, wbrequest.urlrewriter,
                                             head_insert_func=head_insert_func,
                                             env=wbrequest.env)

        status_headers, gen, is_rewritten = result

        return WbResponse(status_headers, gen)


def create_live_rewriter_app():
    routes = [Route('rewrite', RewriteHandler()),
              Route('static/default', StaticHandler('pywb/static/'))
             ]
    return ArchivalRouter(routes, hostpaths=['http://localhost:8080'])
