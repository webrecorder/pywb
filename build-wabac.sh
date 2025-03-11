#!/bin/bash

WABAC_SW_URL=https://cdn.jsdelivr.net/npm/@webrecorder/wabac@2.21.3/dist/sw.js

wget "$WABAC_SW_URL" -O ./pywb/static/wabacWorker.js
