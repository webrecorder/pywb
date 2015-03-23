#!/bin/sh

# requires uwsgi
pip install uwsgi
pip install gevent

if [ $? -ne 0 ]; then
    "uwsgi install failed"
    exit 1
fi


mypath=$(cd `dirname $0` && pwd)

params="$mypath/uwsgi.ini"

#if [ -n "$VIRTUAL_ENV" ] ; then
#    params="$params -H $VIRTUAL_ENV"
#fi

uwsgi $params
