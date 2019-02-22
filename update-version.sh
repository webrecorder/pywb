#!/bin/bash

BASE=2.2
NOW=$(date +%Y%m%d)
sed -i='' -E  "s/(__version__ = ').*$/\1$BASE.$NOW'/" ./pywb/version.py 
git checkout -b v-$BASE.$NOW
git commit ./pywb/version.py
git push origin v-$BASE.$NOW
