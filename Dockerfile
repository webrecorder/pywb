ARG PYTHON=python:3.5.3

FROM $PYTHON

RUN mkdir /uwsgi
COPY uwsgi.ini /uwsgi/

WORKDIR /pywb

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD extra_requirements.txt .
RUN pip install -r extra_requirements.txt

ADD . .
RUN python setup.py install

RUN mkdir /webarchive
COPY config.yaml /webarchive/

VOLUME /webarchive

WORKDIR /webarchive

EXPOSE 8080

CMD ["uwsgi", "/uwsgi/uwsgi.ini"]

RUN useradd -ms /bin/bash -u 1000 archivist

USER archivist


