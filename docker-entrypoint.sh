#!/bin/sh

set -e

# Run as custom user
if ! [ -w $VOLUME_DIR ]; then
    # Get UID/GID from volume dir
    VOLUME_UID=$(stat -c '%u' $VOLUME_DIR)
    VOLUME_GID=$(stat -c '%g' $VOLUME_DIR)

    # create or modify user and group to match expected uid/gid
    groupadd --gid $VOLUME_GID archivist || groupmod -o --gid $VOLUME_GID archivist
    useradd -ms /bin/bash -u $VOLUME_UID -g $VOLUME_GID archivist || usermod -o -u $VOLUME_UID archivist

    # initialize a collection if defined and not present
    if [ -n "$INIT_COLLECTION" ] && [ ! -d $VOLUME_DIR/collections/$INIT_COLLECTION ]; then
        su archivist -c "wb-manager init $INIT_COLLECTION"
    fi

    cmd="cd $PWD; $@"

    # run process as new archivist user
    su archivist -c "$cmd"

# run as current user (root)
else
    # initialize a collection if defined and not present
    if [ -n "$INIT_COLLECTION" ] && [ ! -d $VOLUME_DIR/collections/$INIT_COLLECTION ]; then
        cd $VOLUME_DIR
        wb-manager init $INIT_COLLECTION
    fi

    # run process directly
    exec $@
fi
