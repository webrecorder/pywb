from cdxserver import CDXServer
import logging
import os


test_cdx_dir = os.path.dirname(os.path.realpath(__file__)) + '/../../sample_archive/cdx/'

#=================================================================
def main(config = None):
    logging.basicConfig(format = '%(asctime)s: [%(levelname)s]: %(message)s', level = logging.DEBUG)

    if not config:
        config = [test_cdx_dir]

    cdxserver = CDXServer(config)

    def application(env, start_response):
        try:
            response = cdxserver.load_cdx_from_request(env)
            start_response('200 OK', [('Content-Type', 'text/plain')])

            response = list(response)

        except Exception as exc:
            import traceback
            err_details = traceback.format_exc(exc)
            start_response('400 Error', [('Content-Type', 'text/plain')])
            response = [str(exc)]
            print err_details

        return response


    return application


if __name__ == "__main__":
    pass
else:
    application = main()


