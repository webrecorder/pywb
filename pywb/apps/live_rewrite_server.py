from pywb.framework.wsgi_wrappers import init_app

from pywb.webapp.live_rewrite_handler import create_live_rewriter_app

from argparse import ArgumentParser


#=================================================================
# init rewrite server app
#=================================================================

def create_app():
    parser = ArgumentParser(description='Live Rewrite Server')

    parser.add_argument('-x', '--proxy',
                        action='store',
                        help='Specify host:port to use as HTTP/S proxy')

    result, unknown = parser.parse_known_args()

    config = dict(proxyhostport=result.proxy, framed_replay=True)

    app = init_app(create_live_rewriter_app, load_yaml=False,
                   config=config)

    return app


application = create_app()
