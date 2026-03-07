# CLAUDE.md

This is the GitOps deployment repo for **${{ values.name }}** (`${{ values.componentId }}`).
It contains a Helm chart that ArgoCD uses to deploy the service into each environment.

The application source repo is at `idp/${{ values.teamName }}/${{ values.componentId }}`.

## Common Helm commands

```bash
# Validate chart and catch template errors
helm lint . -f values.yaml -f environments/homelab.yaml

# Render all templates to stdout (dry-run)
helm template ${{ values.componentId }} . -f values.yaml -f environments/homelab.yaml

# Dry-run against a live cluster
helm upgrade --install ${{ values.componentId }} . \
  -f values.yaml -f environments/homelab.yaml \
  --namespace ${{ values.componentId }} --dry-run
```

## Environment overlay pattern

`values.yaml` holds base configuration. Per-environment overrides in `environments/<env>.yaml` are
merged on top at deploy time. Only `image.tag` is written by CI — everything else is managed here.

Image tag update (executed by the CI pipeline in the app repo on each push to `main`):
```bash
yq -i ".image.tag = \"${CI_COMMIT_SHORT_SHA}\"" environments/${ENVIRONMENT}.yaml
```

Environments and their ArgoCD source branches:

| Environment file                | Cluster env   | ArgoCD branch | Hostname                        |
| ------------------------------- | ------------- | ------------- | ------------------------------- |
| `environments/homelab.yaml`     | `homelab`     | `development` | `<hostname>.k8s.home.rottlr.de` |
| `environments/development.yaml` | `development` | `development` | `<hostname>.dev.idp.rottlr.de`  |
| `environments/production.yaml`  | `production`  | `production`  | `<hostname>.prod.idp.rottlr.de` |

## ESO image-pull secret

`templates/image-pull-secret.yaml` syncs registry credentials from Vault via the `vault-backend`
ClusterSecretStore. The Vault path is:

```
idp/${{ values.teamName }}/${{ values.componentId }}/image-pull-secret
```

The secret must contain three keys: `registry`, `username`, `password`.

## Health endpoints

The liveness and readiness probe paths are configured in `values.yaml`:

- Liveness: `/api/v1/health/live`
- Readiness: `/api/v1/health/ready`

## Adding environment variables

Add static env vars to the `env` list in `templates/deployment.yaml`.
For secret values, add an `ExternalSecret` in `templates/` and reference it via `envFrom`.
