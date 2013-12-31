#!/bin/sh

mypath=$(cd `dirname $0` && pwd)

app=$1
cd $mypath/pywb
if [ -z "$app" ]; then
  app=wbapp.py
fi

uwsgi --static-map /static=$mypath/static --http :8080 --wsgi-file $app
