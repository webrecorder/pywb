ARG PYTHON=python@sha256:1f741aef81d09464251f4c52c83a02f93ece0a636db125d411bd827bf381a763
FROM $PYTHON

# Update system packages
RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get dist-upgrade -y \
  && apt-get install -y \
    libpcre2-8-0 \
    libpcre2-dev \
    build-essential \
    python3-dev \
  && apt-get clean

# MIMIR: Create archivist user and group
RUN groupadd -g 1001 archivist && useradd -m -u 1001 -g archivist -s /bin/bash archivist


WORKDIR /pywb

COPY requirements.txt extra_requirements.txt ./

RUN pip install --upgrade --no-cache-dir -r requirements.txt -r extra_requirements.txt

COPY . ./

# MIMIR: Added chown command and create folders
RUN python setup.py install \
  && mv ./docker-entrypoint.sh / \
  && mkdir /uwsgi && mv ./uwsgi.ini /uwsgi/ \
  && mkdir -p /webarchive/collections/wayback && mv ./config.yaml /webarchive/ \
  && chown -R archivist:archivist /uwsgi /webarchive /pywb

# MIMIR: Switch to non-root user
USER archivist

WORKDIR /webarchive

# MIMIR: set init collection
ENV INIT_COLLECTION='wayback'

ENV VOLUME_DIR='/webarchive'
ENV UWSGI_MOUNT='/=/pywb/pywb/apps/wayback.py'

#USER archivist
COPY docker-entrypoint.sh ./

# volume and port
VOLUME /webarchive
EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uwsgi", "/uwsgi/uwsgi.ini"]
