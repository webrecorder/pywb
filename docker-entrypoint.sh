#!/bin/sh

set -e

# Get UID/GID from volume dir
VOLUME_UID=$(stat -c '%u' $VOLUME_DIR)
VOLUME_GID=$(stat -c '%g' $VOLUME_DIR)

MY_UID=$(id -u)
MY_GID=$(id -g)

# Run as custom user
if [ "$MY_GID" != "$VOLUME_GID" ] || [ "$MY_UID" != "$VOLUME_UID" ]; then
    # create user and group if necessary
    groupadd -f --gid $VOLUME_GID archivist
    useradd -ms /bin/bash -u $VOLUME_UID -g $VOLUME_GID archivist

    # set uwsgi's executing user
    #export UWSGI_UID=$VOLUME_UID
    #export UWSGI_GID=$VOLUME_GID
    #export PYTHON_EGGS_DIR=/home/archivist/.cache/Python-Eggs

    # initialize a collection if defined and not present
    if [ -n "$INIT_COLLECTION" ] && [ ! -d $VOLUME_DIR/collections/$INIT_COLLECTION ]; then
        su archivist -c "wb-manager init $INIT_COLLECTION"
    fi

    cmd="cd $PWD; $@"
    su archivist -c "$cmd"

# run as root
else
    # initialize a collection if defined and not present
    if [ -n "$INIT_COLLECTION" ] && [ ! -d $VOLUME_DIR/collections/$INIT_COLLECTION ]; then
        wb-manager init $INIT_COLLECTION
    fi

    # fork a process w/ the command the container was created w/
    exec $@
fi

