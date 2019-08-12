#!/bin/bash

CURR_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

cd $CURR_DIR/wombat
export OUTPUT_DIR=../pywb/static/
yarn install
yarn run build-prod
#cp ./dist/*.js ../pywb/static/
