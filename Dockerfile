#webrecorder/webrecore 1.0

FROM python:3.5.2

RUN pip install gevent uwsgi bottle urllib3 youtube-dl

RUN pip install git+https://github.com/ikreymer/pywb.git@develop#egg=pywb-0.32.2
#RUN pip install pywb

RUN pip install git+https://github.com/t0m/pyamf.git@python3

RUN pip install boto

ADD . /webrecore/
WORKDIR /webrecore/

RUN pip install -e ./

RUN useradd -ms /bin/bash -u 1000 apprun

USER apprun


