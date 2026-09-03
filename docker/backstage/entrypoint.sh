#!/bin/sh
#
# SWIRL for Backstage container entrypoint
# (TECH_DESIGN_swirl_for_backstage.md section 3.8).
#
# One container: Redis, Django (daphne) and Celery, all against the /data
# volume. Redis is only started here when the broker points at this container;
# an external broker is left alone, so the same script works in the default
# image where docker-compose runs a separate redis service.
#
set -e

DATA_DIR="${SWIRL_DATA_DIR:-/data}"
APP_DIR="${SWIRL_APP_DIR:-/app}"
PORT="${SWIRL_PORT:-8000}"

cd "$APP_DIR"

log() {
    echo "entrypoint: $*"
}

########################################
# The volume

mkdir -p "$DATA_DIR" "$DATA_DIR/redis" "${SWIRL_TANTIVY_DATA_DIR:-$DATA_DIR/tantivy}"

########################################
# Redis, when the broker is this container

broker_is_local() {
    case "${CELERY_BROKER_URL:-}" in
        *localhost*|*127.0.0.1*) return 0 ;;
        *) return 1 ;;
    esac
}

if broker_is_local; then
    if redis-cli ping >/dev/null 2>&1; then
        log "redis is already running"
    else
        log "starting redis-server on the /data volume"
        redis-server --save 60 1 --dir "$DATA_DIR/redis" --daemonize yes \
                     --appendonly no --protected-mode yes --bind 127.0.0.1
        i=0
        until redis-cli ping >/dev/null 2>&1; do
            i=$((i + 1))
            if [ "$i" -gt 60 ]; then
                log "ERROR redis did not answer PING within 30 seconds"
                exit 1
            fi
            sleep 0.5
        done
        log "redis is up"
    fi
else
    log "CELERY_BROKER_URL is not local, not starting redis here"
fi

########################################
# Database

DB_PATH="${SQL_DATABASE:-$DATA_DIR/db.sqlite3}"
case "$DB_PATH" in
    /*) ;;
    *) DB_PATH="$APP_DIR/$DB_PATH" ;;
esac
if [ ! -f "$DB_PATH" ] && [ -f "$APP_DIR/db.sqlite3.dist" ]; then
    log "seeding $DB_PATH from db.sqlite3.dist"
    cp "$APP_DIR/db.sqlite3.dist" "$DB_PATH"
fi

log "applying migrations"
python manage.py migrate --noinput

if [ ! -d "$APP_DIR/static" ]; then
    log "collecting static files"
    python manage.py collectstatic --noinput >/dev/null
fi

########################################
# The Backstage SearchProvider and the admin token

log "loading SearchProviders/backstage.json"
python "$APP_DIR/docker/backstage/load_backstage_provider.py"

########################################
# Workers, then daphne in the foreground

log "starting celery"
python swirl.py start celery-worker celery-beats

log "starting daphne on port $PORT"
exec daphne -b 0.0.0.0 -p "$PORT" swirl_server.asgi:application
