import mimetypes

from pywb.utils.loaders import LocalFileLoader

from pywb.framework.wbrequestresponse import WbResponse


#=================================================================
# Static Content Handler
#=================================================================
class StaticHandler(object):
    def __init__(self, static_path):
        mimetypes.init()

        self.static_path = static_path
        self.block_loader = LocalFileLoader()

    def __call__(self, wbrequest):
        url = wbrequest.wb_url_str.split('?')[0]
        full_path = self.static_path + url

        try:
            data = self.block_loader.load(full_path)

            data.seek(0, 2)
            size = data.tell()
            data.seek(0)
            headers = [('Content-Length', str(size))]

            reader = None

            if 'wsgi.file_wrapper' in wbrequest.env:
                try:
                    reader = wbrequest.env['wsgi.file_wrapper'](data)
                except:
                    pass

            if not reader:
                reader = iter(lambda: data.read(), b'')

            content_type = 'application/octet-stream'

            guessed = mimetypes.guess_type(full_path)
            if guessed[0]:
                content_type = guessed[0]

            return WbResponse.bin_stream(reader,
                                         content_type=content_type,
                                         headers=headers)

        except IOError:
            raise NotFoundException('Static File Not Found: ' +
                                    wbrequest.wb_url_str)


