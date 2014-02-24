import logging

from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.warc.resolvingloader import ResolvingLoader
from pywb.rewrite.rewrite_content import RewriteContent
from pywb.core.views import J2TemplateView, J2HtmlCapturesView
from pywb.core.handlers import WBHandler
from pywb.core.replay_views import ReplayView

#=================================================================
# Config Loading
#=================================================================
def load_template_file(file, desc = None, view_class = J2TemplateView):
    if file:
        logging.debug('Adding {0}: {1}'.format(desc if desc else name, file))
        file = view_class(file)

    return file

#=================================================================
def create_wb_handler(cdx_server, config):

    record_loader = ArcWarcRecordLoader(cookie_maker = config.get('cookie_maker'))
    paths = config.get('archive_paths')

    resolving_loader = ResolvingLoader(paths = paths, cdx_server = cdx_server, record_loader = record_loader)

    replayer = ReplayView(
        content_loader = resolving_loader,

        content_rewriter = RewriteContent(),

        head_insert_view = load_template_file(config.get('head_insert_html'), 'Head Insert'),

        buffer_response = config.get('buffer_response', True),

        redir_to_exact = config.get('redir_to_exact', True),

        reporter = config.get('reporter')
    )


    wb_handler = WBHandler(
        cdx_server,

        replayer,

        html_view = load_template_file(config.get('query_html'), 'Captures Page', J2HtmlCapturesView),

        search_view = load_template_file(config.get('search_html'), 'Search Page'),
    )

    return wb_handler

