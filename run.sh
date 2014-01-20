#!/bin/sh

mypath=$(cd `dirname $0` && pwd)

app=$2
cd $mypath/pywb
if [ -z "$app" ]; then
  app=wbapp.py
fi

if [ -z "$1" ]; then
  # Standard root config
  uwsgi --static-map /static=$mypath/static --http-socket :8080 --wsgi-file $app
else
  # Test on non-root mount
  uwsgi --static-map /static=$mypath/static --http-socket :8080 --mount "$1=$app" --no-default-app --manage-script-name
fi

