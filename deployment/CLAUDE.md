# CLAUDE.md

This is the GitOps deployment repo for **${{ values.name }}** (`${{ values.componentId }}`).
It contains a Helm chart that ArgoCD uses to deploy the service into each environment.

The application source repo is at `idp/${{ values.teamName }}/${{ values.componentId }}`.

## What the chart renders

The chart renders a single `idp.rottler.io/v1alpha1` **WebService** custom resource
(`templates/webservice.yaml`). The Crossplane composition behind that CR produces the
Deployment, Service, Gateway API HTTPRoute, image-pull ExternalSecret, ServiceMonitor and
PodDisruptionBudget — the platform owns everything a developer should not have to wire up.

Config that is identical across environments (image repository, port, compute tier, hostname,
static env) is hard-coded in `templates/webservice.yaml`; only per-environment values
(`environment`, `image.tag`, `scaling`) live in `values.yaml` and the overlays.

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

## Image-pull secret

The platform-standard group pull secret is plumbed by the composition automatically; the chart
no longer carries an `image-pull-secret.yaml`. The Vault path
(`idp/platform/argocd/idp-group-pull-secret`) and registry are composition concerns now.

## Health endpoints

Liveness `/api/v1/health/live` and readiness `/api/v1/health/ready` are the WebService XRD
golden-path defaults — the same paths this app serves — so they are not set in this chart.
Override them only for non-conforming apps by adding a `healthChecks` block to the WebService
spec in `templates/webservice.yaml`.

## Adding environment variables

Add static, non-secret vars directly to the `env` map in `templates/webservice.yaml`; config
that is identical across environments is hard-coded there, not in `values.yaml`. `ENVIRONMENT`
is injected from the per-environment `environment` value. For secret values, add an `envFrom`
entry to the WebService spec — either `secretRef` for an existing in-namespace Secret, or
`vaultPath` + `name` to have the composition create the ExternalSecret.
