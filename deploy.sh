#!/usr/bin/env bash
set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────
PROJECT="studied-sled-487417-m2"
REGION="europe-west1"
DOCKER_USER="artemnikov"

BACKEND_SERVICE="online-pixel-dungeon"
BACKEND_IMAGE="${DOCKER_USER}/online-pixel-dungeon"
BACKEND_PORT=8080
SERVICE_ACCOUNT="cloudrun-runtime@${PROJECT}.iam.gserviceaccount.com"

FRONTEND_SERVICE="frontend"
FRONTEND_IMAGE="${DOCKER_USER}/frontend"
FRONTEND_PORT=8080

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION=$(grep '"version"' "$ROOT_DIR/frontend/package.json" | head -1 | sed 's/.*"\([0-9.]*\)".*/\1/')
echo "Version: $VERSION"

# Resolve backend URL (uses existing service URL)
BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" \
  --project="$PROJECT" --region="$REGION" \
  --format='value(status.url)')

# ── Build ───────────────────────────────────────────────────────────
echo "── Building backend ──"
docker build -t "$BACKEND_IMAGE:$VERSION" -t "$BACKEND_IMAGE:latest" "$ROOT_DIR/backend"

echo "── Building frontend ──"
docker build -t "$FRONTEND_IMAGE:$VERSION" -t "$FRONTEND_IMAGE:latest" "$ROOT_DIR/frontend"

# ── Push ────────────────────────────────────────────────────────────
echo "── Pushing backend ──"
docker push "$BACKEND_IMAGE:$VERSION"
docker push "$BACKEND_IMAGE:latest"

echo "── Pushing frontend ──"
docker push "$FRONTEND_IMAGE:$VERSION"
docker push "$FRONTEND_IMAGE:latest"

# ── Deploy (no traffic yet) ────────────────────────────────────────
echo "── Deploying backend ──"
gcloud run deploy "$BACKEND_SERVICE" \
  --image="$BACKEND_IMAGE:$VERSION" \
  --project="$PROJECT" --region="$REGION" \
  --service-account="$SERVICE_ACCOUNT" \
  --port="$BACKEND_PORT" \
  --no-traffic

echo "── Deploying frontend ──"
gcloud run deploy "$FRONTEND_SERVICE" \
  --image="$FRONTEND_IMAGE:$VERSION" \
  --project="$PROJECT" --region="$REGION" \
  --service-account="$SERVICE_ACCOUNT" \
  --port="$FRONTEND_PORT" \
  --set-env-vars="VITE_API_URL=${BACKEND_URL}" \
  --no-traffic

# ── Route traffic ───────────────────────────────────────────────────
echo "── Routing traffic ──"
gcloud run services update-traffic "$BACKEND_SERVICE" \
  --project="$PROJECT" --region="$REGION" --to-latest
gcloud run services update-traffic "$FRONTEND_SERVICE" \
  --project="$PROJECT" --region="$REGION" --to-latest

echo "── Done ── v${VERSION} deployed"
