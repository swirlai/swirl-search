#!/bin/bash
#
# Usage:
#   pre-checkin-tests.sh [<options>]
#
# Run unit tests and smoke tests
# Options:
#   -h, --help           Display this help message

# Parse command-line options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help) print_help=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done
# Print help message if requested
if [ "$print_help" = true ]; then
    sed -n '/^# Usage:/,/^$/p' "$0"
    exit
fi

PROG=`basename $0`

set -e

# Unit tests

echo $PROG "running pytest unit tests"
pytest
echo $PROG "unit tests succeeded"

## Smoke tests

export ALLOWED_HOSTS=localhost,host.docker.internal
echo $PROG "running smoke tests"
if [ ! -e ".swirl" ]; then
    echo $PROG "starting Swirl"
    python swirl.py start

fi

# make sure we always have the latest
docker pull swirlai/swirl-search-qa:automated-tests-master
docker run --net=host --env-file .env.test.docker -t swirlai/swirl-search-qa:automated-tests-master sh -c "behave --tags=docker_api_smoke"

echo $PROG "smoke tests succeeded"
if [ -e ".swirl" ]; then
        echo $PROG "stopping Swirl"
    python swirl.py stop
fi
