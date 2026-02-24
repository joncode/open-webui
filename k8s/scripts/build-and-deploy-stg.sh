#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
K8S_STG="$REPO_ROOT/k8s/staging"
BUILD_HASH=$(git -C "$REPO_ROOT" rev-parse --short HEAD)

echo "==> [STAGING] Building jaco:${BUILD_HASH}..."
cd "$REPO_ROOT"

# Build the Docker image (no Ollama, no CUDA, full build with embedding models)
docker build \
  --build-arg USE_OLLAMA=false \
  --build-arg USE_CUDA=false \
  --build-arg USE_SLIM=false \
  --build-arg BUILD_HASH="${BUILD_HASH}" \
  -t jaco:latest \
  -t "jaco:${BUILD_HASH}" \
  .

echo "==> [STAGING] Importing image into k3s containerd..."
docker save jaco:latest | sudo k3s ctr images import -

echo "==> [STAGING] Applying k8s manifests..."
sudo kubectl apply -f "$K8S_STG/namespace.yaml"
# Secret is created imperatively — do NOT apply the template here
# See: kubectl -n jaco-stg create secret generic jaco-secret --from-literal=...
sudo kubectl apply -f "$K8S_STG/jaco-configmap.yaml"
sudo kubectl apply -f "$K8S_STG/redis-deployment.yaml"
sudo kubectl apply -f "$K8S_STG/redis-service.yaml"

echo "==> [STAGING] Waiting for Redis..."
sudo kubectl -n jaco-stg rollout status deployment/redis --timeout=60s

sudo kubectl apply -f "$K8S_STG/jaco-pvc.yaml"
sudo kubectl apply -f "$K8S_STG/jaco-deployment.yaml"
sudo kubectl apply -f "$K8S_STG/jaco-service.yaml"
sudo kubectl apply -f "$K8S_STG/jaco-ingress.yaml"

echo "==> [STAGING] Restarting jaco deployment to pick up new image..."
sudo kubectl -n jaco-stg rollout restart deployment/jaco

echo "==> [STAGING] Waiting for rollout (up to 10 minutes for first boot)..."
sudo kubectl -n jaco-stg rollout status deployment/jaco --timeout=600s

echo "==> [STAGING] Deploy complete!"
echo "    Build hash: ${BUILD_HASH}"
echo "    Pods:"
sudo kubectl -n jaco-stg get pods -o wide
