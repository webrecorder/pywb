ARG PYTHON=python:3.5.3

FROM $PYTHON
EXPOSE 8080
CMD entrypoint.sh

WORKDIR /pywb

COPY requirements.txt extra_requirements.txt ./
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt -r extra_requirements.txt \
 && useradd --create-home --shell /bin/bash -u 1000 archivist

COPY . ./
RUN python setup.py install \
 && mkdir /uwsgi && mv ./uwsgi.ini /uwsgi/ \
 && mkdir /webarchive && mv ./config.yaml /webarchive/

VOLUME /webarchive
WORKDIR /webarchive

USER archivist
