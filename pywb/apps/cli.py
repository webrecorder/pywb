import os
import logging
from argparse import ArgumentParser


#=================================================================
def cdx_server(args=None):  #pragma: no cover
    def load():
        import pywb.apps.cdx_server as mod
        return mod

    cli(appload=load,
        args=args,
        default_port=8090,
        desc='pywb CDX Index Server')


#=================================================================
def live_rewrite_server(args=None):  #pragma: no cover
    def load():
        import pywb.apps.live_rewrite_server as mod
        return mod

    cli(appload=load,
        args=args,
        default_port=8090,
        desc='pywb Live Rewrite Proxy Server')


#=================================================================
def wayback(args=None):
    def load():
        import pywb.apps.wayback as mod
        return mod

    cli(appload=load,
        args=args,
        default_port=8080,
        desc='pywb Wayback Web Archive Replay')


#=================================================================
def cli(appload, args=None, default_port=8080, desc=''):
    parser = ArgumentParser(desc)
    parser.add_argument('-p', '--port', type=int, default=default_port)
    parser.add_argument('-t', '--threads', type=int, default=4)
    parser.add_argument('-a', '--autoindex', action='store_true')

    help_dir='Specify root archive dir (default is current working directory)'
    parser.add_argument('-d', '--directory', help=help_dir)

    r = parser.parse_args(args)
    if r.directory:  #pragma: no cover
        os.chdir(r.directory)

    # Load App
    #from pywb.apps.wayback import application
    application = appload().application

    if r.autoindex:
        from pywb.manager.manager import CollectionsManager
        m = CollectionsManager('', must_exist=False)
        if not os.path.isdir(m.colls_dir):
            msg = 'No managed directory "{0}" for auto-indexing'
            logging.error(msg.format(m.colls_dir))
            import sys
            sys.exit(2)
        else:
            msg = 'Auto-Indexing Enabled on "{0}"'
            logging.info(msg.format(m.colls_dir))
            m.autoindex(do_loop=False)

    try:
        from waitress import serve
        serve(application, port=r.port, threads=r.threads)
    except ImportError:  # pragma: no cover
        # Shouldn't ever happen as installing waitress, but just in case..
        from pywb.framework.wsgi_wrappers import start_wsgi_ref_server
        start_wsgi_ref_server(application, desc, port=r.port)


#=================================================================
if __name__ == "__main__":
    wayback()
