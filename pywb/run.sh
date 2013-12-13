#!/bin/sh

app=$1
if [ -z "$app" ]; then
  app=wbapp.py
fi

uwsgi --http :9090 --wsgi-file $app
