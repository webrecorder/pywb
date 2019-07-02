#!/bin/bash
set -e

if [ "$WR_TEST" = "no" ]; then
    python setup.py test
else
    cd webrecorder-tests
    INTRAVIS=1 pytest -m "pywbtest and chrometest"
fi
