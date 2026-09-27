# ACM applications demo

Public GitOps sources for the retail and payments demonstrations on OpenShift.

| Application path | Purpose |
| --- | --- |
| `retail/overlays/development` | Retail development deployment |
| `retail/overlays/production` | Retail production deployment |
| `retail/overlays/mobility` | Retail workload portability deployment |
| `payments` | Payments team application |
| `retail-orders` | [Three-tier storefront, orders API and persistent PostgreSQL](retail-orders/README.md) |

Argo CD ApplicationSets consume these paths on `main`. ACM Placements choose the destination clusters. Namespaces, governance policies, registration and credentials are prepared separately by the platform.

## Validate

```sh
oc kustomize retail/overlays/development > /tmp/retail-development.yaml
oc kustomize retail/overlays/production > /tmp/retail-production.yaml
oc kustomize retail/overlays/mobility > /tmp/retail-mobility.yaml
oc kustomize payments > /tmp/payments.yaml
```

Images are pinned by digest in the manifests and require access to `registry.access.redhat.com`. Application source is mounted through a ConfigMap; no image build or private registry credentials are required for the retail demo.

Keep this repository public for anonymous GitOps access. Never commit kubeconfigs, tokens, cloud credentials, pull secrets, or generated Secrets. Cluster-specific destination selection and patches belong in the platform's ApplicationSets.
