#!/bin/sh
#
# Remove the pid state swirl.py and celery beat leave behind, so that a
# container that is restarted rather than recreated can start its workers
# again (TECH_DESIGN_swirl_for_backstage.md section 3.8).
#
# Usage: clear_stale_pids.sh [APP_DIR]   (APP_DIR defaults to /app)
#
# swirl.py writes ./.swirl in the app directory, holding {"celery-worker": N,
# ...}. That file lives in the container's writable layer, not on the /data
# volume, so it survives `docker compose restart` while the processes it names
# do not. On the next start swirl.py sees the file and refuses:
#
#   celery-worker is already running - remove .swirl if this is incorrect
#
# ...and the container comes back with daphne and Redis but no Celery worker,
# so the health endpoint never reports ok again.
#
# The pids are not validated first, on purpose. This script runs as the first
# thing in a fresh container process tree, which by definition has no children
# of a previous run; and pid numbers inside a container start at 1 and are
# reused, so a pid from the previous run is quite likely to name an unrelated
# live process (redis-server, daphne) in this one. Checking liveness would
# therefore keep the wedge rather than clear it.
#
# celery beat writes celerybeat.pid in its working directory and refuses to
# start when it already exists, which is the same failure one layer down.
set -e

APP_DIR="${1:-${SWIRL_APP_DIR:-/app}}"

for stale in "$APP_DIR/.swirl" "$APP_DIR/celerybeat.pid"; do
    if [ -e "$stale" ]; then
        echo "entrypoint: removing stale pid state $stale"
        rm -f "$stale"
    fi
done

exit 0
