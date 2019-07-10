#!/bin/bash

VERSION=$(python ./pywb/version.py)

TAG=v-$VERSION

echo "Committing Tag $TAG"

if [ "$1" != "commit" ]; then
  exit 0
fi

# Tag
git tag $TAG
git push origin $TAG

