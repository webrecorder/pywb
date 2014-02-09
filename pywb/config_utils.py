import archiveloader
import views
import handlers
import indexreader
import replay_views
import replay_resolvers
import logging


#=================================================================
# Config Loading
#=================================================================
def load_template_file(file, desc = None, view_class = views.J2TemplateView):
    if file:
        logging.info('Adding {0}: {1}'.format(desc if desc else name, file))
        file = view_class(file)

    return file


#=================================================================
def create_wb_handler(**config):
    replayer = replay_views.RewritingReplayView(

        resolvers = replay_resolvers.make_best_resolvers(config.get('archive_paths')),

        loader = archiveloader.ArchiveLoader(hmac = config.get('hmac', None)),

        head_insert_view = load_template_file(config.get('head_html'), 'Head Insert'),

        buffer_response = config.get('buffer_response', True),

        redir_to_exact = config.get('redir_to_exact', True),
    )


    wb_handler = handlers.WBHandler(
        config['cdx_source'],

        replayer,

        html_view = load_template_file(config.get('query_html'), 'Captures Page', views.J2HtmlCapturesView),

        search_view = load_template_file(config.get('search_html'), 'Search Page'),
    )

    return wb_handler


#=================================================================
def load_class(name):
    result = name.rsplit('.', 1)

    if len(result) == 1:
        modname == ''
        klass = result[0]
    else:
        modname = result[0]
        klass = result[1]

    mod =  __import__(modname, fromlist=[klass])
    return getattr(mod, klass)

