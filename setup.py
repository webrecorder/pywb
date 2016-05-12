#!/usr/bin/env python
# vim: set sw=4 et:

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        # should work with setuptools <18, 18 18.5
        self.test_suite = ' '

    def run_tests(self):
        import pytest
        import sys
        import os
        cmdline = ' --cov-config .coveragerc --cov ./ -vv webagg/test/ recorder/test/ urlrewrite/test/'
        errcode = pytest.main(cmdline)
        sys.exit(errcode)

setup(
    name='webagg',
    version='1.0',
    author='Ilya Kreymer',
    author_email='ikreymer@gmail.com',
    license='Apache 2.0',
    packages=find_packages(),
    url='https://github.com/webrecorder/webagg',
    description='Resource Aggregator',
    long_description=open('README.rst').read(),
    provides=[
        'webagg',
        'recorder',
        'urlrewrite',
        'proxy',
        ],
    install_requires=[
        'pywb>=0.30.0',
        'werkzeug',
        ],
    dependency_links=[
        #'git+https://github.com/ikreymer/pywb.git@develop#egg=pywb-0.30.0-develop',
    ],
    zip_safe=True,
    entry_points="""
        [console_scripts]
    """,
    cmdclass={'test': PyTest},
    test_suite='',
    tests_require=[
        'pytest',
        'pytest-cov',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ]
)
