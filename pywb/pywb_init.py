import archiveloader
import views
import handlers
import indexreader
import replay_views
import replay_resolvers
import cdxserve
from archivalrouter import ArchivalRequestRouter, Route
import os
import yaml
import utils
import logging

#=================================================================
## Reference non-YAML config
#=================================================================
def pywb_config_manual():
    default_head_insert = """

    <!-- WB Insert -->
    <script src='/static/wb.js'> </script>
    <link rel='stylesheet' href='/static/wb.css'/>
    <!-- End WB Insert -->
    """

    # Current test dir
    #test_dir = utils.test_data_dir()
    test_dir = './sample_archive/'

    # Standard loader which supports WARC/ARC files
    aloader = archiveloader.ArchiveLoader()

    # Source for cdx source
    #query_h = query.QueryHandler(indexreader.RemoteCDXServer('http://cdx.example.com/cdx'))
    #test_cdx = [test_dir + 'iana.cdx', test_dir + 'example.cdx', test_dir + 'dupes.cdx']
    indexs = indexreader.LocalCDXServer([test_dir + 'cdx/'])

    # Loads warcs specified in cdx from these locations
    prefixes = [replay_resolvers.PrefixResolver(test_dir + 'warcs/')]

    # Jinja2 head insert
    head_insert = views.J2HeadInsertView('./ui/head_insert.html')

    # Create rewriting replay handler to rewrite records
    replayer = replay_views.RewritingReplayView(resolvers = prefixes, archiveloader = aloader, head_insert = head_insert, buffer_response = True)

    # Create Jinja2 based html query view
    html_view = views.J2QueryView('./ui/query.html')

    # WB handler which uses the index reader, replayer, and html_view
    wb_handler = handlers.WBHandler(indexs, replayer, html_view)

    # cdx handler
    cdx_handler = handlers.CDXHandler(indexs)

    # Finally, create wb router
    return ArchivalRequestRouter(
        {
            Route('echo_req', handlers.DebugEchoHandler()), # Debug ex: just echo parsed request
            Route('pywb',   wb_handler),
            Route('cdx', cdx_handler),
        },
        # Specify hostnames that pywb will be running on
        # This will help catch occasionally missed rewrites that fall-through to the host
        # (See archivalrouter.ReferRedirect)
        hostpaths = ['http://localhost:8080/'])



#=================================================================
# YAML config loader
#=================================================================
DEFAULT_CONFIG_FILE = 'config.yaml'


def pywb_config(config_file = None):
    if not config_file:
        config_file = os.environ.get('PYWB_CONFIG', DEFAULT_CONFIG_FILE)

    config = yaml.load(open(config_file))

    routes = map(yaml_parse_route, config['routes'])

    hostpaths = config.get('hostpaths', ['http://localhost:8080/'])

    return ArchivalRequestRouter(routes, hostpaths)




def yaml_parse_index_loader(index_config):
    # support mixed cdx streams and remote servers?
    # for now, list implies local sources
    if isinstance(index_config, list):
        return indexreader.LocalCDXServer(index_config)

    if isinstance(index_config, str):
        uri = index_config
        cookie = None
    elif isinstance(index_config, dict):
        uri = index_config['url']
        cookie = index_config['cookie']
    else:
        raise Exception('Invalid Index Reader Config: ' + str(index_config))

    # Check for remote cdx server
    if (uri.startswith('http://') or uri.startswith('https://')) and not uri.endswith('.cdx'):
        return indexreader.RemoteCDXServer(uri, cookie = cookie)
    else:
        return indexreader.LocalCDXServer([uri])


def yaml_parse_head_insert(config):
    # First, try a template file
    head_insert_file = config.get('head_insert_html_template')
    if head_insert_file:
        logging.info('Adding Head-Insert Template: ' + head_insert_file)
        return views.J2HeadInsertView(head_insert_file)

    # Then, static head_insert text
    head_insert_text = config.get('head_insert_text', '')
    logging.info('Adding Head-Insert Text: ' + head_insert_text) 
    return head_insert_text


def yaml_parse_calendar_view(config):
    html_view_file = config.get('calendar_html_template')
    if html_view_file:
        logging.info('Adding HTML Calendar Template: ' + html_view_file)
    else:
        logging.info('No HTML Calendar View Present')

    return views.J2QueryView(html_view_file) if html_view_file else None



def yaml_parse_route(config):
    name = config['name']

    archive_loader = archiveloader.ArchiveLoader()

    index_loader = yaml_parse_index_loader(config['index_paths'])

    archive_resolvers = map(replay_resolvers.make_best_resolver, config['archive_paths'])

    head_insert = yaml_parse_head_insert(config)

    replayer = replay_views.RewritingReplayView(resolvers = archive_resolvers,
                                                archiveloader = archive_loader,
                                                head_insert = head_insert,
                                                buffer_response = config.get('buffer_response', False))

    html_view = yaml_parse_calendar_view(config)

    wb_handler = handlers.WBHandler(index_loader, replayer, html_view)

    return Route(name, wb_handler)


if __name__ == "__main__" or utils.enable_doctests():
    # Just test for execution for now
    pywb_config(os.path.dirname(os.path.realpath(__file__)) + '/../config.yaml')
    pywb_config_manual()


