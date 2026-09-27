# Retail Orders / Fieldnotes

A three-tier OpenShift GitOps workshop application: a storefront, a Python orders API and PostgreSQL on a 1Gi persistent volume. Synthetic products/orders only; no payment processing or personal information. The app has no authentication and is intended for a temporary workshop, not production.

## Deploy from the UI

Prerequisites: OpenShift with an available default storage class, OpenShift GitOps in `openshift-gitops`, permission to create the dedicated namespace/project, and access to the registries and PyPI endpoints listed below. These defaults target the hub itself; it is still a central Argo CD **push** deployment. Deploying to a spoke requires a corresponding project destination and separately prepared target permissions/connectivity.

1. In the **hub OpenShift console → + → Import YAML**, create the two documents in [platform/prerequisites.yaml](platform/prerequisites.yaml). They create only namespace `retail-orders-demo` and AppProject `retail-orders`. The namespace's managed-by label lets the OpenShift GitOps operator prepare controller permissions in that namespace. Confirm its controller RoleBinding appears before synchronization.
2. Through **+ → Import YAML**, create [platform/application.yaml](platform/application.yaml). It creates an Argo CD Application in `openshift-gitops`, with manual sync. It is not an ApplicationSet and does not select destinations through ACM Placement.
3. Open **ACM → Applications**, find `retail-orders`, and follow its Argo CD link. If ACM discovery lags, open the existing Argo CD console and select the Application directly.
4. Review source and destination, then **Sync → Synchronize**, leaving prune disabled. Watch the resource tree and sync waves; wait for Synced / Healthy.
5. Open **hub → Networking → Routes → retail-orders-demo → retail-orders → Location**. Add products and confirm a demo order. Open Order history and Platform view.

For an Argo CD creation form, use:

| Field | Value |
| --- | --- |
| Application name / project | `retail-orders` / `retail-orders` |
| Repository URL | `https://github.com/rh-aelgendy/acm-applications-demo.git` |
| Revision / path | `main` / `retail-orders` |
| Destination server | `https://kubernetes.default.svc` |
| Destination namespace | `retail-orders-demo` |
| Sync | Manual, prune disabled |

## What to show

- **One Application, many objects:** ConfigMaps, Services, Deployments, StatefulSet, PVC, Route, network policies, service accounts, bootstrap RBAC and a transient sync Job.
- **Ordered readiness:** bootstrap ConfigMaps/RBAC → credential hook → database/storage/network → API → storefront. The API's readiness checks the database; liveness does not depend on it.
- **Credentials outside Git:** the hook creates `orders-db-credentials` using a random password and preserves it on later syncs. It never logs the password. Do not show Secret YAML. The hook's service account can get that named Secret and create Secrets only in this dedicated namespace; runtime pods have no mounted API token.
- **Real writes:** the API validates products/quantities and computes prices server-side. An order UUID provides retry idempotency; reuse with a different basket is rejected.
- **Persistence:** after an order is confirmed, delete only the orders-api Pod through the cluster console. Wait for readiness; order history should still contain the order. Database Pod recreation also reuses the same PVC, with a brief single-database outage. Do not delete the PVC to test persistence.

## Images, dependencies and network

Images are pinned by digest in `base/resources.yaml`. Python uses public Red Hat UBI; PostgreSQL uses the public **upstream SCLorg CentOS Stream** image, not a claim of a supported Red Hat database product. Allow `registry.access.redhat.com`, `quay.io` and their blob/CDN endpoints.

The API init container installs wheel-only dependencies from `pypi.org` / `files.pythonhosted.org`, pinned with hashes in `base/requirements.txt`. It requires outbound HTTPS on first pod startup. For disconnected/production use, build a reviewed image with these dependencies instead. No runtime image build is required for this demo.

NetworkPolicies default-deny ingress and egress, then allow router → storefront → API → database. DNS is allowed for the frontend/API; API HTTPS egress is allowed for dependency bootstrap and remains an explicit lab exception. The bootstrap Job can reach the Kubernetes API over HTTPS. PostgreSQL has no external Route or node port. In-cluster application/database traffic is not encrypted; this is a bounded workshop design, not production security architecture.

Kustomize uses the cluster's default storage class. PVC capacity is 1Gi; provider minimum allocation/billing can be larger. Azure disk and compute charges apply while deployed. The PostgreSQL StatefulSet has one replica: this demonstrates persistence, not HA, backup, DR or cross-cluster data mobility.

## Clean up after the workshop

1. Delete the `retail-orders` Argo Application **without cascading deletion**; it must stop reconciling first. With the supplied YAML it has no resource-deletion finalizer. In Argo CD choose non-cascading deletion if prompted.
2. Confirm the Application is absent. In the hub console delete **only** project/namespace `retail-orders-demo`. This intentionally deletes the sample orders, PVC, generated Secret and all application resources. Confirm the PVC's storage class reclaim policy before expecting the cloud disk to disappear.
3. Delete only AppProject `retail-orders` in namespace `openshift-gitops` through API Explorer. Do not delete the GitOps namespace or existing projects.

Deleting the Application alone does not delete data. Re-syncing preserves credentials and orders. A completely fresh demo requires the namespace/PVC cleanup above before importing the prerequisites again.

## Developer validation

```sh
oc kustomize retail-orders
python3 -m pip install --require-hashes -r retail-orders/base/requirements.txt
python3 -m unittest discover -s retail-orders/tests
```

Never commit generated Secrets, kubeconfigs, tokens, local state or test credentials.
