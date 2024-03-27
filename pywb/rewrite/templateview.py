from warcio.timeutils import timestamp_to_datetime, timestamp_to_sec
from warcio.timeutils import timestamp_now

from pywb.utils.loaders import load

from six.moves.urllib.parse import urlsplit, quote

from jinja2 import Environment, TemplateNotFound, pass_context, select_autoescape
from jinja2 import FileSystemLoader, PackageLoader, ChoiceLoader

from webassets.ext.jinja2 import AssetsExtension
from webassets.loaders import YAMLLoader
from webassets.env import Resolver

from pkg_resources import resource_filename

import os
import logging

try:
    import ujson as json
except ImportError:  # pragma: no cover
    import json


# ============================================================================
class RelEnvironment(Environment):
    """Override join_path() to enable relative template paths."""
    def join_path(self, template, parent):
        return os.path.join(os.path.dirname(parent), template)


# ============================================================================
class JinjaEnv(object):
    """Pywb JinjaEnv class that provides utility functions used by the templates,
    configured template loaders and template paths, and contains the actual Jinja
    env used by each template."""

    def __init__(self, paths=None,
                 packages=None,
                 assets_path=None,
                 globals=None,
                 overlay=None,
                 extensions=None,
                 env_template_params_key='pywb.template_params',
                 env_template_dir_key='pywb.templates_dir'):
        """Construct a new JinjaEnv.

        :param list[str] paths: List of paths to search for templates
        :param list[str] packages: List of assets package names
        :param str assets_path: Path to a yaml file containing assets
        :param dict[str, str] globals: Dictionary of additional globals available during template rendering
        :param overlay:
        :param list extensions: List of webassets extension classes
        :param str env_template_params_key: The full pywb package key for the template params
        :param str env_template_dir_key: The full pywb package key for the template directory
        """

        if paths is None:
            paths = ['templates', '.', '/']

        if packages is None:
            packages = ['pywb']

        self._init_filters()

        loader = ChoiceLoader(self._make_loaders(paths, packages))

        self.env_template_params_key = env_template_params_key
        self.env_template_dir_key = env_template_dir_key

        extensions = extensions or []

        if assets_path:
            extensions.append(AssetsExtension)

        if overlay:
            jinja_env = overlay.jinja_env.overlay(loader=loader,
                                                  autoescape=select_autoescape(),
                                                  trim_blocks=True,
                                                  extensions=extensions)
        else:
            jinja_env = RelEnvironment(loader=loader,
                                       autoescape=select_autoescape(),
                                       trim_blocks=True,
                                       extensions=extensions)

        jinja_env.filters.update(self.filters)

        if globals:
            jinja_env.globals.update(globals)

        self.jinja_env = jinja_env

        # init assets
        if assets_path:
            assets_loader = YAMLLoader(load(assets_path))
            assets_env = assets_loader.load_environment()
            assets_env.resolver = PkgResResolver()
            jinja_env.assets_environment = assets_env

        self.default_locale = ''

    def _make_loaders(self, paths, packages):
        """Initialize the template loaders based on the supplied paths and packages.

        :param list[str] paths: List of paths to search for templates
        :param list[str] packages: List of assets package names
        :return: A list of loaders to be used for loading the template assets
        :rtype: list[FileSystemLoader|PackageLoader]
        """
        loaders = []
        # add loaders for paths
        for path in paths:
            loaders.append(FileSystemLoader(path))

        # add loaders for all specified packages
        for package in packages:
            loaders.append(PackageLoader(package))

        return loaders

    def init_loc(self, locales_root_dir, locales, loc_map, default_locale):
        locales = locales or []
        locales_root_dir = locales_root_dir or os.path.join('i18n', 'translations')
        default_locale = default_locale or 'en'
        self.default_locale = default_locale

        if locales:
            try:
                from babel.support import Translations
                for loc in locales:
                    loc_map[loc] = Translations.load(locales_root_dir, [loc, default_locale])
            except:
                logging.warn("Ignoring Locales. You must install i18n extensions with 'pip install pywb[i18n]' to use localization features")

        def get_translate(context):
            loc = context.get('env', {}).get('pywb_lang', default_locale)
            return loc_map.get(loc)

        def override_func(jinja_env, name):
            @pass_context
            def get_override(context, text):
                translate = get_translate(context)
                if not translate:
                    return text

                func = getattr(translate, name)
                return func(text)

            jinja_env.globals[name] = get_override

        # standard gettext() translation function
        override_func(self.jinja_env, 'gettext')

        # single/plural form translation function
        override_func(self.jinja_env, 'ngettext')

        # Special _Q() function to return %-encoded text, necessary for use
        # with text in banner
        @pass_context
        def quote_gettext(context, text):
            translate = get_translate(context)
            if not translate:
                return text

            text = translate.gettext(text)
            return quote(text, safe='/: ')

        self.jinja_env.globals['locales'] = list(loc_map.keys())
        self.jinja_env.globals['_Q'] = quote_gettext
        self.jinja_env.globals['default_locale'] = default_locale

        @pass_context
        def switch_locale(context, locale):
            environ = context.get('env')
            curr_loc = environ.get('pywb_lang', '')

            request_uri = environ.get('REQUEST_URI', environ.get('PATH_INFO'))

            if curr_loc and request_uri.startswith('/' + curr_loc + '/'):
                return request_uri.replace(curr_loc, locale, 1)

            app_prefix = environ.get('pywb.app_prefix', '')

            if app_prefix and request_uri.startswith(app_prefix):
                request_uri = request_uri.replace(app_prefix, '')

            return app_prefix + '/' + locale + request_uri

        @pass_context
        def get_locale_prefixes(context):
            environ = context.get('env')
            locale_prefixes = {}

            orig_prefix = environ.get('pywb.app_prefix', '')
            coll = environ.get('SCRIPT_NAME', '')

            if orig_prefix and coll.startswith(orig_prefix):
                coll = coll[len(orig_prefix):]

            curr_loc = environ.get('pywb_lang', '')
            if curr_loc and coll.startswith('/' + curr_loc):
                coll = coll[len(curr_loc) + 1:]

            for locale in loc_map.keys():
                locale_prefixes[locale] = orig_prefix + '/' + locale + coll + '/'

            return locale_prefixes

        self.jinja_env.globals['switch_locale'] = switch_locale
        self.jinja_env.globals['get_locale_prefixes'] = get_locale_prefixes

    def template_filter(self, param=None):
        """Returns a decorator that adds the wrapped function to dictionary of template filters.

        The wrapped function is keyed by either the supplied param (if supplied)
        or by the wrapped functions name.

        :param param: Optional name to use instead of the name of the function to be wrapped
        :return: A decorator to wrap a template filter function
        :rtype: callable
        """
        def deco(func):
            name = param or func.__name__
            self.filters[name] = func
            return func

        return deco

    def _init_filters(self):
        """Initialize the default pywb provided Jninja filters available during template rendering"""
        self.filters = {}

        @self.template_filter()
        def format_ts(value, format_='%a, %b %d %Y %H:%M:%S'):
            """Formats the supplied timestamp using format_

            :param str value: The timestamp to be formatted
            :param str format_:  The format string
            :return: The correctly formatted timestamp as determined by format_
            :rtype: str
            """
            if format_ == '%s':
                return timestamp_to_sec(value)
            else:
                value = timestamp_to_datetime(value)
                return value.strftime(format_)

        @self.template_filter('urlsplit')
        def get_urlsplit(url):
            """Splits the supplied URL

            :param str url: The url to be split
            :return: The split url
            :rtype: urllib.parse.SplitResult
            """
            split = urlsplit(url)
            return split

        @self.template_filter()
        def tojson(obj):
            """Converts the supplied object/array/any to a JSON string if it can be JSONified

            :param any obj: The value to be converted to a JSON string
            :return: The JSON string representation of the supplied value
            :rtype: str
            """
            return json.dumps(obj)

        @self.template_filter()
        def tobool(bool_val):
            """Converts a python boolean to a JS "true" or "false" string
            :param any obj: A value to be evaluated as a boolean
            :return: The string "true" or "false" to be inserted into JS
            """

            return 'true' if bool_val else 'false'


# ============================================================================
class BaseInsertView(object):
    """Base class of all template views used by Pywb"""

    def __init__(self, jenv, insert_file, banner_view=None):
        """Create a new BaseInsertView.

        :param JinjaEnv jenv: The instance of pywb.rewrite.templateview.JinjaEnv to be used
        :param str insert_file: The name of the template file
        :param BaseInsertView banner_view: The banner_view property of pywb.apps.RewriterApp
        """
        self.jenv = jenv
        self.insert_file = insert_file
        self.banner_view = banner_view

    def render_to_string(self, env, **kwargs):
        """Render this template.

        :param dict env: The WSGI environment associated with the request causing this template to be rendered
        :param any kwargs: The keyword arguments to be supplied to the Jninja template render method
        :return: The rendered template
        :rtype: str
        """
        template = None
        template_path = env.get(self.jenv.env_template_dir_key)

        if template_path:
            # jinja paths are not os paths, always use '/' as separator
            # https://github.com/pallets/jinja/issues/411
            template_path = template_path + '/' + self.insert_file

            try:
                template = self.jenv.jinja_env.get_template(template_path)
            except TemplateNotFound as te:
                pass

        if not template:
            template = self.jenv.jinja_env.get_template(self.insert_file)

        params = env.get(self.jenv.env_template_params_key)
        if params:
            kwargs.update(params)

        kwargs['env'] = env
        kwargs['static_prefix'] = env.get('pywb.static_prefix', '/static')


        return template.render(**kwargs)


# ============================================================================
class HeadInsertView(BaseInsertView):
    """The template view class associated with rendering the HTML inserted
    into the head of the pages replayed (WB Insert)."""

    def create_insert_func(self, wb_url,
                           wb_prefix,
                           host_prefix,
                           top_url,
                           env,
                           is_framed,
                           coll='',
                           include_ts=True,
                           **kwargs):
        """Create the function used to render the header insert template for the current request.

        :param rewrite.wburl.WbUrl wb_url: The WbUrl for the request this template is being rendered for
        :param str wb_prefix: The URL prefix pywb is serving the content using (e.g. http://localhost:8080/live/)
        :param str host_prefix: The host URL prefix pywb is running on (e.g. http://localhost:8080)
        :param str top_url: The full URL for this request (e.g. http://localhost:8080/live/http://example.com)
        :param dict env: The WSGI environment dictionary for this request
        :param bool is_framed: Is pywb or a specific collection running in framed mode
        :param str coll: The name of the collection this request is associated with
        :param bool include_ts: Should a timestamp be included in the rendered template
        :param kwargs: Additional keyword arguments to be supplied to the Jninja template render method
        :return: A function to be used to render the header insert for the request this template is being rendered for
        :rtype: callable
        """
        params = kwargs
        params['host_prefix'] = host_prefix
        params['wb_prefix'] = wb_prefix
        params['wb_url'] = wb_url
        params['top_url'] = top_url
        params['coll'] = coll
        params['is_framed'] = is_framed

        def make_head_insert(rule, cdx):
            params['wombat_ts'] = cdx['timestamp'] if include_ts else ''
            params['wombat_sec'] = timestamp_to_sec(cdx['timestamp'])
            params['is_live'] = cdx.get('is_live')

            if self.banner_view:
                banner_html = self.banner_view.render_to_string(env, cdx=cdx, **params)
                params['custom_banner_html'] = banner_html

            return self.render_to_string(env, cdx=cdx, **params)

        return make_head_insert


# ============================================================================
class TopFrameView(BaseInsertView):
    """The template view class associated with rendering the replay iframe"""

    def get_top_frame(self, wb_url,
                      wb_prefix,
                      host_prefix,
                      env,
                      frame_mod,
                      replay_mod,
                      coll='',
                      extra_params=None):
        """
        :param rewrite.wburl.WbUrl wb_url: The WbUrl for the request this template is being rendered for
        :param str wb_prefix: The URL prefix pywb is serving the content using (e.g. http://localhost:8080/live/)
        :param str host_prefix: The host URL prefix pywb is running on (e.g. http://localhost:8080)
        :param dict env: The WSGI environment dictionary for the request this template is being rendered for
        :param str frame_mod:  The modifier to be used for framing (e.g. if_)
        :param str replay_mod: The modifier to be used in the URL of the page being replayed (e.g. mp_)
        :param str coll: The name of the collection this template is being rendered for
        :param dict extra_params: Additional parameters to be supplied to the Jninja template render method
        :return: The frame insert string
        :rtype: str
        """

        embed_url = wb_url.to_str(mod=replay_mod)

        timestamp = ''
        if wb_url.timestamp:
            timestamp = wb_url.timestamp
        #else:
        #    timestamp = timestamp_now()

        is_proxy = 'wsgiprox.proxy_host' in env

        params = {'host_prefix': host_prefix,
                  'wb_prefix': wb_prefix,
                  'wb_url': wb_url,
                  'coll': coll,

                  'options': {'frame_mod': frame_mod,
                              'replay_mod': replay_mod},

                  'embed_url': embed_url,
                  'is_proxy': is_proxy,
                  'timestamp': timestamp,
                  'url': wb_url.get_url()
                 }

        if extra_params:
            params.update(extra_params)

        if self.banner_view:
            banner_html = self.banner_view.render_to_string(env, **params)
            params['banner_html'] = banner_html

        return self.render_to_string(env, **params)


# ============================================================================
class PkgResResolver(Resolver):
    """Class for resolving pywb package resources when install via pypi or setup.py"""

    def get_pkg_path(self, item):
        """Get the package path for the

        :param str item: A resources full package path
        :return: The netloc and path from the items package path
        :rtype: tuple[str, str]
        """
        if not isinstance(item, str):
            return None

        parts = urlsplit(item)
        if parts.scheme == 'pkg' and parts.netloc:
            return (parts.netloc, parts.path)

        return None

    def resolve_source(self, ctx, item):
        pkg = self.get_pkg_path(item)
        if pkg:
            filename = resource_filename(pkg[0], pkg[1])
            if filename:
                return filename

        return super(PkgResResolver, self).resolve_source(ctx, item)


