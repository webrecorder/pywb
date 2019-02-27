#!/bin/bash

BASE=2.2
NOW=$(date +%Y%m%d)
sed -i='' -E  "s/(__version__ = ').*$/\1$BASE.$NOW'/" ./pywb/version.py 
git tag v-$BASE.$NOW
git commit -m "version: update to $BASE.$NOW" ./pywb/version.py
git push
git push origin v-$BASE.$NOW
