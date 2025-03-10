#!/bin/sh

set -e

if [ -n "$INIT_COLLECTION" ] && [ ! -d "$VOLUME_DIR/collections/$INIT_COLLECTION" ]; then
    wb-manager init "$INIT_COLLECTION" || echo "Warning: Could not initialize collection."
fi

exec "$@"
