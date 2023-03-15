#!/bin/sh

PROG=`basename $0`

set -e

# local vars
work_container=sw-spg-build_$$
work_dir=/tmp/swirl_ui_install_work_dir_$$
target_dir=./static

# check environment
if ! [ -d "$target_dir" ]; then
    echo $PROG : "Target directory $target_dir does not exist, please make sure you've run set up and are in the SWIRL home directory"
    exit 1
fi

# Clean up on errors
cleanup() {
    rm -rf $work_dir
    docker rm -f $work_container    
}
trap 'cleanup' ERR

mkdir $work_dir
docker create --name $work_container swirlai/spyglass
docker cp "$work_container:/usr/src/spyglass/ui/dist/spyglass/browser/." $work_dir
docker rm -f $work_container

mkdir $target_dir/spyglass
cp -r $work_dir/* $target_dir/spyglass

rm -rf $work_dir
echo $PROG : "Completed normally"
exit 0
