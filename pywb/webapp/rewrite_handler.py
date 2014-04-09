from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.archivalrouter import ArchivalRouter, Route

from pywb.rewrite.rewrite_content import RewriteContent

from handlers import StaticHandler

from pywb.utils.canonicalize import canonicalize
from pywb.utils.timeutils import datetime_to_timestamp
from pywb.utils.statusandheaders import StatusAndHeaders

from pywb.rewrite.rewriterules import use_lxml_parser

import datetime
import requests

from io import BytesIO, BufferedReader

from views import J2TemplateView, HeadInsertView


class RewriteHandler(WbUrlHandler):  # pragma: no cover
    def __init__(self, head_insert_view=None):
        #use_lxml_parser()
        self.rewriter = RewriteContent(defmod='mp_')
        self.head_insert_view = (HeadInsertView.
                                 create_template('ui/head_insert.html',
                                                 'Head Insert'))

        self.frame_insert_view = (J2TemplateView.
                                  create_template('ui/frame_insert.html',
                                                  'Frame Insert'))

    def proxy_request(self, url, env):

        method = env['REQUEST_METHOD'].upper()
        input_ = env['wsgi.input']

        ua = env['HTTP_USER_AGENT']

        req_headers = {'User-Agent': ua}

        if url.startswith('//'):
            url = 'http:' + url

        if method in ('POST', 'PUT'):
            data = input_
        else:
            data = None

        response = self.do_http_request(method,
                                        url,
                                        data,
                                        req_headers)
        code = response.status_code

        headers = response.headers.items()
        stream = response.raw

        status_headers = StatusAndHeaders(str(code), headers)

        return (status_headers, stream)

    def do_http_request(self, method, url, data, req_headers):
        req = requests.request(method=method,
                               url=url,
                               data=data,
                               headers=req_headers,
                               allow_redirects=False,
                               stream=True)
        return req

    def __call__(self, wbrequest):

        url = wbrequest.wb_url.url

        if not wbrequest.wb_url.mod:
            embed_url = wbrequest.wb_url.to_str(mod='mp_')
            timestamp = datetime_to_timestamp(datetime.datetime.utcnow())

            return self.frame_insert_view.render_response(embed_url=embed_url,
                                                          wbrequest=wbrequest,
                                                          timestamp=timestamp,
                                                          url=url)

        ts_err = url.split('///')
        if len(ts_err) > 1:
            url = 'http://' + ts_err[1]

        try:
            status_headers, stream = self.proxy_request(url, wbrequest.env)
        except Exception:
            print 'ERR on ', url
            raise

        urlkey = canonicalize(url)

        cdx = {'urlkey': urlkey,
               'timestamp': datetime_to_timestamp(datetime.datetime.utcnow()),
               'original': url,
               'statuscode' : status_headers.statusline.split(' ')[0],
               'mimetype' : status_headers.get_header('Content-Type')
              }


        #head_insert_func = self.get_head_insert_func(wbrequest, cdx)
        head_insert_func = self.head_insert_view.create_insert_func(wbrequest,
                                                                    cdx)

        result = self.rewriter.rewrite_content(wbrequest.urlrewriter,
                                               status_headers,
                                               stream,
                                               head_insert_func=head_insert_func,
                                               urlkey=urlkey)

        status_headers, gen, is_rewritten = result

        return WbResponse(status_headers, gen)


def create_rewrite_app(): # pragma: no cover
    routes = [Route('rewrite', RewriteHandler()),
              Route('static/default', StaticHandler('pywb/static/'))
             ]
    return ArchivalRouter(routes, hostpaths=['http://localhost:8080'])
