#!/bin/bash

CURR_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

cd $CURR_DIR/wabac.js
yarn install
yarn run build
cp ./dist/sw.js ../pywb/static/wabacWorker.js
