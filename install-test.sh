#!/bin/sh

PROG=`basename $0`

echo $PROG "Installing test dependencies:"
pip install -r requirements-test.txt

echo $PROG : "Completed normally"
exit 0

