# Template for secrets - DO NOT COMMIT with real values
# Use kubeseal to create sealed-secrets.yaml:
#   kubeseal --cert ~/starnode-core/pub-sealed-secrets.pem \
#     --format yaml < secrets.yaml > sealed-secrets.yaml
#
# DATABASE_URL format: postgresql+asyncpg://argent:<password>@postgres-prd-rw.databases.svc:5432/argent
apiVersion: v1
kind: Secret
metadata:
  name: argent-secrets
  namespace: argent-prd
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://argent:CHANGE_ME@postgres-prd-rw.databases.svc:5432/argent"
  SECRET_KEY: "CHANGE_ME_GENERATE_SECURE_KEY"
  RESEND_API_KEY: "re_CHANGE_ME"
  GEMINI_API_KEY: "CHANGE_ME"
