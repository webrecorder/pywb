from six.moves.urllib.parse import urlsplit, urlunsplit, quote

import re

from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.wburl import WbUrl
from pywb.framework.wbrequestresponse import WbRequest, WbResponse


#=================================================================
# ArchivalRouter -- route WB requests in archival mode
#=================================================================
class ArchivalRouter(object):
    def __init__(self, routes, **kwargs):
        self.routes = routes

        # optional port setting may be ignored by wsgi container
        self.port = kwargs.get('port')

        self.fallback = ReferRedirect()

        self.abs_path = kwargs.get('abs_path')

        self.home_view = kwargs.get('home_view')
        self.error_view = kwargs.get('error_view')
        self.info_view = kwargs.get('info_view')

        config = kwargs.get('config', {})
        self.urlrewriter_class = config.get('urlrewriter_class', UrlRewriter)

        self.enable_coll_info = config.get('enable_coll_info', False)

    def __call__(self, env):
        request_uri = self.ensure_rel_uri_set(env)

        for route in self.routes:
            matcher, coll = route.is_handling(request_uri)
            if matcher:
                wbrequest = self.parse_request(route, env, matcher,
                                               coll, request_uri,
                                               use_abs_prefix=self.abs_path)

                return route.handler(wbrequest)

        # Default Home Page
        if request_uri in ['/', '/index.html', '/index.htm']:
            return self.render_home_page(env)

        if self.enable_coll_info and request_uri in ['/collinfo.json']:
            params = env.get('pywb.template_params', {})
            host = WbRequest.make_host_prefix(env)
            return self.info_view.render_response(env=env, host=host, routes=self.routes,
                                                  content_type='application/json',
                                                  **params)

        return self.fallback(env, self) if self.fallback else None

    def parse_request(self, route, env, matcher, coll, request_uri,
                      use_abs_prefix=False):
        matched_str = matcher.group(0)
        rel_prefix = env.get('SCRIPT_NAME', '') + '/'

        if matched_str:
            rel_prefix += matched_str + '/'
            # remove the '/' + rel_prefix part of uri
            wb_url_str = request_uri[len(matched_str) + 2:]
        else:
            # the request_uri is the wb_url, since no coll
            wb_url_str = request_uri[1:]

        wbrequest = route.request_class(env,
                              request_uri=request_uri,
                              wb_url_str=wb_url_str,
                              rel_prefix=rel_prefix,
                              coll=coll,
                              use_abs_prefix=use_abs_prefix,
                              wburl_class=route.handler.get_wburl_type(),
                              urlrewriter_class=self.urlrewriter_class,
                              cookie_scope=route.cookie_scope,
                              rewrite_opts=route.rewrite_opts,
                              user_metadata=route.user_metadata)

        # Allow for applying of additional filters
        route.apply_filters(wbrequest, matcher)

        return wbrequest

    def render_home_page(self, env):
        if self.home_view:
            params = env.get('pywb.template_params', {})
            return self.home_view.render_response(env=env, routes=self.routes, **params)
        else:
            return None

    #=================================================================
    # adapted from wsgiref.request_uri, but doesn't include domain name
    # and allows all characters which are allowed in the path segment
    # according to: http://tools.ietf.org/html/rfc3986#section-3.3
    # explained here:
    # http://stackoverflow.com/questions/4669692/
    #   valid-characters-for-directory-part-of-a-url-for-short-links

    @staticmethod
    def ensure_rel_uri_set(env):
        """ Return the full requested path, including the query string
        """
        if 'REL_REQUEST_URI' in env:
            return env['REL_REQUEST_URI']

        if not env.get('SCRIPT_NAME') and env.get('REQUEST_URI'):
            env['REL_REQUEST_URI'] = env['REQUEST_URI']
            return env['REL_REQUEST_URI']

        url = quote(env.get('PATH_INFO', ''), safe='/~!$&\'()*+,;=:@')
        query = env.get('QUERY_STRING')
        if query:
            url += '?' + query

        env['REL_REQUEST_URI'] = url
        return url


#=================================================================
# Route by matching regex (or fixed prefix)
# of request uri (excluding first '/')
#=================================================================
class Route(object):
    # match upto next / or ? or end
    SLASH_QUERY_LOOKAHEAD = '(?=/|$|\?)'

    def __init__(self, regex, handler, config=None,
                 request_class=WbRequest,
                 lookahead=SLASH_QUERY_LOOKAHEAD):

        config = config or {}
        self.path = regex
        if regex:
            self.regex = re.compile(regex + lookahead)
        else:
            self.regex = re.compile('')

        self.handler = handler
        self.request_class = request_class

        # collection id from regex group (default 0)
        self.coll_group = int(config.get('coll_group', 0))
        self.cookie_scope = config.get('cookie_scope')
        self.rewrite_opts = config.get('rewrite_opts', {})
        self.user_metadata = config.get('metadata', {})
        self._custom_init(config)

    def is_handling(self, request_uri):
        matcher = self.regex.match(request_uri[1:])
        if not matcher:
            return None, None

        coll = matcher.group(self.coll_group)
        return matcher, coll

    def apply_filters(self, wbrequest, matcher):
        for filter in self.filters:
            last_grp = len(matcher.groups())
            filter_str = filter.format(matcher.group(last_grp))
            wbrequest.query_filter.append(filter_str)

    def _custom_init(self, config):
        self.filters = config.get('filters', [])


#=================================================================
# ReferRedirect -- redirect urls that have 'fallen through'
# based on the referrer settings
#=================================================================
class ReferRedirect:
    def __call__(self, env, the_router):
        referrer = env.get('HTTP_REFERER')

        routes = the_router.routes

        # ensure there is a referrer
        if referrer is None:
            return None

        # get referrer path name
        ref_split = urlsplit(referrer)

        # require that referrer starts with current Host, if any
        curr_host = env.get('HTTP_HOST')
        if curr_host and curr_host != ref_split.netloc:
            return None

        path = ref_split.path

        app_path = env.get('SCRIPT_NAME', '')

        if app_path:
            # must start with current app name, if not root
            if not path.startswith(app_path):
                return None

            path = path[len(app_path):]

        ref_route = None
        ref_request = None

        for route in routes:
            matcher, coll = route.is_handling(path)
            if matcher:
                ref_request = the_router.parse_request(route, env,
                                                       matcher, coll, path)
                ref_route = route
                break

        # must have matched one of the routes with a urlrewriter
        if not ref_request or not ref_request.urlrewriter:
            return None

        rewriter = ref_request.urlrewriter

        rel_request_uri = env['REL_REQUEST_URI']

        timestamp_path = '/' + rewriter.wburl.timestamp + '/'

        # check if timestamp is already part of the path
        if rel_request_uri.startswith(timestamp_path):
            # remove timestamp but leave / to make host relative url
            # 2013/path.html -> /path.html
            rel_request_uri = rel_request_uri[len(timestamp_path) - 1:]

        rewritten_url = rewriter.rewrite(rel_request_uri)

        # if post, can't redirect as that would lost the post data
        # (can't use 307 because FF will show confirmation warning)
        if ref_request.method == 'POST':
            new_wb_url = WbUrl(rewritten_url[len(rewriter.prefix):])
            ref_request.wb_url.url = new_wb_url.url
            return ref_route.handler(ref_request)

        final_url = urlunsplit((ref_split.scheme,
                                ref_split.netloc,
                                rewritten_url,
                                '',
                                ''))

        return WbResponse.redir_response(final_url, status='302 Temp Redirect')
