# Dispatch Desk — placement-driven portability

A two-service delivery-quote application with the message **One platform. Run anywhere.** A frontend calls an internal quote engine. The page highlights the deployment location and actual cluster, while keeping workshop mechanics in this guide. The same regional 3 kg quote returns €14 on either cluster. There is no database, session store, PVC, Azure SDK, or AAP dependency.

## Objective and boundaries

Use ACM Placement and OpenShift GitOps to deploy on one cluster, expand to two, scale pods, then retire the source after validating the destination. Two ARO clusters illustrate cloud and on-premises roles; they do not prove an actual on-premises migration. Each cluster has its own endpoint. This lab does not promise a stable public URL, traffic draining, state migration, or zero downtime.

The app uses a digest-pinned public `registry.access.redhat.com/ubi9/python-312` image and Python standard library only. No build, pip download or registry credentials are needed. OpenShift Routes and restricted security contexts are assumed. Generated ConfigMap hashes roll the application when code changes.

## Short customer demo — 5–7 minutes

After preparation, use this flow. Sync is automatic: there is no manual Argo CD sync step.

1. **Today: Azure.** Open the cloud application Route. Show the Azure deployment location and calculate a Regional, 3 kg quote: €14. State the new business requirement to move it on-premises.
2. **Expand:** in ACM → Infrastructure → Clusters → destination → Labels, add the same label to the destination. Keep cloud selected.
3. **Verify:** in ACM Applications inspect `dispatch-desk`. Search `kind:Application namespace:openshift-gitops` for the generated destination Application and wait for Synced/Healthy. Open the destination endpoint, calculate the same quote, and verify its cluster identity. Stop if this fails.
4. **Retire Azure:** after verifying the destination Route shows On-premises and the same quote, remove only the dispatch label from the cloud cluster. Its generated Application and owned app resources disappear. Verify a fresh destination quote still succeeds. This is deliberate stateless source retirement, not a traffic or data migration.
5. **Reset:** select cloud again, wait for readiness and a successful quote, then deselect the destination. The namespace and facilitator permissions remain for reuse.

Say: “The business needs the application in another location. ACM selects that destination; GitOps deploys the same application automatically. We validate it, then retire the old deployment.” Both clusters in the rehearsal are ARO; the on-premises role is simulated. Keep replica scaling as an optional extension, not part of the short story.

The visible location comes from `DEPLOYMENT_LOCATION`, configured in the ApplicationSet's Kustomize patch. This example maps `aro-hcp-spoke` to Azure and `local-hub-aro` to the simulated On-premises role; other clusters default to OpenShift. Adapt this explicit map for your environment. Edge is a possible demonstration role, not a deployed third location. Never mistake the display role for discovered physical infrastructure. Prices are synthetic; the app stores no orders or persistent data.

Use actual Routes for the customer presentation. A private Route requires a browser on a connected network. A local tunnel is a rehearsal aid only; do not describe localhost as a cloud endpoint.

## Facilitator preparation — once per fleet

1. Have two Available ManagedClusters, each registered with the hub's Argo CD through GitOpsCluster. ACM import alone does not grant Argo deployment access. Use the actual ManagedCluster identifiers, not their display names.
2. Check the installed schemas for Placement, ManagedClusterSetBinding, ApplicationSet and AppProject. The examples use the same served API versions as the existing demo; discover and validate them on a new environment before applying.
3. Use the `default` ManagedClusterSet and its binding in `openshift-gitops`, or edit the example for your existing set. Reuse the shared binding; do not replace or delete it. `platform/clusterset-binding.example.yaml` is only for a missing binding after confirming access.
4. On **each cluster**, use **+ → Import YAML** for `platform/namespace.yaml`. This creates only the dedicated `acm-demo-dispatch` namespace. Confirm it has no unrelated resources. Review and import `platform/gitops-rbac.yaml` on each cluster: it grants namespaced application permissions to the existing `acm-demo-gitops` managed service account and the hub GitOps controller. Adapt these subjects if your registration uses different identities. Ensure the registered Argo identity may manage ConfigMaps, Services, Deployments and Routes in it. The application deliberately cannot create namespaces or cluster-scoped resources.
5. Review `platform/hub.yaml`. Confirm the ApplicationSet controller service-account name in its RoleBinding matches the installation. The project restricts resources and namespace; the fleet boundary is the chosen ClusterSet and label selector. No IAM or Azure credentials are involved.
6. Validate both bundles client-side and server-side before importing the hub bundle. Namespace existence is required for server validation. Initially neither cluster should have `demo.acm.example.com/dispatch=true`, so no Application is generated.

```sh
oc kustomize dispatch-desk/base > /tmp/dispatch-desk.yaml
oc --context HUB apply --dry-run=client -f dispatch-desk/platform/hub.yaml
oc --context HUB apply --dry-run=server -f dispatch-desk/platform/hub.yaml
oc --context TARGET -n acm-demo-dispatch apply --dry-run=client -f /tmp/dispatch-desk.yaml
oc --context TARGET -n acm-demo-dispatch apply --dry-run=server -f /tmp/dispatch-desk.yaml
```

Replace HUB/TARGET with real authenticated contexts. Repeat target checks for both clusters. Use `oc api-resources` and `oc explain` for API discovery; a failed validation is a stop condition, not permission to bypass validation. Import the reviewed hub bundle with the hub console's **+ → Import YAML**. Cluster-scoped changes are limited to the dedicated namespace on each cluster and the managed-cluster labels used below.

## Presenter walkthrough — 12–15 minutes

For the cloud-to-on-premises story, call the HCP cluster **source/cloud** and the other cluster **destination/simulated on-premises**. You can reverse the roles. Write down the actual names before starting.

| Step and UI action | Expected evidence / speaking point | Fallback |
| --- | --- | --- |
| 1. ACM → Infrastructure → Clusters → source → Labels. Add `demo.acm.example.com/dispatch=true`. | Placement `dispatch-desk` selects the source. In ACM Applications / Argo CD, `dispatch-desk-<source>` becomes Synced and Healthy. “One approved application definition, deployed by placement.” | Inspect PlacementDecision, registration and Application conditions; do not advance while unhealthy. |
| 2. Source console → Networking → Routes → project `acm-demo-dispatch` → dispatch-desk → Location. Calculate a regional, 3 kg quote. | €14 and the real source cluster/pod. “The application tells us where it ran.” | For private ingress use the facilitator port-forward below. Do not expose the private cluster publicly. |
| 3. ACM → Infrastructure → Clusters → destination → Labels. Add the same label, leaving the source selected. | PlacementDecision lists both clusters; a second Application becomes Healthy. Open its endpoint and repeat the quote. Same result, different cluster. “Expand before retiring the source.” | Keep the source selected if destination health or access fails. |
| 4. ACM → Search → query `kind:ApplicationSet namespace:openshift-gitops` → `openshift-gitops/dispatch-desk` → YAML. In `spec.template.spec.source.kustomize.replicas`, change quote-engine `count: 1` to `count: 3`. | Both Applications reconcile; each selected cluster has three Ready quote-engine pods. “Replica scaling is distinct from adding another cluster.” | Inspect Argo diff/sync events. Do not edit the generated Application or live Deployment; controllers restore them. Restore count 1 after demonstrating. |
| 5. Explain the new residency requirement, verify the destination quote, then remove the dispatch label from the source in ACM. | Source Application and its owned workloads are deleted; destination remains Healthy. “ACM selects the destination; GitOps retires the old stateless deployment.” | If destination validation fails, do not deselect source. To recover after removal, re-add the label and wait for redeployment. This is not instantaneous traffic rollback. |
| 6. Show destination's fresh quote and source Deployments list. | Only destination serves this deployment; source's dedicated namespace remains. No data or traffic migration is claimed. | Use ACM Search and Argo resource status if browser access is unavailable; label it deployment evidence, not successful request evidence. |

**Deletion behavior is deliberate:** `preserveResourcesOnDeletion: false` makes removal from the Placement cascade through the generated Application to its owned resources. `prune: true` also removes resources deleted from Git. Only this stateless app's dedicated namespace is in scope. Never use this behavior for persistent applications without a data-lifecycle design. Inspect generated Application finalizers before relying on retirement; if deletion stalls, inspect errors rather than removing finalizers blindly.

The template is platform-owned and editable in the UI for this workshop. In production, version its changes in a platform Git repository and use the normal review workflow. This lab's destination label is a presenter control, not a compliance certification. A production residency policy needs protected labels, RBAC and an independently verified eligibility source.

## Private ingress access

Preparation may use a temporary local tunnel with an authenticated context for the target cluster:

```sh
oc --context TARGET -n acm-demo-dispatch port-forward service/dispatch-desk 18080:8080 --address=127.0.0.1
```

Open `http://127.0.0.1:18080`; use port 18081 for the second cluster. The workstation must reach and authenticate to the target API (for example through approved private connectivity). If it cannot, present deployment evidence only until access is prepared. This tunnel is a viewing aid, not a production traffic solution, and uses no new public route or ACM proxy token. Stop it with Ctrl+C after the session.

## Reset / teardown

Reset through the same UI: select source again, wait for Healthy and a successful quote, then deselect destination; restore both replica counts to 1. To tear down, deselect both clusters and wait for both Applications and workloads to disappear. Delete only this module's ApplicationSet, Placement, AppProject, ConfigMap, Role and RoleBinding from `platform/hub.yaml`. Delete `acm-demo-dispatch` on each cluster only after checking it contains no unrelated resources. Keep the shared ClusterSet binding, GitOps registration and existing demos.

## Validation

Status: live rehearsal passed on 2026-10-05 using ACM 2.17 on the existing ARO fleet. Both targets accepted strict client/server dry-runs. Automatic deployment, identical €14 quotes with distinct cluster identities, three Ready engine replicas per cluster, source retirement and return to cloud-only were exercised. The application UI was checked in the browser. Other fleets still need their own preparation and validation.

```sh
python3 -m unittest discover -s dispatch-desk/tests
oc kustomize dispatch-desk/base
```

Local tests and Kustomize rendering are not proof of successful deployment. Record server validation, two-cluster readiness, quote responses, scaling, retirement and reset during rehearsal before presenting this as tested on your fleet.
