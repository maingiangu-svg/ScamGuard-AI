#!/usr/bin/env bash
# Deploy ScamShield Forensic lên Google Cloud Run
# Yêu cầu: gcloud CLI đã login + project đã bật Cloud Run & Artifact Registry
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-YOUR_GCP_PROJECT_ID}"
REGION="${GCP_REGION:-asia-southeast1}"
SERVICE="scamshield-forensic"

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "❌ Thiếu GEMINI_API_KEY. Chạy: export GEMINI_API_KEY=your_key"
  exit 1
fi

echo "🚀 Deploying to Cloud Run (project=$PROJECT_ID, region=$REGION)..."

gcloud config set project "$PROJECT_ID"

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY},RATE_LIMIT_PER_MINUTE=15" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --port 8080

echo "✅ Done! URL:"
gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)'
