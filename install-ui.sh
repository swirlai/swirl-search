#!/bin/bash
#
# Usage:
#   install-ui.sh [<options>]
#
# Install the UI into Swirl static directory. The Swirl install and setup must be run
# before this command can be used.
#
# Options:
#   -h, --help       Display this help message
#   -p, --preview    Use Preview image
#   -x, --x-fork     Use Experimental fork image
#   -d, --directory  Directory on local machine
# Parse command-line options

PROG=`basename $0`

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help) print_help=true ;;
        -p|--preview) preview_image=true ;;
        -x|--x-fork) experimental_image=true ;;
        -d|--directory) shift; source_dir=$1 ;;
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


set -e

# check environment

where_jq=`which jq`
if [ $? -eq 0 ]; then
    echo $PROG "Found jq command in ${where_jq}"
else
    echo $PROG "Could not find jq command on your path, please consult the Installation Guide at https://docs.swirlaiconnect.com/Installation-Community.html."
    exit 1
fi


# local vars
work_container=sw-spg-build_$$
work_dir=/tmp/swirl_ui_install_work_dir_$$
target_dir=./static
ui_home=galaxy
conf_home=api/config

echo $PROG "remove install target : $target_dir/$ui_home"
rm -rf $target_dir/$ui_home

## if Source dir is set, just copy from there.
if [ -n "$source_dir" ]; then
    if ( test -d "$source_dir" ); then
	echo $PROG "source_dir: $source_dir target_dir: $target_dir"
	echo "cp -r $source_dir/ui/dist/spyglass/browser/* $target_dir/$ui_home"
	mkdir -p $target_dir/$ui_home
	mkdir -p $target_dir/$conf_home
	cp -rv $source_dir/ui/dist/spyglass/browser/* $target_dir/$ui_home
	jq '.default' $source_dir/ui/config-swirl-demo.db.json | sed -e "s/<msal-app-id>/$MSAL_APP_ID/" \
								     -e "s/<msal-tenant-id>/$MSAL_TENANT_ID/" \
								     -e "s/<msal-port>/$MSAL_CB_PORT/" \
								     -e "s/<msal-host>/$MSAL_HOST/" \
								     > $target_dir/api/config/default
    jq '.microsoftGalaxyOauth = "'true'"' $target_dir/api/config/default > ./temp_$$ && mv ./temp_$$ $target_dir/api/config/default; rm -rf ./temp_$$
	exit 0
    else
	echo $PROG "ERROR : source_dir:$source_dir does not exist or is not a directory"
	exit 1
    fi
fi

# check environment
if ! [ -d "$target_dir" ]; then
    echo $PROG : "Target directory $target_dir does not exist, please make sure you've run set up and are in the Swirl home directory"
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
docker cp "$work_container:/usr/src/spyglass/ui/config-swirl-demo.db.json" $work_dir
docker rm -f $work_container
rm -rf $target_dir/$ui_home
mkdir $target_dir/$ui_home
mkdir -p $target_dir/$conf_home
cp -r $work_dir/* $target_dir/$ui_home
jq '.default' $work_dir/config-swirl-demo.db.json | sed -e "s/<msal-app-id>/$MSAL_APP_ID/" \
-e "s/<msal-tenant-id>/$MSAL_TENANT_ID/" \
-e "s/<msal-port>/$MSAL_CB_PORT/" \
-e "s/<msal-host>/$MSAL_HOST/" \
> $target_dir/api/config/default
jq '.microsoftGalaxyOauth = "'true'"' $target_dir/api/config/default > ./temp_$$ && mv ./temp_$$ $target_dir/api/config/default; rm -rf ./temp_$$
rm -rf $work_dir
echo $PROG : "Completed normally"
exit 0
