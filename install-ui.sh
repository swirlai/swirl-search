#!/bin/bash
#
# Usage:
#   install-ui.sh [<options>]
#
# Install the UI into SWIRL static directory. The SWIRL install and setup must be run
# before this command can be used.
#
# Options:
#   -h, --help           Display this help message
#   -p, --preview        Use Preview image
#   -x, --x-fork         Use Experimental fork image
# Parse command-line options

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help) print_help=true ;;
        -p|--preview) preview_image=true ;;
        -x|--x-fork) experimental_image=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done
# Print help message if requested
if [ "$print_help" = true ]; then
    sed -n '/^# Usage:/,/^$/p' "$0"
    exit
fi

if [ "$preview_image" = true -a "$experimental_image" = true ]; then
    sed -n '/^# Usage:/,/^$/p' "$0"
    echo $PROG ERROR must specify preview or experimental, not both
    exit
fi

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

if [ "$preview_image" = true ]; then
    echo $PROG "PREVIEW IMAGE"
    image="swirlai/spyglass:preview"
elif [ "$experimental_image" = true ]; then
    echo $PROG "EXPERIMENTAL IMAGE"
    image="swirlai/spyglass:fork-x"
else
    echo $PROG "LATEST IMAGE"
    image="swirlai/spyglass"
fi

mkdir $work_dir
docker pull $image
docker create --name $work_container $image
docker cp "$work_container:/usr/src/spyglass/ui/dist/spyglass/browser/." $work_dir
docker rm -f $work_container
rm -rf $target_dir/spyglass
mkdir $target_dir/spyglass
cp -r $work_dir/* $target_dir/spyglass

rm -rf $work_dir
echo $PROG : "Completed normally"
exit 0
