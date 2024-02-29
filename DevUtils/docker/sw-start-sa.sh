#!/bin/bash

# Start Redis in the background
redis-server &

service nginx start

echo "$PROG Copying: .env.dist -> .env"
cp .env.dist .env

echo "$PROG Copying: db.sqlite3.dist -> db.sqlite3"
cp db.sqlite3.dist db.sqlite3

# Your original command to setup and start the application
rm -fr ./.swirl && python swirl.py setup && mkdir -p static/api/config &&
/usr/bin/jq ".default" ./config-swirl-demo.db.json | sed -e "s/<msal-app-id>/$MSAL_APP_ID/" \
    -e "s/<msal-tenant-id>/$MSAL_TENANT_ID/" \
    -e "s/http:\/\/<msal-host>/https:\/\/<msal-host>/" \
    -e "s/<msal-port>/$MSAL_CB_PORT/" \
    -e "s/<msal-host>/$MSAL_HOST/" \
    -e "s/ws:/wss:/" > static/api/config/default &&
python swirl.py start celery-worker celery-beats &&
daphne -b 0.0.0.0 -p 8000 swirl_server.asgi:application

# Keep the container running (if needed)
wait
