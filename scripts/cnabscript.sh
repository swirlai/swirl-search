# This script will be accessed via public storage contaoner to ARM Template.
# https://swirlcnabscript.blob.core.windows.net/swirlcnab/cnabscript.sh

# Install kubectl
az aks install-cli --only-show-errors

# Get AKS credentials
az aks get-credentials \
  --admin \
  --name $clusterName \
  --resource-group $resourceGroupName \
  --subscription $subscriptionId \
  --only-show-errors

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 -o get_helm.sh -s
chmod 700 get_helm.sh
./get_helm.sh &>/dev/null


# Install Ingress controller
command="helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx; helm repo update; helm install ingress-nginx ingress-nginx/ingress-nginx \
    --create-namespace \
    --namespace ingress-controller \
    --set controller.replicaCount=2 \
    --set defaultBackend.nodeSelector."kubernetes\.io/os"=linux \
    --set controller.service.annotations.\"service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path\"=/healthz"

az aks command invoke \
    --name $clusterName \
    --resource-group $resourceGroupName \
    --subscription $subscriptionId \
    --command "$command";

# # Install Cert Manager
command="helm repo add jetstack https://charts.jetstack.io; helm repo update; helm install cert-manager jetstack/cert-manager \
    --create-namespace \
    --namespace cert-manager \
    --set installCRDs=true \
    --set nodeSelector.\"kubernetes\.io/os\"="linux" \
    --set-string podLabels.\"azure\.workload\.identity/use\"=true \
    --set-string serviceAccount.labels.\"azure\.workload\.identity/use\"=true"


az aks command invoke \
    --name $clusterName \
    --resource-group $resourceGroupName \
    --subscription $subscriptionId \
    --command "$command";


# # Create application Namespace and secrets

command="kubectl create namespace swirl";

az aks command invoke \
    --name $clusterName \
    --resource-group $resourceGroupName \
    --subscription $subscriptionId \
    --command "$command";

command="kubectl create secret generic swirl-env-secrets --namespace swirl \
    --from-literal=SQL_USER=$DbAdminUsername \
    --from-literal=SQL_DATABASE=$DbName \
    --from-literal=SQL_PASSWORD=$DbAdminPassword \
    --from-literal=SQL_HOST=$DbServerName \
    --from-literal=SQL_PORT=$DbPort \
    --from-literal=ADMIN_PASSWORD=$DjangoAdminPassword"

az aks command invoke \
    --name $clusterName \
    --resource-group $resourceGroupName \
    --subscription $subscriptionId \
    --command "$command";


# Get Ingress Load Balancer IP to Create DNS Record in Azure    
ingressIp=$(kubectl get service ingress-nginx-controller --namespace ingress-controller --output jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "INGRESS_DNS_IP=$ingressIp"

az network dns record-set a add-record --resource-group $DnsZoneResourceGroup \
  --ttl 30 --zone-name $AzureDnsZone \
  --record-set-name $appEndPointPrefix \
  --ipv4-address $ingressIp;


# Cert Manager cluster issuer needs ACME record to validate dns zone via identity profile

az extension add --name aks-preview

cluster_oidc_url=$(az aks show --name $clusterName --resource-group $resourceGroupName --query "oidcIssuerProfile.issuerUrl" -o tsv 2>/dev/null)
echo "oidcissuerurl=$cluster_oidc_url"

federated_identity=$(az identity federated-credential create \
  --name "cert-manager-$clusterName" \
  --identity-name "$userIdentityName" \
  --resource-group $DnsZoneResourceGroup \
  --issuer "$cluster_oidc_url" \
  --subject "system:serviceaccount:cert-manager:cert-manager" 1>/dev/null)


# # Create cluster issuer
command="cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: $letEncryptEmail
    privateKeySecretRef:
      name: letsencrypt
    solvers:
    - dns01:
        azureDNS:
          subscriptionID: $subscriptionId
          resourceGroupName: $DnsZoneResourceGroup
          hostedZoneName: $AzureDnsZone
          environment: AzurePublicCloud
          managedIdentity:
            clientID: $(az identity show --name "${userIdentityName}"  --resource-group $DnsZoneResourceGroup --query 'clientId' -o tsv)
EOF"

# # Deploy cluster Issuer
az aks command invoke \
    --name $clusterName \
    --resource-group $resourceGroupName \
    --subscription $subscriptionId \
    --command "$command";
