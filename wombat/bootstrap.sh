#!/usr/bin/env bash

SELF_D=$(dirname ${BASH_SOURCE[0]})
ASSETSPath="${SELF_D}/test/assets"
NODEM="${SELF_D}/node_modules"
INTERNAL="${SELF_D}/internal"
ROLLUP="${NODEM}/.bin/rollup"

if hash yarn 2>/dev/null; then
  yarn install
else
  npm install
fi

printf "\nBuilding wombat in prod mode"
node ${ROLLUP} -c rollup.config.prod.js


printf "\nBootstrapping tests"
cp "../pywb/static/css/bootstrap.min.css" "${ASSETSPath}/bootstrap.min.css"
node ${ROLLUP} -c "${INTERNAL}/rollup.testPageBundle.config.js"
node ${ROLLUP} -c "${SELF_D}/rollup.config.test.js"
