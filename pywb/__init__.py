from pywb.version import __version__

DEFAULT_CONFIG = 'pywb/default_config.yaml'

DEFAULT_RULES_FILE = 'pkg://pywb/rules.yaml'


def get_test_dir():
    import os
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                        '..',
                                        'sample_archive') + os.path.sep
