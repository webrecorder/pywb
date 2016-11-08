FROM python:3.5

WORKDIR /code/

RUN pip install -U git+https://github.com/ikreymer/pywb.git@develop#egg=pywb-0.30.0-develop
RUN pip install uwsgi gevent bottle

ADD . /code/webagg/
ADD ./test/ /code/test/

WORKDIR /code/
CMD uwsgi /code/test/live.ini


