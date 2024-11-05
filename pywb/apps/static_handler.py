import mimetypes
import os
from pathlib import Path

from pathvalidate import sanitize_filepath

from pywb.utils.loaders import LocalFileLoader

from pywb.apps.wbrequestresponse import WbResponse
from pywb.utils.wbexception import NotFoundException


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

        # url = sanitize_filepath(url)

        static_path_to_validate = None

        full_path = environ.get('pywb.static_dir')
        if full_path:
            static_path_to_validate = full_path
            full_path = os.path.join(full_path, url)
            if not os.path.isfile(full_path):
                full_path = None

        if not full_path:
            static_path_to_validate = self.static_path
            full_path = os.path.join(self.static_path, url)

        try:
            validate_requested_file_path(static_path_to_validate, url)
        except ValueError:
            raise NotFoundException('Static File Not Found: ' +
                                    url_str)

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

    def validate_requested_file_path(self, static_dir, requested_path):
        """Validate that requested relative file path is within static dir.

        Returns relative path starting from static_dir or raises ValueError if
        path traversal outside the static directory is being attempted.
        """
        static_dir = Path(static_dir)
        return static_dir.joinpath(requested_path).resolve().relative_to(static_dir.resolve())



