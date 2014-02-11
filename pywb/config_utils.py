import archiveloader
import views
import handlers
import indexreader
import replay_views
import replay_resolvers
import logging
import hmac
import time

#=================================================================
# Config Loading
#=================================================================
def load_template_file(file, desc = None, view_class = views.J2TemplateView):
    if file:
        logging.info('Adding {0}: {1}'.format(desc if desc else name, file))
        file = view_class(file)

    return file

#=================================================================
# Cookie Signing
#=================================================================

class HMACCookieMaker:
    def __init__(self, key, name):
        self.key = key
        self.name = name

    def __call__(self, duration, extra_id = ''):
        expire = str(long(time.time() + duration))

        if extra_id:
            msg = extra_id + '-' + expire
        else:
            msg = expire

        hmacdigest = hmac.new(self.key, msg)
        hexdigest = hmacdigest.hexdigest()

        if extra_id:
            cookie = '{0}-{1}={2}-{3}'.format(self.name, extra_id, expire, hexdigest)
        else:
            cookie = '{0}={1}-{2}'.format(self.name, expire, hexdigest)

        return cookie


#=================================================================
def create_wb_handler(cdx_source, config):

    replayer = replay_views.RewritingReplayView(

        resolvers = replay_resolvers.make_best_resolvers(config.get('archive_paths')),

        loader = archiveloader.ArchiveLoader(hmac = config.get('hmac')),

        head_insert_view = load_template_file(config.get('head_insert_html'), 'Head Insert'),

        buffer_response = config.get('buffer_response', True),

        redir_to_exact = config.get('redir_to_exact', True),

        reporter = config.get('reporter')
    )


    wb_handler = handlers.WBHandler(
        cdx_source,

        replayer,

        html_view = load_template_file(config.get('query_html'), 'Captures Page', views.J2HtmlCapturesView),

        search_view = load_template_file(config.get('search_html'), 'Search Page'),
    )

    return wb_handler

