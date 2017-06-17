__version__ = '0.33.2'

DEFAULT_CONFIG = 'pywb/default_config.yaml'


def get_test_dir():
    import os
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                        '..',
                                        'sample_archive') + os.path.sep
