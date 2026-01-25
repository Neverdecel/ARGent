# Template for GHCR image pull secret - DO NOT COMMIT with real values
# Use kubeseal to create sealed-image-pull-secret.yaml:
#   kubeseal --cert ~/starnode-core/pub-sealed-secrets.pem \
#     --format yaml < ghcr-creds.yaml > sealed-image-pull-secret.yaml
#
# To create the base64 dockerconfigjson:
#   echo -n '{"auths":{"ghcr.io":{"auth":"BASE64_OF_USERNAME:PAT"}}}' | base64
#
# Where BASE64_OF_USERNAME:PAT is: echo -n "username:ghp_xxxx" | base64
apiVersion: v1
kind: Secret
metadata:
  name: ghcr-creds-prd
  namespace: argent-prd
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: CHANGE_ME_BASE64_ENCODED_DOCKER_CONFIG
