# deploy/

This directory is **gitignored** (except this README). It holds environment-specific deployment manifests.

## Convention

When you fork this repo, create your own deployment config here:

- `k8s/` — Kubernetes manifests (Deployment, Service, ConfigMap)
- `compose/` — Docker Compose overrides for your environment

The application is configured entirely via environment variables documented in `.env.example`.

## Example k8s deployment

```bash
kubectl apply -f deploy/k8s/
```
