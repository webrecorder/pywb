#!/bin/bash

BASE=2.2

NOW=$(date +%Y%m%d)

VERSION="$BASE.$NOW"

# Update
echo "Updating version to $VERSION"
sed -i='' -E  "s/(__version__ = ').*$/\1$VERSION'/" ./pywb/version.py

if [ "$1" != "commit" ]; then
  exit 0
fi

TAG=v-$VERSION

echo "Committing Tag $TAG"

git commit -m "version: update to $VERSION" ./pywb/version.py
git push

# Tag
git tag $TAG
git push origin $TAG

