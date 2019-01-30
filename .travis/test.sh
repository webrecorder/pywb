#!/bin/bash
set -e

if [ "$WR_TEST" = "no" ]; then
    python setup.py test
    cd karma-tests && make test && cd ..
else
    cd webrecorder-tests
    INTRAVIS=1 pytest -m "pywbtest and chrometest"
fi
