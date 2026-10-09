ARG PYTHON=python:3.14-slim

FROM $PYTHON

WORKDIR /pywb

COPY requirements.txt ./

# pyuwsgi wheel links against libexpat, which the slim image lacks
RUN apt-get update \
 && apt-get install -y --no-install-recommends libexpat1 \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt \
    pyuwsgi boto3 pysocks lxml ujson babel translate_toolkit babel-vue-extractor

COPY . ./

RUN python setup.py install \
 && mv ./docker-entrypoint.sh / \
 && mkdir /uwsgi && mv ./uwsgi.ini /uwsgi/ \
 && mkdir /webarchive && mv ./config.yaml /webarchive/

WORKDIR /webarchive

# auto init collection
ENV INIT_COLLECTION ''

ENV VOLUME_DIR /webarchive
ENV UWSGI_MOUNT '/=/pywb/pywb/apps/wayback.py'

#USER archivist
COPY docker-entrypoint.sh ./

# volume and port
VOLUME /webarchive
EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uwsgi", "/uwsgi/uwsgi.ini"]
