FROM python:3.6-alpine

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uwsgi", "/uwsgi/uwsgi.ini"]

WORKDIR /pywb

COPY requirements.txt extra_requirements.txt ./
RUN apk add --no-cache ca-certificates tzdata \
 && apk add --no-cache --virtual .build-deps build-base git libffi-dev libressl-dev linux-headers python3-dev \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt -r extra_requirements.txt \
 && apk del .build-deps

COPY . ./
RUN python setup.py install \
 && mv ./entrypoint.sh / \
 && mkdir /uwsgi && mv ./uwsgi.ini /uwsgi/ \
 && mkdir /webarchive && mv ./config.yaml /webarchive/

VOLUME /webarchive
WORKDIR /webarchive
