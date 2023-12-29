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
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz"


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
    --set nodeSelector.\"kubernetes\.io/os\"=linux"


az aks command invoke \
    --name $clusterName \
    --resource-group $resourceGroupName \
    --subscription $subscriptionId \
    --command "$command";

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
    - http01:
        ingress:
          class: nginx
          podTemplate:
            spec:
              nodeSelector:
                "kubernetes.io/os": linux
EOF"

# # Deploy cluster Issuer
az aks command invoke \
    --name $clusterName \
    --resource-group $resourceGroupName \
    --subscription $subscriptionId \
    --command "$command";


command="kubectl create namespace swirl";
# # Create application Namespace
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
