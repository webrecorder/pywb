#!/bin/bash

BASE=2.2

NOW=$(date +%Y%m%d)

TAG="$BASE.$NOW"

# Update
sed -i='' -E  "s/(__version__ = ').*$/\1$TAG'/" ./pywb/version.py 
git commit -m "version: update to $TAG" ./pywb/version.py
git push

# Tag
git tag v-$TAG
git push origin v-$TAG
