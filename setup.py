#!/usr/bin/env python
# vim: set sw=4 et:

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import glob


# Fix for TypeError: 'NoneType' object is not callable" error
# when running 'python setup.py test'
try:
    import multiprocessing
except ImportError:
    pass


long_description = open('README.md').read()


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_suite = True

    def run_tests(self):
        import pytest
        import sys
        cmdline = ' --cov-config .coveragerc --cov pywb'
        cmdline += ' -v --doctest-module ./pywb/ tests/'
        errcode = pytest.main(cmdline)
        sys.exit(errcode)

setup(
    name='pywb',
    version='0.2',
    url='https://github.com/ikreymer/pywb',
    author='Ilya Kreymer',
    author_email='ilya@archive.org',
    long_description=long_description,
    license='GPL',
    packages=find_packages(),
    provides=[
        'pywb',
        'pywb.utils',
        'pywb.cdx',
        'pywb.warc',
        'pywb.rewrite',
        'pywb.framework'
        'pywb.perms',
        'pywb.core',
        'pywb.apps'
        ],
    package_data={
        'pywb': ['ui/*', 'static/*', '*.yaml'],
        },
    data_files=[
        ('sample_archive/cdx/', glob.glob('sample_archive/cdx/*')),
        ('sample_archive/zipcdx/', glob.glob('sample_archive/zipcdx/*')),
        ('sample_archive/warcs/', glob.glob('sample_archive/warcs/*')),
        ('sample_archive/text_content/',
            glob.glob('sample_archive/text_content/*')),
        ],
    install_requires=[
        'rfc3987',
        'chardet',
        'redis',
        'jinja2',
        'surt',
        'pyyaml',
       ],
    tests_require=[
        'WebTest',
        'pytest',
        'pytest-cov',
       ],
    cmdclass={'test': PyTest},
    test_suite='',
    )
