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

## ===========
default_head_insert = """

<!-- WB Insert -->
<script src='/static/wb.js'> </script>
<link rel='stylesheet' href='/static/wb.css'/>
<!-- End WB Insert -->
"""

def pywb_config2():
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


def pywb_config(filename = './pywb/config.yaml'):
    config = yaml.load(open(filename))

    routes = map(yaml_parse_route, config['routes'].iteritems())

    hostpaths = config.get('hostpaths', ['http://localhost:8080/'])

    return ArchivalRequestRouter(routes, hostpaths)



def yaml_parse_route((route_name, handler_def)):
    return Route(route_name, yaml_parse_handler(handler_def))


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


def yaml_parse_archive_resolvers(archive_paths):

    #TODO: more options (remote files, contains param, etc..)
    def make_resolver(path):
        if path.startswith('redis://'):
            return replay_resolvers.RedisResolver(path)
        elif os.path.isfile(path):
            return replay_resolvers.PathIndexResolver(path)
        else:
            logging.info('Adding Archive Source: ' + path)
            return replay_resolvers.PrefixResolver(path)

    return map(make_resolver, archive_paths)

def yaml_parse_head_insert(handler_def):
    # First, try a template file
    head_insert_file = handler_def.get('head_insert_template')
    if head_insert_file:
        logging.info('Adding Head-Insert Template: ' + head_insert_file)
        return views.J2HeadInsertView(head_insert_file)

    # Then, static head_insert text
    head_insert_text = handler_def.get('head_insert_text', '')
    logging.info('Adding Head-Insert Text: ' + head_insert_text) 
    return head_insert_text


def yaml_parse_handler(handler_def):
    archive_loader = archiveloader.ArchiveLoader()

    index_loader = yaml_parse_index_loader(handler_def['index_paths'])

    archive_resolvers = yaml_parse_archive_resolvers(handler_def['archive_paths'])

    head_insert = yaml_parse_head_insert(handler_def)

    replayer = replay_views.RewritingReplayView(resolvers = archive_resolvers,
                                                archiveloader = archive_loader,
                                                head_insert = head_insert,
                                                buffer_response = handler_def.get('buffer_response', False))

    html_view_file = handler_def.get('html_query_template')
    if html_view_file:
        logging.info('Adding HTML Calendar Template: ' + html_view_file)
    else:
        logging.info('No HTML Calendar View Present')

    html_view = views.J2QueryView(html_view_file) if html_view_file else None

    wb_handler = handlers.WBHandler(index_loader, replayer, html_view)
    return wb_handler

if __name__ == "__main__" or utils.enable_doctests():
    pass
    #print pywb_config('config.yaml')


