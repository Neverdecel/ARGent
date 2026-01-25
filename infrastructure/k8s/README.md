# ARGent K3s Deployment

Deploy ARGent to the Starnode K3s cluster using Flux GitOps.

## Target Configuration

- **Domain**: `argent.neverdecel.com`
- **Image**: `ghcr.io/neverdecel/argent:main-YYYYMMDD-HHMMSS-<sha>`
- **Namespace**: `argent-prd`

## Prerequisites

- Access to Starnode K3s cluster
- `kubectl` configured with cluster access
- `kubeseal` installed
- Access to `pub-sealed-secrets.pem` certificate

## Database Setup

Create the `argent` database in the existing `postgres-prd` CNPG cluster:

```bash
# Connect to postgres pod
kubectl exec -it postgres-prd-1 -n databases -- psql -U postgres

# Run these SQL commands:
CREATE DATABASE argent;
CREATE USER argent WITH PASSWORD 'your-secure-password-here';
GRANT ALL PRIVILEGES ON DATABASE argent TO argent;
\c argent
GRANT ALL ON SCHEMA public TO argent;
```

## Sealed Secrets Setup

### 1. Create Application Secrets

```bash
cd infrastructure/k8s/prd

# Copy template and fill in real values
cp secrets.yaml.tpl secrets.yaml
# Edit secrets.yaml with actual values

# Seal the secrets
kubeseal --cert ~/starnode-core/pub-sealed-secrets.pem \
  --format yaml < secrets.yaml > sealed-secrets.yaml

# Clean up plaintext (IMPORTANT!)
rm secrets.yaml
```

### 2. Create GHCR Image Pull Secret

```bash
# Generate the dockerconfigjson
# Replace USERNAME and PAT with your GitHub credentials
AUTH=$(echo -n "USERNAME:ghp_xxxxxxxxxxxx" | base64)
CONFIG=$(echo -n "{\"auths\":{\"ghcr.io\":{\"auth\":\"$AUTH\"}}}" | base64)

# Create the secret yaml
cat > ghcr-creds.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: ghcr-creds-prd
  namespace: argent-prd
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: $CONFIG
EOF

# Seal it
kubeseal --cert ~/starnode-core/pub-sealed-secrets.pem \
  --format yaml < ghcr-creds.yaml > sealed-image-pull-secret.yaml

# Clean up
rm ghcr-creds.yaml
```

## Deployment to Starnode Core

Copy the prd directory to the starnode-core repository:

```bash
# In starnode-core repo
mkdir -p clusters/core/apps/argent
cp -r /path/to/argent/infrastructure/k8s/prd clusters/core/apps/argent/

# Add to main kustomization
# Edit clusters/core/apps/kustomization.yaml and add:
#   - argent/prd

# Commit and push
git add clusters/core/apps/argent
git commit -m "Add ARGent production deployment"
git push
```

## Verification

After pushing to starnode-core:

```bash
# Force reconciliation
flux reconcile kustomization flux-system --with-source

# Check deployment status
kubectl get pods -n argent-prd
kubectl get svc -n argent-prd
kubectl get ingress -n argent-prd

# Check logs
kubectl logs -f -n argent-prd -l app=argent

# Verify image automation
flux get image repository -n argent-prd
flux get image policy -n argent-prd

# Test health endpoint
curl https://argent.neverdecel.com/health
```

## Run Database Migrations

After the first deployment:

```bash
POD=$(kubectl get pods -n argent-prd -l app=argent -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n argent-prd $POD -- alembic upgrade head
```

## Environment Variables

### ConfigMap (non-sensitive)

| Variable | Value |
|----------|-------|
| ENVIRONMENT | production |
| DEBUG | false |
| BASE_URL | https://argent.neverdecel.com |
| EMAIL_ENABLED | true |
| SMS_ENABLED | false |
| WEB_INBOX_ENABLED | true |
| ALLOW_WEB_ONLY_REGISTRATION | true |

### Secrets (sealed)

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| SECRET_KEY | Application secret key |
| RESEND_API_KEY | Resend email service API key |
| GEMINI_API_KEY | Google Gemini AI API key |

## Troubleshooting

```bash
# Check pod events
kubectl describe pod -n argent-prd -l app=argent

# Check sealed secret controller
kubectl logs -n kube-system -l name=sealed-secrets-controller

# Check Flux image automation
flux logs --kind=ImageRepository -n argent-prd
flux logs --kind=ImagePolicy -n argent-prd
```
