#!/bin/bash
#
# Usage:
#   run-integration-tests.sh [<options>]
#
# Run integrated API tests
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


export ALLOWED_HOSTS=localhost,host.docker.internal
echo $PROG "running integration tests"
if [ ! -e ".swirl" ]; then
    echo $PROG "starting Swirl"
    python swirl.py start

fi

docker pull swirlai/swirl-search-qa:automated-tests-master

docker run -e SWIRL_TEST_HOST=host.docker.internal --net=host -t swirlai/swirl-search-qa:automated-tests-master sh -c "behave --tags=integrated_api"

echo $PROG "integration tests succeeded"
if [ -e ".swirl" ]; then
        echo $PROG "stopping Swirl"
    python swirl.py stop
fi
