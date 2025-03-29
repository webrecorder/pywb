#!/usr/bin/env python
# vim: set sw=4 et:

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import glob
import os
import pathlib
import sys
import urllib.request

from pywb import __version__


root_dir = pathlib.Path(__file__).parent


#WABAC_SW_URL = "https://cdn.jsdelivr.net/npm/@webrecorder/wabac@2.22.8/dist/sw.js"
WABAC_SW_URL = "https://raw.githubusercontent.com/webrecorder/wabac.js/refs/heads/add-top-frame-passthrough/dist/sw.js"

def download_wabac_sw():
    print(f"Downloading {WABAC_SW_URL}")
    with urllib.request.urlopen(WABAC_SW_URL) as response:  # nosec
        with open(root_dir.joinpath("pywb", "static", "wabacSW.js"), "wb") as fh:
            fh.write(response.read())


download_wabac_sw()


def get_long_description():
    with open('README.rst', 'r') as fh:
        long_description = fh.read()
    return long_description


class PyTest(TestCommand):
    user_options = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_suite = ' '

    def run_tests(self):
        from gevent.monkey import patch_all
        patch_all()

        import pytest
        import os
        os.environ.pop('PYWB_CONFIG_FILE', None)
        cmdline = '--cov-config .coveragerc --cov pywb'
        cmdline += ' -v --doctest-modules ./pywb/ tests/'

        errcode = pytest.main(cmdline.split(' '))

        sys.exit(errcode)


def get_git_short_hash():
    import subprocess
    try:
        hash_id = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).rstrip()
        if sys.version_info >= (3, 0):
            hash_id = hash_id.decode('utf-8')

        return hash_id
    except Exception:
        return ''


def generate_git_hash_py(pkg, filename='git_hash.py'):
    try:
        git_hash = get_git_short_hash()
        with open(os.path.join(pkg, filename), 'wt') as fh:
            fh.write('git_hash = "{0}"\n'.format(git_hash))
    except Exception:
        pass


def load_requirements(filename):
    with open(filename, 'rt') as fh:
        requirements = fh.read().rstrip().split('\n')
    return requirements


def get_package_data():
    pkgs = ['static/*.*',
            'templates/*',
            '*.yaml']

    for root, dirs, files in os.walk(os.path.join('pywb', 'static')):
        for dir_ in dirs:
            pkgs.append(os.path.relpath(os.path.join(root, dir_, '*'), 'pywb'))

    return pkgs


generate_git_hash_py('pywb')

setup(
    name='pywb',
    version=__version__,
    url='https://github.com/webrecorder/pywb',
    author='Ilya Kreymer',
    author_email='ikreymer@gmail.com',
    description='Pywb Webrecorder web archive replay and capture tools',
    long_description=get_long_description(),
    license='GPL',
    packages=find_packages(exclude=['tests_disabled']),
    zip_safe=False,
    package_data={
        'pywb': get_package_data(),
    },
    data_files=[
        ('sample_archive/cdx', glob.glob('sample_archive/cdx/*')),
        ('sample_archive/cdxj', glob.glob('sample_archive/cdxj/*')),
        ('sample_archive/non-surt-cdx', glob.glob('sample_archive/non-surt-cdx/*')),
        ('sample_archive/zipcdx', glob.glob('sample_archive/zipcdx/*')),
        ('sample_archive/warcs', glob.glob('sample_archive/warcs/*')),
        ('sample_archive/text_content',
         glob.glob('sample_archive/text_content/*')),
    ],
    install_requires=load_requirements('requirements.txt'),
    extras_require={
        "i18n":  [
            "babel",
            "translate_toolkit"
        ],
    },
    python_requires='>=3.7,<3.12',
    tests_require=load_requirements("test_requirements.txt"),
    cmdclass={'test': PyTest},
    test_suite='',
    entry_points="""
        [console_scripts]
        pywb = pywb.apps.cli:wayback
        wayback = pywb.apps.cli:wayback
        cdx-server = pywb.apps.cli:cdx_server
        live-rewrite-server = pywb.apps.cli:live_rewrite_server
        cdx-indexer = pywb.indexer.cdxindexer:main
        wb-manager = pywb.manager.manager:main_wrap_exc
        warcserver = pywb.apps.cli:warcserver
        """,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: Proxy Servers',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Archiving',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: Utilities',
    ])
