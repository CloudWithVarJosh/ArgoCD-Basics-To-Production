# Argo CD Sync Phases & Hooks Tutorial | Step-by-Step Hands-On

## Video reference for this lecture is the following:

[![Watch the video](https://img.youtube.com/vi/usj6RP6uzUc/maxresdefault.jpg)](https://www.youtube.com/watch?v=usj6RP6uzUc&ab_channel=CloudWithVarJosh)

---
## ⭐ Support the Project  
If this **repository** helps you, give it a ⭐ to show your support and help others discover it! 

---

## Table of Contents

- [Introduction](#-introduction)  
- [Sync Phases & Hooks in Argo CD](#sync-phases--hooks-in-argo-cd)  
  - [What is a sync operation?](#what-is-a-sync-operation)  
- [What are Sync Phases & Hooks](#what-are-sync-phases--hooks)  
  - [What are sync phases?](#what-are-sync-phases)  
  - [What is a hook?](#what-is-a-hook)  
  - [Supported hook types and their behavior](#supported-hook-types-and-their-behavior)  
- [How hooks are defined, executed, cleaned up, and used](#how-hooks-are-defined-executed-cleaned-up-and-used-with-real-examples)  
  - [Core behavior](#core-behavior)  
  - [Phase-based hooks](#phase-based-hooks)  
  - [What resources can be used as hooks](#what-resources-can-be-used-as-hooks-and-when-to-use-them)  
  - [Hook execution and failure semantics](#hook-execution-and-failure-semantics)  
- [Canonical hook usage patterns](#canonical-hook-usage-patterns-production-realistic-job-examples)  
  - [1. PreSync hook – blocking prerequisite enforcement](#1-presync-hook--blocking-prerequisite-enforcement)  
    - [Why PreSync is different from init containers](#why-presync-is-different-from-init-containers)  
    - [PreSync-only use cases](#presync-only-use-cases-init-containers-cannot-do-these)  
  - [2. Skip hook – disabling an existing hook](#2-skip-hook--disabling-an-existing-hook)  
  - [3. SyncFail hook – failure capture and alerting](#3-syncfail-hook--failure-capture-and-alerting)  
  - [4. Sync hook – deliberately absent (and why)](#4-sync-hook--deliberately-absent-and-why)  
  - [5. Skip hook – dev-only Ingress](#5-skip-hook--dev-only-ingress)  
  - [6. PostDelete hook – external resource cleanup](#6-postdelete-hook--external-resource-cleanup)  
  - [Hook cleanup (mandatory in production)](#hook-cleanup-mandatory-in-production)  
- [**Demo:** Sync Hooks in Argo CD](#demo-sync-hooks-in-argo-cd-presync-postsync-skip)  
  - [Step 0: What we are demonstrating](#step-0-what-we-are-demonstrating-context)  
  - [Step 0.5: Build and push container images](#step-05-build-and-push-container-images-prerequisite)  
  - [Step 1: Create a dedicated namespace](#step-1-create-a-dedicated-namespace)  
  - [Step 2: Create a PreSync hook](#step-2-create-a-presync-hook-backend-preparation)  
  - [Step 3: Create a PostSync hook](#step-3-create-a-postsync-hook-frontend-validation)  
  - [Step 4: Push manifests to GitHub](#step-4-push-manifests-to-github)  
  - [Step 5: Apply Argo CD Application CRDs](#step-5-apply-argo-cd-application-crds)  
  - [Step 6: Sync the backend application](#step-6-sync-the-backend-application-observe-presync)  
  - [Step 7: Sync the frontend application](#step-7-sync-the-frontend-application-observe-postsync)  
  - [Step 8: Demonstrate Skip hook](#step-8-demonstrate-skip-hook-debugging-scenario)  
- [Final takeaway for learners](#final-takeaway-for-learners)  
- [Conclusion](#-conclusion)  
- [References](#-references)  

---

## Introduction

Argo CD implements GitOps through a **control-plane–driven reconciliation model**, where desired state stored in Git is continuously compared against live cluster state.
While this model is fundamentally declarative, real production deployments often require **controlled procedural steps** during application lifecycle events.

**Sync Phases and Hooks** provide this control.
They allow operators to introduce **explicit lifecycle checkpoints**, enforce **preconditions**, run **one-time or conditional logic**, handle **failure diagnostics**, and perform **external cleanup**, all without breaking GitOps principles.

This document explains **how sync phases work**, **what hooks really are**, **when each hook type should be used**, and **why certain hooks exist at all**.
The goal is not just correctness, but **operational clarity and production safety**.

---

# Sync Phases & Hooks in **Argo CD**

A sync operation in Argo CD is not a simple “apply manifests” step. It is a **control-plane–driven lifecycle** where Argo CD evaluates desired state from Git, detects drift, and reconciles the cluster to converge fully to that state.

Sync phases and hooks exist to provide **lifecycle control within this sync process**. They allow specific actions to run **before, during, after, or upon failure of a sync**, enabling procedural logic around an otherwise declarative GitOps model.

---

### What is a sync operation?

![Alt text](/images/6a.png)
A **sync operation** is Argo CD’s control-plane action that **applies Git-declared desired state to the Kubernetes cluster**, attempting to make live state match version-controlled intent.

* Argo CD compares desired Git state with live cluster state, detects drift, and computes the exact changes required for reconciliation.
* A successful sync means **all targeted Kubernetes manifests were applied successfully** and accepted by the Kubernetes API server.
* Sync success is based on **apply-time correctness**, not on whether the resulting workloads are running or healthy.
* If any manifest fails to apply due to validation or API errors, the sync **fails immediately** and convergence is not achieved.
* Sync execution and enforcement occur entirely at the **Argo CD control-plane layer**, independent of kubectl usage or manual cluster access.

**Important distinction (Sync vs Health):**

* A sync can succeed even if workloads are **not running correctly**.
* For example, a Deployment YAML may apply successfully while Pods remain in states like `ImagePullBackOff`, `CrashLoopBackOff`, or `Pending`.
* In such cases, **Sync status is Successful**, but **Application Health is not green**.
* The **App Health section in the Argo CD UI** reflects this runtime state and indicates whether deployed resources are Healthy, Degraded, or Progressing.

> **Manual vs automated sync:** Sync phases and hooks behave **identically** for **manual syncs (UI or CLI)** and **automated syncs (Git-triggered)**.
> Hook execution is **independent of the sync trigger** and always evaluated as part of the **same Argo CD reconciliation lifecycle**.

---

## What are Sync Phases & Hooks

### What are sync phases?

![Alt text](/images/6b.png)

Sync phases exist because Kubernetes manifests only describe *what* to deploy, not *when* deployment steps should occur.
They provide Argo CD with **explicit lifecycle checkpoints** where deployment, validation, failure handling, or cleanup logic can be orchestrated.

Sync phases are **named lifecycle stages within an Argo CD operation**, indicating **where Argo CD is in the deployment lifecycle**.

* A successful sync follows the **PreSync → Sync → PostSync** execution path.
* If a sync fails at any point, Argo CD transitions into the **SyncFail** phase.
* **PostDelete** is a separate lifecycle phase triggered during Application deletion, not during sync execution.
* Sync phases act as **execution boundaries** that govern flow; they do not define custom logic themselves.
* The **Sync phase** is where standard Kubernetes resources without hook annotations are applied.
* Sync phases exist **even when no hooks are defined**, ensuring a consistent lifecycle model.

> **Important clarification:**
> Some hooks are **named after sync phases** (for example, `PreSync`, `PostSync`, `SyncFail`), but **hooks and phases are different concepts**.
> Phases define *where Argo CD is* in the lifecycle, while hooks define *what runs* at those points.
> Additionally, some hooks such as `Skip` are **not phases at all**, but behavioral directives.

---

### What is a hook?

![Alt text](/images/6c.png)

A **hook** is a Kubernetes resource (native or custom) that Argo CD **treats specially** to perform actions **around a sync or application lifecycle operation**, instead of reconciling it like a normal workload.

* Hooks are defined **directly inside Kubernetes resource manifests** using annotations, not in Argo CD Application specs.
* Hooks are **not continuously reconciled**; they are evaluated only when their specific condition is met (sync execution, sync failure, or application deletion).
* Hooks are used for **one-time or conditional tasks** such as database migrations, prerequisite validation, smoke tests, diagnostics, or external cleanup.
* Depending on the hook type, failure can **block a sync**, **terminate it**, or run **only after failure or deletion**.

> **Important clarification:**
> Not all hook types represent execution points.
> `Skip` is a **behavioral directive** that prevents a manifest from being applied, and `PostDelete` runs during **Application deletion**, not during sync.

---

### Supported hook types and their behavior

![Alt text](/images/6d.png)

Hooks are Kubernetes resources annotated with **hook names**.
Most hook names align with sync phase names to define *when* they execute, but they remain **hooks**, not phases.
Some hook names, such as `Skip`, are **behavioral overrides** used to disable hook execution and do not represent execution timing.

Reference: [https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)

| Hook Name      | Description                                                                                                                                | Concrete, practical examples                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| **PreSync**    | Executes before any resources are applied. Used for mandatory checks or preparation that must succeed before sync continues.               | Database migrations, validate required Secrets, enforce schema or policy preconditions |
| **Sync**       | Executes during the Sync phase alongside resource application. Exists mainly for edge coordination cases and is rarely needed in practice. | Rarely used; prefer PreSync, PostSync, or Sync Waves instead                           |
| **Skip**       | Disables execution of an already-defined hook without deleting it from Git. Acts as a temporary override, not a lifecycle phase.           | Temporarily disable PostSync smoke tests, pause PreSync migrations during debugging    |
| **PostSync**   | Executes after Sync completes successfully and resources are Healthy. Used to validate end-to-end system behavior.                         | API smoke tests, frontend–backend integration checks                                   |
| **SyncFail**   | Executes immediately when the sync operation fails. Used for failure diagnostics and notifications.                                        | Capture logs, send alerts, persist failure context                                     |
| **PostDelete** | Executes after an Application is deleted. Used to clean up external or non-Kubernetes resources.                                           | Deregister services, delete external data, clean cloud-side dependencies               |

---

> **Important clarification:**
> `Skip` does not define *when* something runs.
> It **replaces an existing hook** to prevent that hook from executing.

> Although `Sync` is a valid hook type, most production workflows rely primarily on **PreSync**, **PostSync**, **SyncFail**, and **PostDelete**.
> Ordering concerns inside the Sync phase are usually better handled using **Sync Waves**, which we will discuss next.

> **Sync phases define *when* Argo CD evaluates resources.**
> **Hooks define *what runs* (or is intentionally disabled) at those points.**
> Together, they turn a sync operation from a blind apply into a **controlled, phase-aware deployment lifecycle**.

---

## How hooks are defined, executed, cleaned up, and used (with real examples)

Hooks are declared **directly on Kubernetes resources** using annotations, which instruct Argo CD to treat the resource differently from a continuously reconciled workload.

```yaml
argocd.argoproj.io/hook: <HookName>
```

### Core behavior

* Hook resources are **not continuously reconciled**
* They are evaluated **only when their triggering lifecycle event occurs**
* Execution may occur **during sync phases, on sync failure, or during application deletion**
* Kubernetes is **unaware of hook semantics** and treats them as normal resources

---

### Phase-based hooks

Phase-based hooks define **when a resource executes** within the sync lifecycle.

Valid phase-based hooks may be combined when needed:

```yaml
argocd.argoproj.io/hook: PreSync,PostSync
```

Used for paired **setup and verification** workflows.

> **Note:** `Skip` is not a lifecycle hook phase.
> It is a behavioral directive that disables execution entirely.
> `Skip` must not be combined with phase-based hooks like PreSync or PostSync.

---

### What resources can be used as hooks (and when to use them)

Argo CD hooks are defined using Kubernetes manifests.
Any Kubernetes resource (native or custom) can be treated as a hook when annotated appropriately, but real-world usage follows clear patterns:

* **Kubernetes Jobs** – most commonly used and recommended in practice
  Clear completion semantics make success or failure unambiguous.
* **Kubernetes Pods** – limited, lightweight usage
  Suitable for simple, non-retryable, fire-and-forget actions.
* **Any Kubernetes manifest** – technically supported
  Rarely used due to lack of clear completion semantics.
* **Argo Workflows** – advanced use cases
  Used for multi-step automation, retries, and orchestration.
* **Custom Resources (CRDs)** – controller-dependent
  Viable only when the CRD exposes meaningful status conditions.

---

### Hook execution and failure semantics

During a sync operation:

* Hooks execute **strictly in sync phase order**
* Each hook **must complete successfully** before the next phase begins
* Hook failure **fails the entire sync immediately**
* Hooks are **not retried automatically** unless a new sync is triggered

This design prevents uncontrolled retries and ensures **deterministic, fail-fast deployments**.

---

### Canonical hook usage patterns (production-realistic Job examples)



### 1. PreSync hook – blocking prerequisite enforcement

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: app1-presync-prerequisites
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: precheck
          image: busybox
          command:
            - sh
            - -c
            - |
              echo "Validating deployment prerequisites..."
              test -n "$DB_HOST"
              echo "PreSync checks passed"
```

**Purpose**

* Runs **before any application resources are applied**
* Blocks deployment if mandatory prerequisites are missing
* Used for config validation, environment readiness, policy enforcement
* Ensures **no previous Job with the same name exists** before re-running

**Why `BeforeHookCreation` here matters**

* Argo CD does **not** overwrite existing Jobs with the same name
* If a previous hook Job is still present, the new sync can fail unexpectedly
* `BeforeHookCreation` guarantees a **clean slate** before the hook runs

This is critical when:

* Hooks are re-run frequently
* Job names are static
* Idempotency must be enforced

---

### Why PreSync is different from init containers

PreSync hooks and init containers are often compared because both run “before the application starts,” but they operate at **different layers of the system**.

* A PreSync hook runs at the **GitOps control-plane level**, before Argo CD applies any Kubernetes resources, which means **Pods do not exist yet**.
* It executes **once per sync operation** and can **block the entire deployment cleanly** if it fails, preventing any resource creation.
* Init containers run **inside individual Pods**, execute **per Pod start or restart**, and cannot stop other resources from being created once a sync has begun.

This difference makes PreSync suitable for **global, rollout-level decisions**, while init containers are limited to **Pod-local preparation tasks**.

---

### PreSync-only use cases (init containers cannot do these)

PreSync hooks can enforce **cluster or environment safety checks** before Argo CD **implements any change or implementation in the cluster**, such as:

* Blocking a change or implementation when the target cluster is **PROD** but the change is not approved.
* Blocking a change or implementation if the **Kubernetes version is below a required minimum**.
* Blocking a change or implementation when **required CRDs are missing** in the cluster.

In these scenarios, init containers are ineffective because Pods already exist by the time they run, side effects have already occurred, and failures result in repeated retries.
With PreSync, **no change or implementation is applied**, execution stops immediately at the control-plane level, and the failure remains **clean, global, and controlled**.

---

### 2. Skip hook – disabling an existing hook

A **Skip hook** is used to **disable an already-defined hook** without deleting the manifest from Git.
It only makes sense when a **phase-based hook (PreSync, Sync, PostSync, etc.) already exists**.

Conceptually, `Skip` means:

> “This resource is a hook, but do not execute it.”

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: frontend-smoke-test
  namespace: app1-ns
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
    argocd.argoproj.io/hook: Skip
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: test
        image: curlimages/curl
        command:
          - sh
          - -c
          - |
            echo "Running frontend smoke test..."
            curl -f http://frontend-svc:80
```

**Purpose**

* Represents a **PostSync hook that is intentionally disabled**
* Keeps hook intent and logic **visible in Git**
* Prevents execution without deleting the hook definition

**How to read this correctly (critical)**

* `PostSync` defines **what kind of hook this is**
* `Skip` instructs Argo CD **not to execute it**
* The hook **exists conceptually**, but is **not run**
* This is useful for demos, debugging, or temporarily pausing hooks

> Think of `Skip` as a **disable switch**, not a standalone hook type.

---

### 3. SyncFail hook – failure capture and alerting

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: app1-syncfail-diagnostics
  annotations:
    argocd.argoproj.io/hook: SyncFail
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: diagnostics
          image: busybox
          command:
            - sh
            - -c
            - |
              echo "Sync failed. Capturing diagnostic context..."
              date
              echo "Recording failure metadata"
```

**Purpose**

* Executes **only when a sync operation fails**
* Used for alerts, log capture, external notifications
* Runs after failure, so it does not gate anything further

This improves **mean-time-to-debug**, not deployment correctness.

---

### 4. Sync hook – deliberately absent (and why)

You will notice there is **no Sync hook example here**.

That is intentional.

> After reviewing real-world patterns, I could not find a legitimate production use-case where a **Sync hook** is clearly better than **PreSync**, **PostSync**, or **Sync Waves**.

In almost every scenario:

* Preconditions belong in **PreSync**
* Outcome validation belongs in **PostSync**
* Ordering belongs in **Sync Waves**

If *you* have a Sync hook use-case where none of the above are a better fit,
I’m genuinely **all ears** 🙂

---

### 5. Skip hook – dev-only Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app1-dev-only-ingress
  annotations:
    argocd.argoproj.io/hook: Skip
spec:
  rules:
    - host: app1-dev.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app1-backend
                port:
                  number: 80
```

**Purpose**

* Prevents this manifest from **ever being applied**
* Keeps shared templates in a single repo
* Makes exclusions **explicit and intentional**

> **Important:**
> `Skip` is not a lifecycle phase.
> It is a **behavioral directive** that removes a manifest from sync entirely.

---

### 6. PostDelete hook – external resource cleanup

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: app1-postdelete-cleanup
  annotations:
    argocd.argoproj.io/hook: PostDelete
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: cleanup
          image: busybox
          command:
            - sh
            - -c
            - |
              echo "Application deleted. Cleaning external resources..."
              echo "Removing database entries"
              sleep 5
              echo "Cleanup completed"
```

**Purpose**

* Runs **after the Application is deleted**
* Handles **non-Kubernetes cleanup**
* Prevents orphaned external resources

> **Key distinction:**
> `PostDelete` does **not** run during sync.
> It runs during the **Application deletion lifecycle**.

---

### Hook cleanup (mandatory in production)

By default, hook resources **remain in the cluster after execution**.
Cleanup behavior must be defined explicitly:

```yaml
argocd.argoproj.io/hook-delete-policy
```

Common policies:

* `HookSucceeded` – delete hook after success
* `HookFailed` – delete hook after failure
* `BeforeHookCreation` – remove previous hook before re-run

Defining delete policies is a **production requirement** to prevent clusters from filling up with completed Jobs.

---

## Demo: Sync Hooks in Argo CD (PreSync, PostSync, Skip)

In this demo, we will **intentionally and visually observe** how **PreSync**, **PostSync**, and **Skip** hooks behave during a sync operation.

All Application CRDs, application code, and Kubernetes manifests used here are part of the **GitHub notes for this lecture**.
You can refer to them alongside the demo to see the full repository structure.

**Pre-Requisite**
Before starting this demo, ensure the following:

* Argo CD is installed and running
* Argo CD API server is accessible

If you need installation steps, refer to:
[https://github.com/CloudWithVarJosh/ArgoCD-Basics-To-Production/tree/main/02-Arch-Install](https://github.com/CloudWithVarJosh/ArgoCD-Basics-To-Production/tree/main/02-Arch-Install)

Enable port-forwarding:

```bash
kubectl port-forward service/my-argo-cd-argocd-server -n argocd 8080:443
```

---

## Step 0: What we are demonstrating (context)

We will show:

* **PreSync hook**
  Runs **before any manifests are applied**
* **PostSync hook**
  Runs **after manifests are applied and resources are Healthy**
* **Skip hook**
  Used to **temporarily disable a hook** without deleting it from Git

We are intentionally **not enabling auto-sync**, so that hook execution and cleanup are clearly visible in the UI.

---

## Step 0.5: Build and push container images

To keep this demo **focused on Argo CD sync hooks**, we will use **simple container images** built locally and pushed to Docker Hub.

The **application code, Dockerfiles, and Kubernetes manifests** are all provided as part of the **GitHub notes for this lecture**.
You are expected to **reuse the same structure**.

---

**Frontend image**

```bash
cd app1-frontend
docker build -t cloudwithvarjosh/app1-frontend:v1.0.0 .
docker push cloudwithvarjosh/app1-frontend:v1.0.0
```

---

**Backend image**

```bash
cd app1-backend
docker build -t cloudwithvarjosh/app1-backend:v1.0.0 .
docker push cloudwithvarjosh/app1-backend:v1.0.0
```

---

**Important notes (read carefully)**

* **Dockerfiles and source code** are already present in the GitHub notes
  You do **not** need to write them from scratch.
* The manifests in the repository **default to the `cloudwithvarjosh` Docker Hub account**
* You are expected to:

  * Use **your own Docker Hub account**
  * Push images under **your namespace**
  * Update the Deployment manifests to point to **your image repository**
* Docker Desktop is **already logged in** on the demo machine
* On Linux VMs, run `docker login` before pushing images

---

## Step 1: Create a dedicated namespace

```bash
kubectl apply -f app1-ns.yaml
```

### Why this step matters

* It is a **best practice** to isolate application resources using namespaces
* In this demo, **all namespace-scoped resources for app1** (Jobs, Pods, Services, Deployments) live in `app1-ns`
* This makes hook behavior easier to observe and reason about

---

## Step 2: Create a PreSync hook (backend preparation)

**File:** `app1-backend-config/presync-hook.yaml`

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: presync-db-migration
  namespace: app1-ns
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migrate
        image: busybox
        command:
          - sh
          - -c
          - |
            echo "Running DB migrations..."
            echo "Migration completed successfully."
```

### What this PreSync hook does

* Runs **before Argo CD applies any manifests**
* Simulates a **database migration or prerequisite check**
* If this Job fails, **the entire sync is blocked**

### Why this lives in `app1-backend-config`

* Database migrations and schema preparation are **backend concerns**
* PreSync hooks should live **next to the component they protect**
* This mirrors real production repo layouts

### Important limitation (call this out explicitly)

> **PreSync hooks cannot depend on Services or Pods**,
> because **those resources do not exist yet**.

If your logic requires runtime dependencies:

* Use **PostSync hooks**
* Or application-level mechanisms like readiness probes or initContainers

---

## Step 3: Create a PostSync hook (frontend validation)

**File:** `app1-frontend-config/postsync-hook.yaml`

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: frontend-smoke-test
  namespace: app1-ns
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: test
        image: curlimages/curl
        command:
          - sh
          - -c
          - |
            echo "Running frontend smoke test..."
            curl -f http://frontend-svc:80
```

### What this PostSync hook does

* Runs **after all manifests are applied**
* Runs **only if resources are Healthy**
* Sends a **real HTTP request** to the frontend Service
* Failure marks the sync as **unsuccessful**

### Why this lives in `app1-frontend-config`

* Smoke testing and availability checks are **frontend responsibilities**
* This keeps hook ownership aligned with component ownership

---

## Step 4: Push manifests to GitHub

At this point, your Git repository contains:

* Namespace manifest
* Backend manifests + PreSync hook
* Frontend manifests + PostSync hook
* Application CRDs for backend and frontend

Commit and push all changes to Git.

---

## Step 5: Apply Argo CD Application CRDs

Apply the Application definitions for backend and frontend.

```bash
kubectl apply -f app1-backend-application.yaml
kubectl apply -f app1-frontend-application.yaml
```

### Important setup choice

* **Auto-sync is intentionally disabled**
* This allows us to:

  * Manually trigger syncs
  * Observe hook execution
  * Watch hooks get deleted after success

---

## Step 6: Sync the backend application (observe PreSync)

In the Argo CD UI:

```
Applications → app1-be-app → Sync
```

### What you should observe

* PreSync Job is created **before any backend manifests**
* Job runs successfully
* Job is **automatically deleted** due to:

  ```yaml
  argocd.argoproj.io/hook-delete-policy: HookSucceeded
  ```
* Only after PreSync completes does Argo CD apply backend resources

This shows:

> **PreSync gates the entire sync.**

---

## Step 7: Sync the frontend application (observe PostSync)

In the Argo CD UI:

```
Applications → app1-fe-app → Sync
```

### What you should observe

* Frontend Deployments and Services are applied first
* Argo CD waits until resources are Healthy
* PostSync Job is created **after rollout**
* Smoke test runs
* Job is deleted after success

### Access the application (optional verification)

```bash
kubectl port-forward -n app1-ns svc/frontend-svc 8081:80
```

Open `http://localhost:8081` in the browser.

---

## Step 8: Demonstrate Skip hook (debugging scenario)

Now we’ll **disable the PostSync hook** without deleting it.

Edit the PreSync hook manifest and add:

```yaml
argocd.argoproj.io/hook: Skip
```

Commit and push the change.


When a hook is marked as `Skip`, it **still exists in Git and is fully recognized by Argo CD**, but it is **not executed at all**. No Job or Pod is created, and no hook logic runs during the sync.
This is especially useful during troubleshooting or debugging, when you want to temporarily bypass validation or potentially destructive actions without deleting or commenting out YAML. By replacing the hook phase with `Skip`, execution is disabled intentionally while keeping the hook definition visible, auditable, and easy to re-enable later.


---

## Conclusion

Sync phases and hooks transform Argo CD from a **blind apply engine** into a **phase-aware deployment controller**.
Phases establish *where* Argo CD is in the lifecycle, while hooks define *what should happen* at those points.

Used correctly, hooks enable **safe rollouts**, **clean failure handling**, and **explicit lifecycle control** without drifting away from GitOps principles.
Used incorrectly, they can introduce hidden complexity and procedural sprawl.

The key takeaway is simple:

* Use **PreSync** for global, gating conditions
* Use **PostSync** for validation and verification
* Use **SyncFail** for diagnostics and alerting
* Use **PostDelete** for external cleanup
* Use **Skip** intentionally, never accidentally

Everything else belongs to **Sync Waves**, which address ordering concerns inside the Sync phase and are intentionally covered separately.

---

## References

* Argo CD Official Documentation – Sync Phases and Hooks
  [https://argo-cd.readthedocs.io/en/stable/user-guide/sync-phases-hooks/](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-phases-hooks/)

* Argo CD Hook Delete Policies
  [https://argo-cd.readthedocs.io/en/stable/user-guide/resource_hooks/](https://argo-cd.readthedocs.io/en/stable/user-guide/resource_hooks/)

* Argo CD Application Lifecycle
  [https://argo-cd.readthedocs.io/en/stable/operator-manual/applications/](https://argo-cd.readthedocs.io/en/stable/operator-manual/applications/)

* Kubernetes Jobs
  [https://kubernetes.io/docs/concepts/workloads/controllers/job/](https://kubernetes.io/docs/concepts/workloads/controllers/job/)

* GitOps Principles
  [https://opengitops.dev/](https://opengitops.dev/)

---

