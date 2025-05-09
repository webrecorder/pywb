import mimetypes
import os

from pywb.utils.loaders import LocalFileLoader

from pywb.apps.wbrequestresponse import WbResponse
from pywb.utils.wbexception import NotFoundException


# =================================================================
def is_subpath(parent_path, child_path):
    parent = os.path.abspath(parent_path)
    child = os.path.abspath(child_path)
    return os.path.commonpath([parent, child]) == parent


#=================================================================
# Static Content Handler
#=================================================================
class StaticHandler(object):
    def __init__(self, static_path):
        mimetypes.init()

        self.static_path = static_path
        self.block_loader = LocalFileLoader()

    def __call__(self, environ, url_str):
        url = url_str.split('?')[0]

        if url.endswith('/'):
            url += 'index.html'

        full_path = None
        env_static_dir = environ.get('pywb.static_dir')

        if env_static_dir:
            full_path = os.path.join(env_static_dir, url)

            # Prevent path traversal
            if not is_subpath(env_static_dir, full_path):
                raise NotFoundException('Requested a static file outside of static_dir')

            if not os.path.isfile(full_path):
                full_path = None

        if not full_path:
            full_path = os.path.join(self.static_path, url)

            # Prevent path traversal
            if not is_subpath(self.static_path, full_path):
                raise NotFoundException('Requested a static file outside of static_dir')

        try:
            data = self.block_loader.load(full_path)

            data.seek(0, 2)
            size = data.tell()
            data.seek(0)
            headers = [('Content-Length', str(size))]

            reader = None

            if 'wsgi.file_wrapper' in environ:
                try:
                    reader = environ['wsgi.file_wrapper'](data)
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
                                    url_str)


