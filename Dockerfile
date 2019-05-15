ARG PYTHON=python:3.7.2
FROM node:11.11.0 as wombat

COPY ./wombat ./buildWombat
WORKDIR buildWombat
RUN yarn install && yarn run build-prod

FROM $PYTHON as pywb

WORKDIR /pywb

COPY requirements.txt extra_requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r extra_requirements.txt

COPY . ./
COPY --from=wombat /pywb/static/*.js ./pywb/static/

RUN python setup.py install \
 && mv ./docker-entrypoint.sh / \
 && mkdir /uwsgi && mv ./uwsgi.ini /uwsgi/ \
 && mkdir /webarchive && mv ./config.yaml /webarchive/ \
 && rm -rf ./wombat

WORKDIR /webarchive

# auto init collection
ENV INIT_COLLECTION ''

ENV VOLUME_DIR /webarchive

#USER archivist
COPY docker-entrypoint.sh ./

# volume and port
VOLUME /webarchive
EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uwsgi", "/uwsgi/uwsgi.ini"]

