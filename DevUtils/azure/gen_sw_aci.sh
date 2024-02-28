#!/bin/bash
#
# Usage:
#   gen_sw_az_deploy.sh 
#
# Generate command to install swirl in azure containery
#

PROG=`basename $0`

sizemg=8
port=443

read -p "$PROG Enter location (e.g. eastus): " location
read -p "$PROG Enter 'o' for open souce or 'e' for enterprise: " dtype
read -p "$PROG Enter application name: " dname
read -p "$PROG Enter your OpenAI Key ID: " openai_key
read -p "Enter your Azure Registered App ID: " app_id
read -p "Enter your Azure Tenant ID: " tenant_id

location=${location:-eastus}
dtype=${dtype:-o}

if [ "$dtype" = "e" ]; then
    image="swirlai/swirl-search-internal:develop-sa"
elif [ "$dtype" = "o" ]; then
    image="swirlai/swirl-search:develop-sa"
else
    echo $PROG "err unknown deployment type $dtype"
    exit 1
fi


echo az login
echo az group create --name sw$dtype-$dname-rg --location $location
echo az container create \
     --resource-group sw$dtype-$dname-rg \
     --name sw$dtype-$dname \
     --dns-name-label sw$dtype-$dname \
     --ports 80 443 \
     --image $image \
     --environment-variables MSAL_APP_ID=$app_id  MSAL_TENANT_ID=$tenant_id MSAL_CB_PORT=$port MSAL_HOST=sw$dtype-$dname.$location.azurecontainer.io ALLOWED_HOSTS=sw$dtype-$dname.$location.azurecontainer.io OPENAI_API_KEY=$openai_key CSRF_TRUSTED_ORIGINS=https://sw$dtype-$dname.$location.azurecontainer.io \
     --memory $sizemg
 
echo az container logs --resource-group sw$dtype-$dname-rg --name swo-chlorine --container-name sw$dtype-$dname
echo az container exec --resource-group sw$dtype-$dname-rg --name swo-chlorine --container-name sw$dtype-$dname --exec-command "/bin/bash"
