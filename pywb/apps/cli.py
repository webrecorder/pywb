#=================================================================
def wayback(args=None):
    from argparse import ArgumentParser, RawTextHelpFormatter

    parser = ArgumentParser('pywb Wayback Web Archive Replay')
    parser.add_argument('-p', '--port', type=int, default=8080)
    parser.add_argument('-t', '--threads', type=int, default=4)

    help_dir='Specify root archive dir (default is current working directory)'
    parser.add_argument('-d', '--directory', help=help_dir)

    r = parser.parse_args(args)
    if r.directory:  #pragma: no cover
        import os
        os.chdir(r.directory)

    # Load App
    from pywb.apps.wayback import application

    try:
        from waitress import serve
        serve(application, port=r.port, threads=r.threads)
    except ImportError:  # pragma: no cover
        # Shouldn't ever happen as installing waitress, but just in case..
        from pywb.framework.wsgi_wrappers import start_wsgi_server
        start_wsgi_server(application, 'Wayback', default_port=r.port)


#=================================================================
if __name__ == "__main__":
    wayback()

