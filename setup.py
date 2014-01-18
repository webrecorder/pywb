#!/usr/bin/env python
# vim: set sw=4 et:

import setuptools 

setuptools.setup(name='pywb',
        version='1.0',
        url='https://github.com/ikreymer/pywb',
        author='Ilya Kreymer',
        author_email='ilya@archive.org',
        long_description=open('README.md').read(),
        license='GPL',
        packages=['pywb'],
        install_requires=['uwsgi', 'rfc3987', 'chardet', 'redis', 'jinja2'],
        # test_suite='?',   # not sure how to run doctests here
        zip_safe=False)

