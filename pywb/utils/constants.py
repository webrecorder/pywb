__all__ = ['ContentRewriteTypes', 'CharSets', 'RewriteMods']


class ContentRewriteTypes(object):
    amf = 'amf'
    cookie = 'cookie'
    css = 'css'
    dash = 'dash'
    header = 'header'
    hls = 'hls'
    html = 'html'
    html_banner_only = 'html-banner-only'
    js = 'js'
    js_proxy = 'js-proxy'
    json = 'json'
    xml = 'xml'

    guess_text = 'guess-text'
    guess_bin = 'guess-bin'
    guess_html = 'guess-html'

    js_and_js_proxy = {'js', 'js-proxy'}
    html_or_js = {'html', 'js'}
    css_or_xml = {'css', 'xml'}

    guess_types = {'guess-text', 'guess-bin', 'guess-html'}
    guess_text_type = {'guess-text', 'guess-html'}
    guess_bin_or_html = {'guess-bin', 'html'}


class CharSets(object):
    utf = 'uft-8'
    iso = 'iso-8859-1'
    ascii = 'ascii'

    utf_and_iso = {'utf-8', 'iso-8859-1'}


class RewriteMods(object):
    binary = 'bn_'
    css = 'cs_'
    frame = 'fr_'
    identity = 'id_'
    iframe = 'if_'
    image = 'im_'
    javascript = 'js_'
    main_page = 'mp_'
    object_embed = 'oe_'
    service_worker = 'sw_'
    web_worker = 'wkr_'

    js_worker_mods = {'sw_', 'wkr_'}
    css_and_js = {'cs_', 'js_'}
    cookie_rw_mods = {'mp_', 'cs_', 'js_', 'im_', 'oe_', 'if_'}
    only_prefix_cookie_mods = {'mp_', 'if_'}
    url_rw_excluded_mods = {'id_', 'bn_', 'sw_', 'wkr_'}
    known_text_types = {'fr_', 'if_', 'mp_', 'bn_', ''}


class RewriteRule(object):
    live_only = 'live_only'
    mixin = 'mixin'
    mixin_type = 'mixin_type'
    js_regex_func = 'js_regex_func'
