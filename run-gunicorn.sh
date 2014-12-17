#!/bin/sh
pip install gunicorn

if [ $? -ne 0 ]; then
    "gunicorn install failed"
    exit 1
fi

export PYWB_CONFIG_FILE=config.yaml
gunicorn -w 4 pywb.apps.wayback -b 0.0.0.0:8080
