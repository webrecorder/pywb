import json
import os
import tempfile
import shutil

def to_json_list(cdxlist, fields=['timestamp', 'load_url', 'filename', 'source']):
    return list([json.loads(cdx.to_json(fields)) for cdx in cdxlist])

def key_ts_res(cdxlist, extra='filename'):
    return '\n'.join([cdx['urlkey'] + ' ' + cdx['timestamp'] + ' ' + cdx[extra] for cdx in cdxlist])

def to_path(path):
    if os.path.sep != '/':
        path = path.replace('/', os.path.sep)

    return path


class TempDirTests(object):
    @classmethod
    def setup_class(cls):
        cls.root_dir = tempfile.mkdtemp()

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.root_dir)

