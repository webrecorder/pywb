import os
import pytest

import yaml

@pytest.fixture
def testconfig():
    config = yaml.load(open('tests/test_config.yaml'))
    assert config
    if 'index_paths' not in config:
        # !!! assumes this module is in a sub-directory of project root.
        config['index_paths'] = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '../sample_archive/cdx')
    return config

#================================================================
# Reporter callback for replay view
class PrintReporter:
    """Reporter callback for replay view.
    """
    def __call__(self, wbrequest, cdx, response):
        print(wbrequest)
        print(cdx)
        pass
