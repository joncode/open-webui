#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
K8S_BASE="$REPO_ROOT/k8s/base"
BUILD_HASH=$(git -C "$REPO_ROOT" rev-parse --short HEAD)

echo "==> Building jaco:${BUILD_HASH}..."
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

echo "==> Importing image into k3s containerd..."
docker save jaco:latest | sudo k3s ctr images import -

echo "==> Applying k8s manifests..."
sudo kubectl apply -f "$K8S_BASE/namespace.yaml"
# Secret is created imperatively — do NOT apply the template here
# See: kubectl -n jaco create secret generic jaco-secret --from-literal=...
sudo kubectl apply -f "$K8S_BASE/jaco-configmap.yaml"
sudo kubectl apply -f "$K8S_BASE/redis-deployment.yaml"
sudo kubectl apply -f "$K8S_BASE/redis-service.yaml"

echo "==> Waiting for Redis..."
sudo kubectl -n jaco rollout status deployment/redis --timeout=60s

sudo kubectl apply -f "$K8S_BASE/jaco-pvc.yaml"
sudo kubectl apply -f "$K8S_BASE/jaco-deployment.yaml"
sudo kubectl apply -f "$K8S_BASE/jaco-service.yaml"
sudo kubectl apply -f "$K8S_BASE/jaco-ingress.yaml"

echo "==> Restarting jaco deployment to pick up new image..."
sudo kubectl -n jaco rollout restart deployment/jaco

echo "==> Waiting for rollout (up to 10 minutes for first boot)..."
sudo kubectl -n jaco rollout status deployment/jaco --timeout=600s

echo "==> Deploy complete!"
echo "    Build hash: ${BUILD_HASH}"
echo "    Pods:"
sudo kubectl -n jaco get pods -o wide
