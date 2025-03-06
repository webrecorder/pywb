ARG PYTHON=python:3.10

FROM $PYTHON

WORKDIR /pywb

COPY requirements.txt extra_requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt -r extra_requirements.txt

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
