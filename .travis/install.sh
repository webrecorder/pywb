#!/bin/bash
set -e

pip install --upgrade pip setuptools
python setup.py -q install
pip install -r extra_requirements.txt
pip install coverage pytest-cov coveralls
pip install codecov
npm install

if [ "$WR_TEST" = "yes" ]; then
    git clone https://github.com/webrecorder/webrecorder-tests.git
    cd webrecorder-tests
    pip install --upgrade -r requirements.txt
    ./bootstrap.sh
fi
