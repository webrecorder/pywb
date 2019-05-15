#!/bin/bash
set -ev

if [[ ${WR_TEST} = "no" && ${WOMBAT_TEST} = "no" ]]; then
    python setup.py test
elif [[ ${WR_TEST} = "yes" && ${WOMBAT_TEST} = "no" ]]; then
    cd webrecorder-tests
    INTRAVIS=1 pytest -m "pywbtest and chrometest"
    cd ..
elif [[ ${WR_TEST} = "no" && ${WOMBAT_TEST} = "yes" ]]; then
    cd wombat
    yarn run test
    cd ..
fi
