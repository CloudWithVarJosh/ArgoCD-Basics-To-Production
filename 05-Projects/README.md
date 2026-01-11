# Argo CD Projects Explained | Production-Grade GitOps Guardrails, RBAC & Hands-On Demo

## Video reference for this lecture is the following:

---
## ⭐ Support the Project  
If this **repository** helps you, give it a ⭐ to show your support and help others discover it! 

---

## Table of Contents

* [Introduction](#introduction)  
* [Why Argo CD Projects?](#why-argo-cd-projects)  
* [What is an Argo CD Project](#what-is-an-argo-cd-project)  
* [Correct mental model](#correct-mental-model)  
* [What Projects control (production scope)](#what-projects-control-production-scope)  
* [What is the default Argo CD Project?](#what-is-the-default-argo-cd-project)  
* [Demo: Working with AppProject](#demo-working-with-appproject)  
  * [What are we going to do?](#what-are-we-going-to-do)  
  * [Pre-requisites](#pre-requisites)  
  * [Step 1: Repository layout (important context)](#step-1-repository-layout-important-context)  
  * [Step 2: Create the namespace](#step-2-create-the-namespace)  
  * [Step 3: Create the AppProject (guardrails first)](#step-3-create-the-appproject-guardrails-first)  
  * [Step 4: Create Argo CD Applications (frontend and backend)](#step-4-create-argo-cd-applications-frontend-and-backend)  
  * [Step 5: Build and push container images](#step-5-build-and-push-container-images)  
  * [Step 6: Populate config repositories](#step-6-populate-config-repositories)  
  * [Step 7: Verify deployment](#step-7-verify-deployment)  
  * [Step 8: Access the application](#step-8-access-the-application)  
  * [Step 9: Policy enforcement and RBAC testing](#step-9-policy-enforcement-and-rbac-testing-intentional-failure-scenarios)  
* [Critical note (please do not skip)](#critical-note-please-do-not-skip)  
* [Conclusion](#conclusion)  
* [References](#references)  

---

## Introduction

In earlier lectures, we worked exclusively with the **default Argo CD Project** to focus on core GitOps mechanics such as Applications, sync, and reconciliation. While this approach simplifies learning, it does **not reflect real-world Argo CD usage**.

In production environments, Argo CD is rarely used in a flat, unrestricted manner. As the number of Applications grows and multiple teams begin sharing the same Argo CD instance and Kubernetes clusters, **explicit governance boundaries** become mandatory.

This lecture introduces **Argo CD Projects**, the construct that enables teams to define **guardrails, ownership, access control, and safety guarantees** before any Application is allowed to deploy. You will learn not just *what* Projects are, but *why* they exist, *how* they are enforced, and *how they fit into a production-grade GitOps workflow*.

---

# Projects in Argo CD

Up to this point, all demos in the course have been using the **default Argo CD project**. This was intentional to delay governance concepts while focusing on core GitOps mechanics, but it does **not** reflect how Argo CD is used in production environments.

As environments grow beyond a single application, Argo CD requires an explicit way to **define boundaries, ownership, and safety guarantees** across Applications.

Argo CD **Projects** are the construct that provide this control.

---

## Why Argo CD Projects?

As Argo CD usage grows beyond a single application, certain limitations start to appear **when no explicit governance boundaries exist**.

* **Unrestricted source repositories:** Any Application can reference manifests from any Git repository, making it easy to deploy from the wrong repo, a fork, or an unreviewed source.
  **Example:** An Application points to a developer’s fork instead of the approved organization repository and deploys unreviewed YAML to the cluster.

* **Uncontrolled deployment destinations:** Applications can deploy to any cluster and any namespace known to Argo CD, increasing the risk of accidental cross-environment or cross-team deployments.
  **Example:** A workload intended for the `dev` environment is accidentally deployed into the `prod` cluster due to a misconfigured destination.

* **No resource-level safety:** Git changes can introduce cluster-scoped or privileged resources such as RBAC objects or CRDs without guardrails, creating risk of privilege escalation.
  **Example:** A commit adds a `ClusterRoleBinding` granting broad permissions, and Argo CD applies it without restriction.

* **Lack of application-level RBAC:** Anyone with Argo CD access can operate any Application, regardless of team ownership or responsibility boundaries.
  **Example:** A frontend developer triggers a sync or deletes a backend Application owned by another team.

  > **Note on Kubernetes RBAC vs Argo CD RBAC:**
  > Kubernetes RBAC can be used to control **who can interact with Argo CD CRDs** such as `Application`, `ApplicationSet`, and `AppProject`, and which Kubernetes verbs (`get`, `create`, `update`, `delete`) are allowed on them. You can verify these CRDs and supported verbs using `kubectl api-resources -o wide | grep -i argo`.
  >
  > However, Kubernetes RBAC has **no concept of GitOps operations** such as application sync, rollback, refresh, pruning, enabling auto-sync, or terminating ongoing operations. These actions are not Kubernetes API verbs; they are Argo CD–specific behaviors. Because Argo CD performs deployments using its own service account, Kubernetes RBAC never evaluates the end user for these operations. This is why **Kubernetes RBAC cannot replace Argo CD RBAC**. Kubernetes RBAC controls access to Kubernetes objects, while Argo CD RBAC controls **who can operate GitOps** at the application and project level.

* **Single-tenant behavior by default:** All Applications effectively share the same trust and permission model, which does not scale for multiple teams or environments.
  **Example:** A misconfiguration in one team’s Application affects other unrelated Applications running on the same Argo CD instance.

These challenges do not appear immediately, but they become unavoidable as:

* the number of Applications increases,
* multiple teams share the same Argo CD instance,
* and production safety becomes a requirement.

This is the problem space that Argo CD Projects are designed to solve.

> **Note on scale:**
> These challenges may not feel significant when managing 10–20 microservices. At small scale, teams can rely on tribal knowledge, conventions, and manual discipline to keep things under control.
> As environments grow to **hundreds or thousands of microservices**, often shared across multiple teams and environments, these same gaps quickly turn into **operational and security nightmares**. What felt optional early on becomes a hard requirement for safe, predictable GitOps at scale.

---

## What is an Argo CD Project

An **Argo CD Project** is a **control-plane level construct**, enforced entirely by Argo CD, and is not part of the Kubernetes runtime model.

* **Argo CD–scoped construct:** Defined as an Argo CD field and enforced by the Argo CD controller, independent of Kubernetes RBAC, namespaces, or runtime permissions.

* **Not a namespace:** Does not create, isolate, or scope Kubernetes resources; namespaces continue to handle runtime isolation, quotas, and network boundaries.

* **Evaluated before reconciliation:** Project rules are validated before any Application is reconciled, making Projects a pre-sync enforcement layer rather than a runtime safety net.

This distinction matters because Kubernetes and Argo CD operate at different layers:

* Kubernetes namespaces solve **runtime isolation and access control**.
* Argo CD Projects solve **GitOps governance and policy enforcement**.

Argo CD Projects are not just conceptual groupings. They are **first-class Kubernetes objects**, defined and managed declaratively.

They are implemented as a CRD:

* Kind: `AppProject`
* API Group: `argoproj.io`

You can confirm this directly from the cluster:

```bash
kubectl api-resources | grep -i argo
```

Expected output:

```text
applications      app,apps       argoproj.io/v1alpha1   true   Application
applicationsets   appset          argoproj.io/v1alpha1   true   ApplicationSet
appprojects       appproj         argoproj.io/v1alpha1   true   AppProject
```

This confirms that Projects:

* Are declarative GitOps objects.
* Can be version-controlled like Applications.
* Are auditable, reviewable, and enforceable by Argo CD itself.

> **Note on ownership and ordering:**
> In production GitOps setups, **AppProjects are created and applied first** to establish governance boundaries. These are typically **owned and managed by platform or Kubernetes administrators**. **Application CRDs are created only after the Project exists** and are validated against its rules. In many teams, **developers are allowed to manage Application YAMLs**, but only within the **constraints enforced by the Project**. This **separation of duties** enables safe, scalable GitOps without relying on manual reviews.

---

## Correct mental model

Think of an **AppProject as a GitOps guardrail**, not just as a grouping mechanism.

* Grouping Applications is incidental; enforcement is the primary purpose.
* Guardrails are applied before sync, not after resources are created.
* Any violation blocks reconciliation entirely.

When an Application violates Project rules:

* Argo CD marks the Application as invalid.
* Synchronization does not proceed.
* Even Kubernetes cluster-admin privileges cannot bypass Project enforcement.

---

## What Projects control (production scope)

Projects define **hard GitOps boundaries** that every Argo CD Application must satisfy **before sync begins**.

* **Trusted source repositories:** Only explicitly allowed Git repositories can be referenced by Applications, preventing deployments from forks, personal repos, wrong organizations, or accidentally copied manifests.

* **Deployment destinations:** Projects restrict which Kubernetes clusters and namespaces Applications may deploy into, ensuring workloads cannot escape intended environments or cross team boundaries.

* **Allowed Kubernetes resource kinds:** Projects explicitly allow or deny resource types such as Deployments, Services, CRDs, DaemonSets, NetworkPolicies, or RBAC objects, preventing privilege escalation or cluster-wide impact through Git.

* **Application-level RBAC:** Projects define Argo CD RBAC, not Kubernetes RBAC, controlling who can view Applications, trigger syncs, enable pruning, perform rollbacks, or delete Applications, typically mapped to OIDC groups or JWT claims.

* **Organization and multi-tenancy:** Projects provide the primary mechanism to safely run multiple teams and applications on a shared Argo CD instance and shared clusters while preserving ownership and operational isolation.

---

## What is the default Argo CD Project?

Every Argo CD Application belongs to **exactly one Project**. If a Project is not explicitly specified, the Application is automatically assigned to the **default project**.

In all demos so far:

* Applications used the default project.
* Things worked because the default project allows everything.

This was intentional early on, as it helped focus on basic GitOps mechanics without introducing governance.

The default project:

* Is created automatically when Argo CD is installed.
* Cannot be deleted.
* Is intentionally permissive.

By default, it allows:

* Any source Git repository.
* Any destination cluster registered with Argo CD.
* Any namespace.
* Any Kubernetes resource kind.

Effectively, Applications using the default project can deploy **anything, anywhere**.

You can verify this in the Argo CD UI:

```
Argo CD UI → Settings → Projects → default
```

You will see `*` configured for both source repositories and destinations, indicating no restrictions.

This behavior is useful for:

* Initial learning and experimentation.
* Quick proofs of concept.

However, it does not scale beyond simple setups.

As we move forward and introduce:

* Multiple Applications,
* Multiple repositories,
* Orchestration, ordering, and ownership boundaries,

Applications **must be explicitly tied to the correct Project**.
Relying on the default project is no longer acceptable or safe.

Although the default project can technically be modified, production setups should:

* Leave the default project untouched.
* Create explicit Projects with clearly defined permissions and boundaries.

This ensures governance is intentional, visible, and enforced.

Projects therefore form the **foundation** for everything that follows: multi-application setups, orchestration, sync ordering, RBAC, and safe GitOps at scale.

---

# Demo: Working with AppProject (2-Tier Application)

## What are we going to do?

In this demo, we will work with a simple **two-tier application (`app1`)** consisting of a **frontend** and a **backend**, as shown in the attached diagram.

Both tiers are intentionally lightweight Flask applications running as Kubernetes workloads. The application itself is **not the focus** of this demo. Instead, the diagram highlights the **end-to-end GitOps flow**, from defining guardrails to enforcing application state.

The goal of this demo is to make the following ideas concrete:

* **Guardrails come first** – AppProjects are defined before any Applications exist.
* **Applications inherit constraints** – every frontend and backend Application is evaluated against the Project.
* **Git declares, Kubernetes reconciles** – desired state is committed to Git and enforced automatically.
* **Policy enforcement is intentional** – we will later trigger failures to prove that RBAC and guardrails are real.

As reflected in the diagram, we will move step-by-step from:

* defining **repository and ownership boundaries**,
* preparing a **runtime boundary (namespace)**,
* creating the **AppProject (policy and governance)**,
* deploying frontend and backend Applications,
* and finally **verifying reconciliation and enforcement**.

This mirrors how AppProjects are used in **real production GitOps setups**, where governance is established first and applications are allowed to operate **only within those boundaries**.

---

## Pre-requisites

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

## Step 1: Repository layout (important context)

From previous lectures, we already know one fundamental GitOps principle:

**Application code and application configuration must live in separate repositories.**

Before we start creating repositories for this demo, let’s pause briefly and look at the **repository patterns used for a 2-tier application (frontend + backend)**, as shown in the diagram above.

The diagram highlights **three common patterns** seen in real-world GitOps setups:

* **2 repositories:** Simple setups where frontend and backend share lifecycle and governance boundaries.
* **3 repositories:** Growing setups with separate build pipelines per tier but shared GitOps configuration.
* **5 repositories:** Mature setups with strong separation of duties, smallest blast radius per change, and centralized GitOps governance.

As organizations grow, the number of repositories increases **not because of complexity**, but because of ownership boundaries, security requirements, blast-radius control, and platform governance.

---

## Repository pattern used in this demo

For this demo, we will intentionally use the **5-repository pattern**, because it best represents **production-grade GitOps**, even though the application itself is simple. This pattern allows us to demonstrate AppProjects as platform guardrails, clear separation between application teams and platform teams, and how Argo CD scales beyond toy examples.

Concretely, we will work with **five repositories**:

* **Two code repositories**, one for frontend and one for backend. These contain only application source code, Dockerfiles, and build-related concerns, and they do not include Kubernetes manifests or any Argo CD configuration.

* **Two configuration repositories**, again one for frontend and one for backend. These define what runs in the cluster and typically contain Kubernetes manifests along with the Argo CD Application CRD for the respective tier. They represent **runtime desired state**, not build logic.

* **One platform repository**, owned by the platform or GitOps team. This stores Argo CD–specific governance objects such as AppProject definitions, GitOps guardrails, and onboarding boundaries that apply to the entire application.

The platform repository is separate because:

* `AppProject` is a **Kubernetes CRD**, not application configuration.
* It belongs to the **application boundary (app1)** rather than to frontend or backend individually.
* It must be version-controlled, reviewed, and audited independently.

This mirrors real production setups where platform teams define guardrails first and application teams deploy strictly within those boundaries.

---


### Create the following public repositories

Create the following repositories now, but **do not add any files yet**:

* `app1-frontend-config`
* `app1-backend-config`
* `argocd-platform-config`

In the next step, we will start with the **platform repository**, define the AppProject guardrails, and only then move on to creating application-level resources.

This ordering is intentional and mirrors how GitOps is done in production.

> **Note on demo simplifications:**
> To keep this demo focused and fast, we will use **public Git repositories**, assume that **application code already exists locally**, and **build and push container images locally**. This avoids interrupting the core GitOps flow with authentication setup.
>
> Configuration of **private Git repositories**, **private container registries**, and credentials (repo secrets, image pull secrets, sync, prune, self-heal) has already been covered in detail earlier. If you want to revisit that, refer to:
> [https://github.com/CloudWithVarJosh/ArgoCD-Basics-To-Production/tree/main/04-PrivateRepo%2BSyncPruneSelfHeal](https://github.com/CloudWithVarJosh/ArgoCD-Basics-To-Production/tree/main/04-PrivateRepo%2BSyncPruneSelfHeal)

---


## Step 2: Create the namespace

Create the namespace:

```bash
kubectl create namespace app1-ns
```

Verify the namespace:

```bash
kubectl get ns app1-ns
```

> **Note:**
> For this demo, we are creating the namespace manually to keep the focus on **AppProjects and RBAC**. In production setups, namespace creation and other prerequisites are typically automated and orchestrated using **sync waves and hooks**, which we will cover in a later lecture.

---

## Step 3: Create the AppProject (guardrails first)

In production GitOps setups:

* **Projects are always created first**
* They define what applications are allowed to do
* Applications that violate project rules are rejected immediately

We will now create an AppProject for `app1`.

### Create `app1-appproj.yaml`

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: app1-project
  namespace: argocd
spec:
  description: Project for App1 frontend and backend workloads

  sourceRepos:
    - https://github.com/CloudWithVarJosh/app1-frontend-config.git
    - https://github.com/CloudWithVarJosh/app1-backend-config.git

  destinations:
    - namespace: app1-*
      server: https://kubernetes.default.svc

  clusterResourceWhitelist:
    - group: ""
      kind: Namespace

  namespaceResourceWhitelist:
    - group: apps
      kind: Deployment
    - group: ""
      kind: Service
    - group: ""
      kind: ConfigMap
    - group: ""
      kind: Secret

  clusterResourceBlacklist:
    - group: rbac.authorization.k8s.io
      kind: ClusterRole
    - group: rbac.authorization.k8s.io
      kind: ClusterRoleBinding

  roles:
    - name: dev-readonly
      description: Read-only access for developers
      policies:
        - p, proj:app1-project:dev-readonly, applications, get, app1-project/*, allow
      groups:
        - app1-devs

    - name: platform-admin
      description: Full control for platform team
      policies:
        - p, proj:app1-project:platform-admin, applications, *, app1-project/*, allow
      groups:
        - platform-team
```

### Understanding `app1-appproj.yaml` (line by line)

This AppProject defines **hard GitOps guardrails** for everything related to `app1`.
Nothing outside these rules can be deployed, even if an Application CRD exists.

---

### API metadata

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
```

This declares an **Argo CD–specific CRD**, not a native Kubernetes resource.

* Managed entirely by Argo CD
* Enforced before any Application reconciliation
* Evaluated at the control-plane level

This confirms we are defining **governance**, not workload state.

---


```yaml
metadata:
  name: app1-project
  namespace: argocd
```

* `name`: Logical boundary for all app1-related Applications
* `namespace`: Must be `argocd` because Argo CD watches Projects there

All Applications that reference `project: app1-project` will be evaluated against this object.

> **Note on Project naming and strategy:**
> In real production environments, Project names often vary based on **environment strategy and governance model**, not just application boundaries. You may see Projects named `app1-dev-project`, `app1-prod-project`, or even shared Projects like `dev-project` or `prod-project`.
>
> This is intentional. Once you understand that Projects are not just about segregation, but also about **RBAC, guardrails, and access patterns**, it becomes clear that multiple applications may share the same Project. For example, if all development workloads follow identical access rules and restrictions, a single Project may govern all dev-related Applications. Broaden your imagination beyond one-Project-per-app; Projects model **policy boundaries**, not just application names.

---


### Project description

```yaml
description: Project for App1 frontend and backend workloads
```

Purely informational, but important in production.

* Helps operators quickly identify ownership
* Appears in Argo CD UI and CLI
* Useful when dozens of projects exist

Descriptions matter at scale.

---

### Source repository restrictions

```yaml
sourceRepos:
  - https://github.com/CloudWithVarJosh/app1-frontend-config.git
  - https://github.com/CloudWithVarJosh/app1-backend-config.git
```

This is the **first and strongest security boundary**.

What this enforces:

* Applications in this project can **only** reference these Git repositories
* Any Application pointing elsewhere is rejected before sync

What this prevents:

* Deployments from forks or personal repos
* Accidental cross-application repo usage
* Malicious or unreviewed manifests entering the cluster

Even Argo CD admins cannot bypass this without modifying the Project itself.

---

### Deployment destinations

```yaml
destinations:
  - namespace: app1-*
    server: https://kubernetes.default.svc
```

This restricts **where** Applications are allowed to deploy.

* Only the in-cluster Kubernetes API server is allowed
* Only namespaces matching `app1-*` are permitted

Why this matters:

* Prevents accidental deployment into unrelated namespaces
* Prevents deploying app1 workloads into other clusters
* Supports environment patterns like `app1-dev`, `app1-qa`, `app1-prod`

This is namespace governance, enforced at the GitOps layer.

---

### Cluster-scoped resource whitelist

```yaml
clusterResourceWhitelist:
  - group: ""
    kind: Namespace
```

Cluster-scoped resources are **denied by default**.

This explicitly allows:

* Namespace creation via GitOps

Why this is required:

* Namespaces are cluster-scoped
* Without this rule, Argo CD cannot create namespaces
* Namespace creation is a common and safe requirement

Production principle applied here:

> Allow the minimum required cluster-wide capability.

---

### Namespaced resource whitelist

```yaml
namespaceResourceWhitelist:
  - group: apps
    kind: Deployment
  - group: ""
    kind: Service
  - group: ""
    kind: ConfigMap
  - group: ""
    kind: Secret
```

This defines **exactly what workload resources Applications may create**.

Allowed:

* Workloads (`Deployment`)
* Networking (`Service`)
* Configuration (`ConfigMap`, `Secret`)

Everything else:

* StatefulSets
* DaemonSets
* Ingresses
* Jobs
* Custom resources

is **implicitly denied** unless added here.

This turns GitOps into a **policy enforcement mechanism**, not just deployment automation.

---

### Cluster resource blacklist

```yaml
clusterResourceBlacklist:
  - group: rbac.authorization.k8s.io
    kind: ClusterRole
  - group: rbac.authorization.k8s.io
    kind: ClusterRoleBinding
```

This is a **hard deny**, even if someone tries to widen permissions later.

What this prevents:

* Privilege escalation via Git
* Applications granting themselves cluster-admin
* Accidental or malicious RBAC changes

Even if:

* the manifest exists in Git
* the Application syncs successfully

Argo CD will refuse to apply these resources.

This is a **non-negotiable production safety net**.

> **Important note on allow vs deny behavior:**
> When you define an explicit **whitelist** for cluster-scoped resources (for example, allowing only `Namespace`) or namespace-scoped resources, Argo CD follows an **implicit deny model**. Anything that is **not explicitly allowed is denied by default**.
>
> The blacklist exists to express **explicit hard denials** for particularly sensitive resources, but you should not assume that resources are allowed unless listed. In AppProjects, **whitelists define the only allowed surface area**, and everything outside that surface area is automatically blocked.

---

Absolutely. Below is a **cleaned, tighter version** of the writeup with **redundant explanations removed**, while keeping **all essential technical meaning intact**.
Nothing important is lost, only repetition and excess verbosity.

You can directly replace your existing section with this.

---

### Project roles and RBAC (who can operate GitOps)

```yaml
roles:
  - name: dev-readonly
    description: Read-only access for developers
    policies:
      - p, proj:app1-project:dev-readonly, applications, get, app1-project/*, allow
    groups:
      - app1-devs

  - name: platform-admin
    description: Full control for platform team
    policies:
      - p, proj:app1-project:platform-admin, applications, *, app1-project/*, allow
    groups:
      - platform-team
```

This defines **Argo CD–level RBAC scoped to this Project**.
It controls **who can view and operate Argo CD Applications**, not who can access Kubernetes resources.

This is **GitOps RBAC**, not Kubernetes RBAC.

---

### RBAC policy syntax (what the policy line means)

**Reference:** https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/#rbac-model-structure

Argo CD RBAC policies follow a **Casbin-style format**:

```
p, <role/user/group>, <resource>, <action>, <object>, <effect>
```

Example:

```
p, proj:app1-project:platform-admin, applications, *, app1-project/*, allow
```

Breakdown:

* `p`
  Policy rule declaration.

* `proj:app1-project:platform-admin`
  Scope: applies **only to the `platform-admin` role in `app1-project`**.

* `applications`
  Resource type: Argo CD Applications (not Kubernetes Deployments or Services).

* `*`
  Action: all Application-level operations.

* `app1-project/*`
  Object scope: all Applications within this Project.

* `allow`
  Explicit permission grant.

In plain terms:

> Allows users in the `platform-admin` role to **perform all Argo CD Application operations (view, sync, update, delete, rollback, prune, etc.) on every Application within the `app1-project`**.


---

### What roles represent in an AppProject

* Roles are **scoped to a Project**
* Roles apply **only to Applications in that Project**
* Roles are mapped to **external identity groups** (OIDC / SSO)

Roles do **not** grant cluster access.
They grant permission to **operate Argo CD Applications**.

---

### Developer read-only role

```yaml
- name: dev-readonly
```

Intended for developers and QA users who need **visibility without control**.

Policy behavior:

* Allows `get` on Applications
* Scope limited to `app1-project/*`

Allowed:

* View Applications
* Inspect sync status, health, and manifests

Not allowed:

* Sync
* Rollback
* Delete
* Enable or disable auto-sync
* Modify Applications

Group mapping:

```yaml
groups:
  - app1-devs
```

Any authenticated user in the `app1-devs` identity group automatically receives this role.

---

### Platform admin role

```yaml
- name: platform-admin
```

Intended for platform engineers and GitOps administrators.

Policy behavior:

* Applies to Argo CD Applications
* `*` enables all Application-level actions
* Scope limited to `app1-project/*`

Includes:

* sync
* update
* rollback
* delete
* prune
* auto-sync control

Group mapping:

```yaml
groups:
  - platform-team
```

Users in this group get **full Application control within the Project**, without requiring Kubernetes cluster-admin access.

---

### Where do these groups come from? (end-to-end RBAC flow)

The groups referenced in an AppProject (for example `app1-devs` or `platform-team`) are **not created inside the Project itself**. They come from Argo CD’s **authentication and identity integration layer**.

In most production environments, Argo CD does **not maintain its own user database**. Instead, it relies on an **external identity provider** as the single source of truth.

A very common setup looks like this:

1. **A central identity system exists**
   Examples include Microsoft Active Directory (MS-AD), Azure AD, Okta, Google Workspace, or Keycloak.

2. **Argo CD is integrated with the identity provider**
   Argo CD is configured to authenticate users using OIDC (or LDAP in some setups).
   At login time, authentication is delegated entirely to the identity provider.

3. **Argo CD receives user and group claims**
   After successful login, Argo CD receives:

   * user identity (username or email)
   * group membership information (for example `app1-devs`, `platform-team`)

4. **Argo CD RBAC evaluates permissions**
   Based on the received groups:

   * users are mapped to Project roles
   * Project policies define what actions are allowed

5. **Actions are allowed or denied**
   When a user tries to view an Application, trigger a sync, roll back, or delete an Application, Argo CD evaluates:

   * the user’s groups
   * the Project role bindings
   * the Project policies

   and then allows or blocks the action.

This is why RBAC decisions are **centralized, consistent, and enforceable**.

---

### Example: MS-AD as the identity source

If Microsoft Active Directory is your single source of truth:

* Users and groups are created and managed in MS-AD
* Group membership is assigned there (for example `app1-devs`, `platform-team`)
* Argo CD is integrated with MS-AD via OIDC or LDAP
* Argo CD reads users and groups from MS-AD at login time
* AppProject roles reference those **existing groups**
* Permissions are enforced automatically based on group membership

In this model:

* Argo CD does not create users
* Argo CD does not manage groups
* Argo CD only **consumes identity information**

---

### Is there a local user or group system in Argo CD?

Argo CD provides a **minimal local account mechanism**, but it is intentionally limited and **not designed for general user management**.

Local accounts:

* are **statically defined** in Argo CD configuration (`argocd-cm`)
* do **not support group creation or group membership**
* are typically used only for **initial bootstrap**, **break-glass administrative access**, or **automation and CI/CD tokens**

They are **not suitable** for multi-user environments, team-based access control, or scalable production RBAC.

In production setups, local accounts are usually **disabled, tightly restricted, or reserved exclusively for emergency scenarios**, with day-to-day access handled through external identity providers.

---

### Why this model works in production

* Identity is managed in one place
* Access patterns are consistent across tools
* Onboarding and offboarding are centralized
* GitOps permissions are enforced declaratively

Argo CD focuses on what it does best:

* enforcing **GitOps-level permissions**
* mapping identity groups to **Project guardrails**

---

## Applying and verifying the Project

```bash
kubectl apply -f app1-appproj.yaml
kubectl get appproj -n argocd
```

Successful output confirms:

* The Project is registered with Argo CD
* Governance rules are now active

Also verify in the UI:

* Argo CD UI → Settings → Projects → `app1-project`

> Guardrails first, workloads second.

---

## Step 4: Create Argo CD Applications (frontend and backend)

Now that the guardrails are in place, we can create Applications.

### Frontend Application CRD

`app1-fe-app-crd.yaml`

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app1-fe-app
  namespace: argocd
spec:
  project: app1-project
  source:
    repoURL: https://github.com/CloudWithVarJosh/app1-frontend-config.git
    targetRevision: HEAD
    path: frontend
  destination:
    server: https://kubernetes.default.svc
    namespace: app1-ns
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

```bash
kubectl apply -f app1-fe-app-crd.yaml
kubectl get applications -n argocd
```

### Backend Application CRD

`app1-be-app-crd.yaml`

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app1-be-app
  namespace: argocd
spec:
  project: app1-project
  source:
    repoURL: https://github.com/CloudWithVarJosh/app1-backend-config.git
    targetRevision: HEAD
    path: backend
  destination:
    server: https://kubernetes.default.svc
    namespace: app1-ns
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

```bash
kubectl apply -f app1-be-app-crd.yaml
kubectl get applications -n argocd
```

At this stage:

* Applications exist
* They show errors in the UI
* This is expected, because config repos are empty

---

## Step 5: Build and push container images

To keep the demo simple, we will use **public Docker images**.

### Frontend image

```bash
cd app1-frontend
docker build -t cloudwithvarjosh/app1-frontend:v1.0.0 .
docker push cloudwithvarjosh/app1-frontend:v1.0.0
```

### Backend image

```bash
cd app1-backend
docker build -t cloudwithvarjosh/app1-backend:v1.0.0 .
docker push cloudwithvarjosh/app1-backend:v1.0.0
```

Note:

* Images are pushed to `cloudwithvarjosh`
* Docker Desktop is already logged in
* On Linux VMs, run `docker login` first

---

## Step 6: Populate config repositories

Commit manifests with the following structure.
This structure already exists in the GitHub repo for this lecture.

```text
├── app1-backend
│   ├── app.py
│   └── Dockerfile
├── app1-backend-config
│   ├── argo
│   │   └── app1-be-app-crd.yaml
│   └── backend
│       ├── deploy.yaml
│       └── svc.yaml
├── app1-frontend
│   ├── app.py
│   └── Dockerfile
├── app1-frontend-config
│   ├── argo
│   │   └── app1-fe-app-crd.yaml
│   └── frontend
│       ├── deploy.yaml
│       └── svc.yaml
├── argocd-platform-config
│   └── app1-appproj.yaml
```

As soon as commits are pushed:

* Argo CD auto-sync triggers
* Resources are created automatically

---

## Step 7: Verify deployment

Check resources:

```bash
kubectl get all -n app1-ns
```

Because automated sync is enabled:

* no manual sync is required
* self-heal and prune are active

---

## Step 8: Access the application

Port-forward the frontend service:

```bash
kubectl port-forward -n app1-ns svc/frontend-svc 8081:80
```

Open browser:

```
http://localhost:8081
```

---


## Step 9: Policy enforcement and RBAC testing (intentional failure scenarios)

In this step, we will **intentionally break rules** to validate that our AppProject guardrails and RBAC controls are actually enforced.

This is not chaos engineering for availability.
This is **GitOps policy verification**.

---

### 1) Can Applications create resources that are not explicitly allowed?

So far, we explicitly allowed only a small set of cluster-scoped and namespace-scoped resources in the AppProject.
Anything outside that allowlist should be **implicitly denied**.

To verify this, we will attempt to deploy **two resources** that are *not* allowed:

* a **PersistentVolume** (cluster-scoped)
* a **PersistentVolumeClaim** (namespace-scoped)

---

#### Add an unsupported manifest

Go to the `app1-backend-config` repository and create a file named:

```
pv-pvc.yaml
```

Add the following content:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: app1-backend-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: app1-manual
  hostPath:
    path: /mnt/app1-backend-data
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app1-backend-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: app1-manual
  resources:
    requests:
      storage: 1Gi
```

Commit and push the changes.

---

#### Observe and verify

Because automated sync is enabled, Argo CD will immediately attempt to apply these resources.

Expected behavior:

* Application status becomes **OutOfSync**
* Sync **fails**
* Argo CD reports that the resources are **not permitted by the Project**

What this confirms:

* Cluster-scoped resources are denied unless explicitly whitelisted
* Namespace-scoped resources are also denied unless explicitly whitelisted
* The Project follows an **implicit deny model**

Nothing outside the defined surface area is allowed.

---

### 2) Can a user outside allowed roles perform Argo CD actions?

Next, we will test **RBAC enforcement** by logging in as a user that is **not mapped to any Project role**.

---

#### Login to Argo CD

```bash
argocd login localhost:8080
```

Authenticate as the `admin` user.

---

#### List existing local accounts

```bash
argocd account list
```

Observation:

* You should only see the built-in `admin` account
* No other users exist by default

---

#### Create a minimal local user (for testing only)

> This is for **demo and verification purposes only**.
> Local users are not recommended for production RBAC.

Edit the Argo CD config map:

```bash
kubectl edit cm -n argocd argocd-cm -o yaml
```

Add the following entry:

```yaml
data:
  accounts.cwvj: login
```

This declares a local account named `cwvj` with **UI login access only**.

---

#### Set a password for the new user

```bash
argocd account update-password \
  --account cwvj \
  --current-password admin@123 \
  --new-password cwvj@123
```

Explanation:

* `--account cwvj` specifies the local user
* `--current-password` must be the password of the user performing the action (`admin`)
* `--new-password` sets the password for the new user

---

#### Verify behavior

Login to the Argo CD UI as user `cwvj`.

Expected behavior:

* User can log in successfully
* User **cannot**:

  * sync Applications
  * delete Applications
  * modify Applications
  * perform any Project-scoped operations

Reason:

* The user is **not mapped to any Project role**
* No permissions are granted implicitly
* RBAC enforcement is working as expected

---

### What this step proves

* AppProject rules are **actively enforced**, not advisory
* Resources outside the allowlist are blocked
* RBAC is deny-by-default
* Authentication alone does not grant authorization

This confirms that **guardrails are real**, not theoretical.

---

## Critical note (please do not skip)

> **Do not delete the repositories created as part of this lecture.**

All repositories and structures created in this demo will be **reused and extended in upcoming lectures**, including:

* sync waves
* hooks
* orchestration and ordering
* multi-Application workflows
* platform bootstrap patterns

These topics build **incrementally** on the same repository layout and Argo CD setup, rather than starting from scratch each time.

Keeping the same repositories:

* preserves continuity across lectures,
* helps you see how GitOps systems evolve over time,
* mirrors how real production GitOps setups are iterated on.

In future lectures, we will **add to** these repositories, not replace them.

---

## Conclusion

Argo CD Projects are not an optional feature or a cosmetic grouping mechanism. They are **foundational to running Argo CD safely at scale**.

In this lecture, you learned that Projects:

* operate at the **GitOps control-plane level**, not the Kubernetes runtime level,
* enforce **hard guardrails before sync begins**,
* define **where Applications can deploy, what they can deploy, and who can operate them**,
* provide a **clean separation of duties** between platform teams and application teams.

Through the demo, we validated that these guardrails are not theoretical. Resources outside the allowlist were blocked, unauthorized users were denied actions, and policy violations were rejected automatically.

As we move forward into topics like **sync waves, hooks, orchestration, and multi-Application deployments**, Projects will remain the **policy foundation** on top of which all higher-level GitOps workflows are built.

---

## References

Official Argo CD documentation:

* Argo CD Projects
  [https://argo-cd.readthedocs.io/en/stable/user-guide/projects/](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)

* Argo CD RBAC
  [https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/](https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/)

* Argo CD Application CRD
  [https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/#applications](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/#applications)

* Argo CD API resources
  [https://argo-cd.readthedocs.io/en/stable/developer-guide/api-docs/](https://argo-cd.readthedocs.io/en/stable/developer-guide/api-docs/)

---


