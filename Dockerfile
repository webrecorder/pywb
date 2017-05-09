FROM python:3.5.3

MAINTAINER Ilya Kreymer <ikreymer at gmail.com>

RUN mkdir /uwsgi
COPY uwsgi.ini /uwsgi/

#RUN pip install gevent==1.1.2 certauth youtube-dl boto uwsgi urllib3
#RUN pip install git+https://github.com/t0m/pyamf.git@python3
#RUN pip install webassets pyyaml brotlipy
#RUN pip install six chardet 'requests<2.12' redis jinja2 'surt>=0.3.0' webencodings portalocker

#RUN mkdir /pywb
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


