#!/usr/bin/env python
# vim: set sw=4 et:

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import glob

from pywb import __version__


long_description = open('README.rst').read()


class PyTest(TestCommand):
    user_options = []
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_suite = ' '

    def run_tests(self):
        from gevent.monkey import patch_all; patch_all()

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
        'pywb.apps',
        'pywb.webagg',
        'pywb.recorder',
        'pywb.urlrewrite'
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
        'six',
        'warcio',
        'chardet',
        'requests',
        'redis',
        'jinja2<2.9',
        'surt>=0.3.0',
        'brotlipy',
        'pyyaml',
        'webencodings',
        'gevent==1.1.2',
        'webassets==0.12.1',
        'portalocker'
        #'pyamf'
    ],
    dependency_links=[
        #'git+https://github.com/t0m/pyamf.git@python3#egg=pyamf-0.8.0'
    ],
    tests_require=[
        'pytest',
        'WebTest<=2.0.23',
        'pytest-cov',
        'fakeredis',
        'mock',
        'urllib3',
        'bottle',
        'werkzeug',
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
        webagg-server = pywb.apps.cli:webagg
        new-wayback = pywb.apps.cli:new_wayback
        """,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
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
