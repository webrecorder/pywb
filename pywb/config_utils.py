import views
import handlers
import replay_views
import logging

from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.warc.resolvingloader import ResolvingLoader
from pywb.rewrite.rewrite_content import RewriteContent

#=================================================================
# Config Loading
#=================================================================
def load_template_file(file, desc = None, view_class = views.J2TemplateView):
    if file:
        logging.debug('Adding {0}: {1}'.format(desc if desc else name, file))
        file = view_class(file)

    return file

#=================================================================
def create_wb_handler(cdx_server, config, ds_rules_file=None):

    record_loader = ArcWarcRecordLoader(cookie_maker = config.get('cookie_maker'))
    paths = config.get('archive_paths')

    resolving_loader = ResolvingLoader(paths=paths,
                                       cdx_server=cdx_server,
                                       record_loader=record_loader)

    replayer = replay_views.ReplayView(
        content_loader = resolving_loader,

        content_rewriter = RewriteContent(ds_rules_file=ds_rules_file),

        head_insert_view = load_template_file(config.get('head_insert_html'), 'Head Insert'),

        buffer_response = config.get('buffer_response', True),

        redir_to_exact = config.get('redir_to_exact', True),

        reporter = config.get('reporter')
    )


    wb_handler = handlers.WBHandler(
        cdx_server,

        replayer,

        html_view = load_template_file(config.get('query_html'), 'Captures Page', views.J2HtmlCapturesView),

        search_view = load_template_file(config.get('search_html'), 'Search Page'),
    )

    return wb_handler

