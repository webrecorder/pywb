#!/usr/bin/env python
# vim: set sw=4 et:

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import glob

from pywb import __version__


# Fix for TypeError: 'NoneType' object is not callable" error
# when running 'python setup.py test'
try:
    import multiprocessing
except ImportError:
    pass


long_description = open('README.rst').read()


class PyTest(TestCommand):
    user_options = []
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_suite = ' '

    def run_tests(self):
        import pytest
        import sys
        import os
        os.environ.pop('PYWB_CONFIG_FILE', None)
        cmdline = ' --cov-config .coveragerc --cov pywb'
        cmdline += ' -v --doctest-module ./pywb/ tests/'

        errcode = pytest.main(cmdline)

        sys.exit(errcode)

setup(
    name='pywb',
    version=__version__,
    url='https://github.com/ikreymer/pywb',
    author='Ilya Kreymer',
    author_email='ikreymer@gmail.com',
    description='Python WayBack for web archive replay and live web proxy',
    long_description=long_description,
    license='GPL',
    packages=find_packages(),
    zip_safe=True,
    provides=[
        'pywb',
        'pywb.utils',
        'pywb.cdx',
        'pywb.warc',
        'pywb.rewrite',
        'pywb.framework',
        'pywb.manager',
        'pywb.perms',
        'pywb.webapp',
        'pywb.apps'
        ],
    package_data={
        'pywb': ['static/flowplayer/*', 'static/*.*', 'templates/*', '*.yaml'],
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
    install_requires=[
        'chardet',
        'requests',
        'redis',
        'jinja2',
        'surt==0.2',
        'pyyaml',
        'watchdog',
        'webencodings',
       ],
    tests_require=[
        'pytest',
        'WebTest',
        'pytest-cov',
        'fakeredis',
        'mock',
       ],
    cmdclass={'test': PyTest},
    test_suite='',
    entry_points="""
        [console_scripts]
        wayback = pywb.apps.cli:wayback
        cdx-server = pywb.apps.cli:cdx_server
        live-rewrite-server = pywb.apps.cli:live_rewrite_server
        cdx-indexer = pywb.warc.cdxindexer:main
        wb-manager = pywb.manager.manager:main_wrap_exc
        """,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
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
