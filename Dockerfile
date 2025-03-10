ARG PYTHON=python:3.8
FROM $PYTHON

RUN groupadd -g 1001 archivist && useradd -m -u 1001 -g archivist -s /bin/bash archivist

WORKDIR /pywb

COPY --chown=archivist:archivist requirements.txt extra_requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r extra_requirements.txt

COPY --chown=archivist:archivist . ./

RUN python setup.py install \
 && mv ./docker-entrypoint.sh / \
 && mkdir -p /uwsgi /webarchive \
 && mv ./uwsgi.ini /uwsgi/ \
 && mv ./config.yaml /webarchive/ \
 && chmod -R g+rwX /webarchive /pywb

WORKDIR /webarchive

ENV INIT_COLLECTION ''
ENV VOLUME_DIR /webarchive

COPY --chown=archivist:archivist docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

USER archivist

VOLUME /webarchive
EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uwsgi", "/uwsgi/uwsgi.ini"]
