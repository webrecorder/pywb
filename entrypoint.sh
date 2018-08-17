#!/bin/sh

set -e

# defaults
: ${USER_ID:='1000'}
: ${GROUP_ID:='1000'}

# create user and group if necessary
getent group $GROUP_ID > /dev/null || addgroup --gid $GROUP_ID archivist
getent passwd $USER_ID > /dev/null  || adduser --uid $USER_ID -G archivist -D archivist

# initialize a collection if defined and not present
if [ -n "$DEFAULT_COLLECTION" ] && [ ! -d /webarchive/collections/$DEFAULT_COLLECTION ]; then
  wb-manager init $DEFAULT_COLLECTION
fi

# ensure the executing user is owner of the data
chown -R archivist.archivist .
chmod -R u+wx .

# set uwsgi's executing user
export UWSGI_UID=$USER_ID
export UWSGI_GID=$GROUP_ID

# fork a process w/ the command the container was created w/
exec "$@"
