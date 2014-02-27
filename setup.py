#!/usr/bin/env python
# vim: set sw=4 et:

import setuptools
import glob

setuptools.setup(name='pywb',
        version='0.2',
        url='https://github.com/ikreymer/pywb',
        author='Ilya Kreymer',
        author_email='ilya@archive.org',
        long_description=open('README.md').read(),
        license='GPL',
        packages=['pywb','pywb.utils','pywb.cdx','pywb.warc','pywb.rewrite'],
        provides=['pywb','pywb.utils','pywb.cdx','pywb.warc','pywb.rewrite'],
        package_data={'pywb': ['ui/*', 'static/*', '*.yaml']},
        data_files = [('sample_archive/cdx/', glob.glob('sample_archive/cdx/*')),
                      ('sample_archive/warcs/', glob.glob('sample_archive/warcs/*')),
                      ('sample_archive/text_content/', glob.glob('sample_archive/text_content/*'))],
        install_requires=['uwsgi', 'rfc3987', 'chardet', 'redis', 'jinja2', 'surt', 'pyyaml', 'WebTest','pytest'],
#        tests_require=['WebTest', 'pytest'],
        zip_safe=False)

