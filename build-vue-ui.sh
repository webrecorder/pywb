#!/bin/bash

CURR_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

cd $CURR_DIR/pywb/vueui/
yarn install
yarn run build
