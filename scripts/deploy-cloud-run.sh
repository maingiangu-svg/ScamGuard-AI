#!/usr/bin/env bash
# Deploy ScamShield Forensic lên Google Cloud Run
# Yêu cầu: gcloud CLI đã login + project đã bật Cloud Run & Artifact Registry
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-YOUR_GCP_PROJECT_ID}"
REGION="${GCP_REGION:-asia-southeast1}"
SERVICE="${GCP_SERVICE:-scamguard-ai}"

if [ "$PROJECT_ID" = "YOUR_GCP_PROJECT_ID" ]; then
  echo 'Set GCP_PROJECT_ID to the intended project before deploying.'
  exit 1
fi

if [ ! -f "ml_model/models/model_bundle.pkl" ]; then
  echo "Train ml_model/train.py before deployment; the complete local model bundle is required."
  exit 1
fi

echo "🚀 Deploying to Cloud Run (project=$PROJECT_ID, region=$REGION)..."

gcloud run deploy "$SERVICE" \
  --project "$PROJECT_ID" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "PYTHON_EXECUTABLE=python,RATE_LIMIT_PER_MINUTE=15,RATE_LIMIT_TOTAL_PER_MINUTE=60,SCAMGUARD_TRUSTED_PROXY_HOPS=0" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --concurrency 1 \
  --timeout 30 \
  --startup-probe 'httpGet.path=/api/health,httpGet.port=8080,initialDelaySeconds=5,periodSeconds=10,timeoutSeconds=5,failureThreshold=12' \
  --liveness-probe 'httpGet.path=/api/health,httpGet.port=8080,initialDelaySeconds=10,periodSeconds=30,timeoutSeconds=5,failureThreshold=3' \
  --port 8080

echo "✅ Done! URL:"
gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format 'value(status.url)'
