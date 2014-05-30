import urlparse
import re

from pywb.rewrite.url_rewriter import UrlRewriter
from wbrequestresponse import WbRequest, WbResponse


#=================================================================
# ArchivalRouter -- route WB requests in archival mode
#=================================================================
class ArchivalRouter(object):
    def __init__(self, routes, **kwargs):
        self.routes = routes

        # optional port setting may be ignored by wsgi container
        self.port = kwargs.get('port')

        hostpaths = kwargs.get('hostpaths')

        if hostpaths:
            self.fallback = ReferRedirect(hostpaths)
        else:
            self.fallback = None

        self.abs_path = kwargs.get('abs_path')

        self.home_view = kwargs.get('home_view')
        self.error_view = kwargs.get('error_view')

    def __call__(self, env):
        for route in self.routes:
            result = route(env, self.abs_path)
            if result:
                return result

        # Default Home Page
        if env['REL_REQUEST_URI'] in ['/', '/index.html', '/index.htm']:
            return self.render_home_page(env)

        return self.fallback(env, self.routes) if self.fallback else None

    def render_home_page(self, env):
        # render the homepage!
        if self.home_view:
            return self.home_view.render_response(env=env, routes=self.routes)
        else:
            # default home page template
            text = '\n'.join(map(str, self.routes))
            return WbResponse.text_response(text)


#=================================================================
# Route by matching regex (or fixed prefix)
# of request uri (excluding first '/')
#=================================================================
class Route(object):
    # match upto next / or ? or end
    SLASH_QUERY_LOOKAHEAD = '(?=/|$|\?)'

    def __init__(self, regex, handler, coll_group=0, config={},
                 request_class=WbRequest,
                 lookahead=SLASH_QUERY_LOOKAHEAD):

        self.path = regex
        if regex:
            self.regex = re.compile(regex + lookahead)
        else:
            self.regex = re.compile('')
        self.handler = handler
        self.request_class = request_class
        # collection id from regex group (default 0)
        self.coll_group = coll_group
        self._custom_init(config)

    def __call__(self, env, use_abs_prefix):
        wbrequest = self.parse_request(env, use_abs_prefix)
        return self.handler(wbrequest) if wbrequest else None

    def parse_request(self, env, use_abs_prefix, request_uri=None):
        if not request_uri:
            request_uri = env['REL_REQUEST_URI']

        matcher = self.regex.match(request_uri[1:])
        if not matcher:
            return None

        matched_str = matcher.group(0)
        if matched_str:
            rel_prefix = env['SCRIPT_NAME'] + '/' + matched_str + '/'
            # remove the '/' + rel_prefix part of uri
            wb_url_str = request_uri[len(matched_str) + 2:]
        else:
            rel_prefix = env['SCRIPT_NAME'] + '/'
            # the request_uri is the wb_url, since no coll
            wb_url_str = request_uri[1:]

        coll = matcher.group(self.coll_group)

        wbrequest = self.request_class(env,
                              request_uri=request_uri,
                              wb_url_str=wb_url_str,
                              rel_prefix=rel_prefix,
                              coll=coll,
                              use_abs_prefix=use_abs_prefix,
                              wburl_class=self.handler.get_wburl_type(),
                              urlrewriter_class=UrlRewriter)

        # Allow for applying of additional filters
        self._apply_filters(wbrequest, matcher)

        return wbrequest

    def _apply_filters(self, wbrequest, matcher):
        for filter in self.filters:
            last_grp = len(matcher.groups())
            filter_str = filter.format(matcher.group(last_grp))
            wbrequest.query_filter.append(filter_str)

    def _custom_init(self, config):
        self.filters = config.get('filters', [])

    def __str__(self):
        #return '* ' + self.regex_str + ' => ' + str(self.handler)
        return str(self.handler)


#=================================================================
# ReferRedirect -- redirect urls that have 'fallen through'
# based on the referrer settings
#=================================================================
class ReferRedirect:
    def __init__(self, match_prefixs):
        if isinstance(match_prefixs, list):
            self.match_prefixs = match_prefixs
        else:
            self.match_prefixs = [match_prefixs]

    def __call__(self, env, routes):
        referrer = env.get('HTTP_REFERER')

        # ensure there is a referrer
        if referrer is None:
            return None

        # get referrer path name
        ref_split = urlparse.urlsplit(referrer)

        # ensure referrer starts with one of allowed hosts
        if not any(referrer.startswith(i) for i in self.match_prefixs):
            if ref_split.netloc != env.get('HTTP_HOST'):
                return None

        path = ref_split.path

        app_path = env['SCRIPT_NAME']

        if app_path:
            # must start with current app name, if not root
            if not path.startswith(app_path):
                return None

            path = path[len(app_path):]

        for route in routes:
            ref_request = route.parse_request(env, False, request_uri=path)
            if ref_request:
                break

        # must have matched one of the routes
        if not ref_request:
            return None

        # must have a rewriter
        if not ref_request.urlrewriter:
            return None

        rewriter = ref_request.urlrewriter

        rel_request_uri = env['REL_REQUEST_URI']

        timestamp_path = '/' + rewriter.wburl.timestamp + '/'

        # check if timestamp is already part of the path
        if rel_request_uri.startswith(timestamp_path):
            # remove timestamp but leave / to make host relative url
            # 2013/path.html -> /path.html
            rel_request_uri = rel_request_uri[len(timestamp_path) - 1:]

        final_url = urlparse.urlunsplit((ref_split.scheme,
                                         ref_split.netloc,
                                         rewriter.rewrite(rel_request_uri),
                                         '',
                                         ''))

        return WbResponse.redir_response(final_url, status='307 Temp Redirect')
