ARG PYTHON=python:3.6.7-alpine

FROM $PYTHON

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uwsgi", "/uwsgi/uwsgi.ini"]
ENV GEVENT_LOOP libuv
ENV GEVENT_RESOLVER dnspython

WORKDIR /pywb

COPY requirements.txt extra_requirements.txt ./
RUN apk add --no-cache ca-certificates tzdata \
 && apk add --no-cache --virtual .build-deps build-base libpcre3 libpcre3-dev git libffi-dev libressl-dev linux-headers python3-dev \
 && pip install --no-cache-dir --upgrade pip setuptools \
 && pip install --no-cache-dir -r requirements.txt -r extra_requirements.txt

COPY . ./
RUN python setup.py install \
 && mv ./entrypoint.sh / \
 && mkdir /uwsgi && mv ./uwsgi.ini /uwsgi/ \
 && mkdir /webarchive && mv ./config.yaml /webarchive/

VOLUME /webarchive
WORKDIR /webarchive