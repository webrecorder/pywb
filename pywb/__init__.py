import os

DEFAULT_CONFIG = 'pywb/default_config.yaml'

def get_test_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                        '..',
                                        'sample_archive') + os.path.sep
