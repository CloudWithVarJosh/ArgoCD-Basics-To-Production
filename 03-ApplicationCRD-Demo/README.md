# Argo CD Application CRD Deep Dive | Deploy Your First App with GitOps

## Video reference for this lecture is the following:


---
## ⭐ Support the Project  
If this **repository** helps you, give it a ⭐ to show your support and help others discover it! 

---

## Table of Contents

* [Introduction](#introduction)  
* [Kubernetes Resource Model and CRDs](#kubernetes-resource-model-and-crds)  
  * [Built-in Kubernetes Resources and Resource Definitions](#built-in-kubernetes-resources-and-resource-definitions)  
  * [Why Kubernetes Is Modular and Extensible](#why-kubernetes-is-modular-and-extensible)  
  * [Controllers and the Reconciliation Loop](#controllers-and-the-reconciliation-loop)  
  * [Built-in Resources With Controllers](#built-in-resources-with-controllers)  
  * [Built-in Resources Without Controllers](#built-in-resources-without-controllers)  
  * [Custom Resources and Custom Controllers](#custom-resources-and-custom-controllers)  
  * [Why This Matters for Argo CD](#why-this-matters-for-argo-cd)  
* [From CRDs to Application CRDs](#from-crds-to-application-crds)  
* [The Application CRD and Why It Matters](#the-application-crd-and-why-it-matters)  
* [Sample Application Manifest](#sample-application-manifest)  
* [Application Resource: Field-by-Field Breakdown](#application-resource-field-by-field-breakdown)  
* [How Argo CD Applications Map to Real-World Architectures](#how-argo-cd-applications-map-to-real-world-architectures)  
  * [Microservices Architecture](#microservices-architecture)  
  * [Multi-Tier Architecture](#multi-tier-architecture)  
  * [Monolithic Architecture](#monolithic-architecture)  
  * [Key Principle (Applies to All Architectures)](#key-principle-applies-to-all-architectures)  
  * [Repository Strategy and Best Practices](#repository-strategy-and-best-practices)  
  * [Final Mapping Summary](#final-mapping-summary)  
* [Application CRD vs Application Manifests](#application-crd-vs-application-manifests)  
* [One Argo CD, Multiple Clusters](#one-argo-cd-multiple-clusters)  
* [Demo: Deploying a Sample Application Using Argo CD](#demo-deploying-a-sample-application-using-argo-cd)  
  * [Prerequisites](#prerequisites)  
  * [Step 1: Access the Argo CD UI](#step-1-access-the-argo-cd-ui)  
  * [Step 2: Create the Application Manifest](#step-2-create-the-application-manifest)  
  * [Step 3: Apply the Application Resource](#step-3-apply-the-application-resource)  
  * [Step 4: Observe the Application in the UI](#step-4-observe-the-application-in-the-ui)  
  * [Step 5: Attempt Synchronization (Expected Failure)](#step-5-attempt-synchronization-expected-failure)  
  * [Step 6: Create the Target Namespace](#step-6-create-the-target-namespace)  
  * [Step 7: Re-Sync the Application](#step-7-re-sync-the-application)  
  * [Step 8: Access the Application](#step-8-access-the-application)  
  * [Key Argo CD Status Concepts](#key-argo-cd-status-concepts)  
  * [What This Demo Demonstrates](#what-this-demo-demonstrates)  
* [Conclusion](#conclusion)  
* [References](#references)  

---

## Introduction

Before working with **Application CRDs**, it is important to first understand **how Kubernetes models resources** and **how Kubernetes is extended using CRDs and controllers**. Without this foundation, GitOps tools like Argo CD can feel opaque rather than Kubernetes-native.

In this lecture, we build a **strong mental model** of Kubernetes resources by revisiting **Resource Definitions, CRDs, and controllers**, and clearly explaining **when reconciliation is required and when it is not**.

With this context, we introduce the **Application CRD**, the core abstraction Argo CD uses to represent a deployed application instance. We explain what it is, why it exists, and how it maps Git to Kubernetes in a way that aligns with real-world architectures such as microservices, multi-tier systems, and monoliths.

Finally, we reinforce these concepts with a **hands-on demo**, where we create our first Application resource and observe Argo CD detect drift, reconcile desired state from Git, and deploy a running application into the cluster.

This lecture establishes the **end-to-end mental model** required before moving into advanced Argo CD and GitOps workflows.

---

## Kubernetes Resource Model and CRDs

Before we start discussing **Application CRDs**, it is important to first build a **strong mental model** of how Kubernetes resources work, and how Kubernetes can be extended. This section lays the foundation for understanding *why* Argo CD defines its own CRDs and *why* controllers are central to GitOps.

---

### Built-in Kubernetes Resources and Resource Definitions

When you **bootstrap a Kubernetes cluster**, it already comes with a set of **built-in resources** such as `Pod`, `Deployment`, `Service`, `ConfigMap`, `Secret`, and many others.

These resources exist because Kubernetes already has their **Resource Definitions** built in.

A **Resource Definition** is the **API schema** that describes:

* What fields a resource supports
* Which fields are mandatory or optional
* What structure and data types are allowed

These schemas are defined by the **Kubernetes community** and shipped as part of Kubernetes itself.

As shown in the diagram:

* **Resource Definition** represents the built-in API type
* **Resource** is a user-created instance of that API type

For example, when you create a `Deployment`, you are creating a **Resource** that must strictly follow the schema defined by the **Deployment Resource Definition**.

If your YAML does not adhere to that schema, Kubernetes will reject it immediately with a validation error.

You can see all built-in resource types and their schemas using:

```bash
kubectl api-resources
```

This command lists:

* Resource names
* Short names
* API versions
* Whether they are namespaced
* Their `Kind`

This is how Kubernetes enforces consistency and safety at the API level.

---

### Why Kubernetes Is Modular and Extensible

Kubernetes is often described as a **modular and extensible system**. This is not marketing language, it is an architectural design choice.

Kubernetes allows you to **add new API types** beyond what ships by default.

When you add your own API type:

* It is called a **Custom Resource**
* The schema that defines it is called a **Custom Resource Definition (CRD)**

This mirrors the built-in model exactly:

| Built-in Kubernetes | Custom Extension                 |
| ------------------- | -------------------------------- |
| Resource Definition | Custom Resource Definition (CRD) |
| Resource            | Custom Resource                  |

As shown in the diagram:

* A **CRD** extends Kubernetes with a new API
* A **Custom Resource** is a user-created instance of that custom API

Without a CRD, Kubernetes has no idea how to validate or store a custom resource.

---

### Controllers and the Reconciliation Loop

Defining resources or custom resources alone is **not enough**.

Kubernetes is declarative, which means:

* Resources declare **desired state**
* Something must ensure the cluster **converges** to that state

That “something” is a **controller**.

A controller implements a **control loop**, which:

1. Observes the desired state (from resources)
2. Compares it with the current state
3. Takes action to reconcile the difference
4. Repeats continuously

This control loop is shown explicitly in the diagram.

Controllers are **optional**, but only in specific cases.

If a resource represents **static data** (for example, a ConfigMap), continuous reconciliation may not be required.

If a resource represents **ongoing behavior** (replicas, scheduling, retries, backups, rollouts), a controller is essential.

---

### Built-in Resources With Controllers

Many built-in Kubernetes resources have controllers because they require continuous enforcement:

* **Deployment Controller**
  Ensures desired replicas, rolling updates, and rollbacks

* **StatefulSet Controller**
  Ensures ordered rollout and stable storage identity

* **Job Controller**
  Ensures a specified number of successful pod completions

* **CronJob Controller**
  Creates Jobs on a defined schedule

These controllers continuously watch resources and reconcile state.

---

### Built-in Resources Without Controllers

Some Kubernetes resources **do not have their own controllers**, because they do not require reconciliation logic:

* **Namespace**
* **ConfigMap**
* **Secret**
* **Service**

For Services, this often causes confusion.

A Service itself does not have a controller that watches it continuously. Instead:

* **Endpoint / EndpointSlice controllers** react to Pod changes
* They update endpoints automatically as Pods are added or removed

This reinforces an important idea:

> Controllers watch **what matters**, not everything.

---

### Custom Resources and Custom Controllers

The same principles apply to **Custom Resources**.

When you define a CRD:

* You are only defining **schema**
* Kubernetes will store and validate objects
* Kubernetes will **not act** on them automatically

If your custom resource represents something that must be continuously enforced (for example, backups running on a schedule, as shown in the diagram), you **must** implement a controller.

This is the **Operator pattern**:

* CRD defines the API
* Controller implements the behavior

---

### Why This Matters for Argo CD

We are discussing all of this because **Argo CD follows this exact Kubernetes model**.

Argo CD is Kubernetes-native because:

* It defines **Custom Resource Definitions**
* It runs **controllers** that reconcile those resources

Since we installed Argo CD in the previous lecture, our cluster already contains Argo CD CRDs and controllers. What we do *not* have yet are **Custom Resources**, because we have not created any.

You can verify the CRDs installed by Argo CD using:

```bash
kubectl api-resources | grep -i argo
```

Example output:

```
applications        app,apps        argoproj.io/v1alpha1   true   Application
applicationsets     appset,appsets  argoproj.io/v1alpha1   true   ApplicationSet
appprojects         appproj,appprojs argoproj.io/v1alpha1  true   AppProject
```

This output shows:

* Short names
* API versions
* Whether the resource is namespaced
* The `Kind`

In this lecture, we will focus on the **Application** kind.
That is the **Custom Resource** Argo CD uses to declaratively define *what to deploy, from where, and into which cluster*.

Once we understand this, Application CRDs will feel natural rather than magical.

---


## From CRDs to Application CRDs

In the previous section, we established how Kubernetes works internally using **Resource Definitions**, **Resources**, **CRDs**, and **Controllers**.

We saw that:

* Kubernetes becomes extensible by defining **CRDs**
* CRDs only define **schema**
* **Controllers** are required when continuous reconciliation is needed

Argo CD follows this exact Kubernetes model.

Argo CD extends Kubernetes by defining its own CRDs and controllers.
The **most important CRD** we will work with in this course is the **Application CRD**.

---

## The Application CRD and Why It Matters

The **Application CRD** represents a **deployed application instance** as understood by Argo CD. It is the Kubernetes resource through which Argo CD models, tracks, and reconciles an application in a given environment.

An **Application resource** is defined by two fundamental references:

* **Source**
  A reference to the **desired state in Git**, including the repository, revision, and path that describe how the application should run.

* **Destination**
  A reference to the **target Kubernetes cluster and namespace** where that desired state should be applied.
  The destination cluster can be identified either by **server** or by **name**, but not both.

Together, these two references answer a simple but critical question:

> *This is the application state declared in Git, and this is where it must run.*

This design creates a clean separation of responsibilities:

* **Git** declares the desired runtime state
* The **Application resource** declares management intent
* **Argo CD controllers** continuously reconcile the two

The Application CRD is therefore not your application itself.
It is Argo CD’s **contract** that connects Git to Kubernetes and enables continuous reconciliation.

This is the point where GitOps becomes concrete:

Git declares the desired state.
The Application resource declares intent.
Argo CD enforces that intent continuously.

That is why the Application CRD is central to Argo CD’s design.

In the next section, we will **create our first Application resource** and observe how Argo CD reconciles it in real time, turning these concepts into something tangible inside the cluster.


---

## Sample Application Manifest

Reference: https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/#applications

Below is a **minimal but valid** Application definition:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
```

This manifest is enough to let Argo CD:

* Pull manifests from Git
* Compare them with cluster state
* Continuously reconcile drift

---

## Application Resource: Field-by-Field Breakdown

**apiVersion and kind**
Identify this object as an Argo CD–defined resource, created from the Application CRD.

**metadata.name**
The name of the Application object inside Argo CD.
Used for tracking, reconciliation, and UI visibility.
It does *not* have to match deployment or namespace names.

**metadata.namespace**
The namespace where **Argo CD is installed**, typically `argocd`.
All Argo CD–owned resources, including **Application** and **AppProject**, **must be created in the Argo CD namespace** as required by Argo CD’s declarative model.

> The Application resource does not belong to your app namespace.
> It belongs to Argo CD itself and therefore must live in the Argo CD namespace.


**spec.project**
Associates the application with an Argo CD Project.
Projects provide grouping, isolation, and policy boundaries.

**spec.source.repoURL**
The Git repository that declares the desired state.
This typically points to an **application configuration repository**, not source code.

**spec.source.targetRevision**
Specifies the Git revision Argo CD should track.
This can be a branch, tag, commit SHA for Git, or a chart version for Helm.

`HEAD` refers to the **latest commit of the default branch** of the repository (for example `main` or `master`).

```yaml
# Examples
targetRevision: HEAD        # Latest commit on default branch
targetRevision: main        # Track a specific branch
targetRevision: v1.2.0      # Track a Git tag
targetRevision: 9fceb02     # Pin to a specific commit SHA
```

> Using `HEAD` means Argo CD will always reconcile against the most recent commit on the repository’s default branch.

> In production, branches are the norm, tags are used for controlled releases, and commit SHAs are reserved for exceptional cases.

> **Note:**
> The default branch is the branch you get by default when a repository is cloned.
> It is typically named `main` (GitHub) or `master` (Git), but it can be renamed to anything.



**spec.source.path**
The directory inside the repository containing manifests, Helm charts, or Kustomize overlays.

**spec.destination.server**
The Kubernetes API server where resources should be applied.
This enables **multi-cluster management from a single Argo CD instance**.

**spec.destination.namespace**
The namespace in the destination cluster where resources will be created.

> **Note:**
> In examples, you will often see the same name reused, such as `guestbook`, for the Application name, Git directory, and Kubernetes namespace.
> This is done **only for clarity and symmetry in demos**.
> These names do **not** need to match, and Argo CD treats them as **independent identifiers**.

---

## How Argo CD Applications Map to Real-World Architectures

In Argo CD, **one Application resource represents one independently deployable workload**.

What that workload represents depends entirely on how your system is architected.
The attached diagram visualizes the **three most common patterns** you will encounter in real environments.

---

### Microservices Architecture

In a **microservices architecture**, an application is decomposed into multiple independently deployable services.

As shown in the diagram:

* `app1` is composed of `ms-1`, `ms-2`, and `ms-3`
* Each microservice has:

  * Its **own Git repository** (`ms-1-repo`, `ms-2-repo`, `ms-3-repo`)
  * Its **own Argo CD Application** (`ms1-app`, `ms2-app`, `ms3-app`)
  * Its **own reconciliation loop** into Kubernetes

In this model:

> **One microservice = one Argo CD Application**

This is the **most common and recommended pattern** in modern GitOps-driven platforms and aligns directly with Argo CD’s design philosophy.

---

### Multi-Tier Architecture

In a **multi-tier architecture** (for example: web tier and app tier), deployability is usually defined at the **tier level**, not the individual component level.

As shown in the diagram:

* `app2` is split into:

  * `web-tier`
  * `app-tier`
* Each tier:

  * Has its **own configuration repository**
  * Is managed by a **separate Argo CD Application**
  * Can be deployed and rolled back independently

In this model:

> **One tier = one Argo CD Application**

This approach is common in transitional architectures or systems modernized incrementally toward microservices.

---

### Monolithic Architecture

In a **monolithic architecture**, the entire application is typically deployed as a single unit.

In such cases:

* A **single Git source**
* A **single Argo CD Application**
* A **single deployment boundary**

> **One monolith = one Argo CD Application**

While fully valid, this model is increasingly uncommon in modern systems.

---

### Key Principle (Applies to All Architectures)

Regardless of architecture style, the invariant rule is:

> **One Argo CD Application maps to one independently deployable unit.**

That unit might be:

* A microservice
* A tier
* Or a monolith

But it must always represent **something you want to deploy, roll back, and reconcile independently**.

---

### Repository Strategy and Best Practices

Although Argo CD allows multiple applications to live in a **single repository using different paths**, modern teams rarely do this in practice.

Instead, as illustrated in the microservices section of the diagram, teams prefer:

* **One service → one repository → one Argo CD Application**

This approach:

* Creates **clear ownership boundaries** for teams
* Enables **fine-grained RBAC**
* Minimizes **blast radius**
* Supports **independent deployments and rollbacks**
* Scales cleanly with organizational growth

---

### Final Mapping Summary

> **10 microservices → 10 Git repositories → 10 Argo CD Application resources**

This model aligns naturally with:

* GitOps principles
* Kubernetes ownership boundaries
* Argo CD’s reconciliation model
* Real-world platform and team structures

This is why Argo CD Applications are modeled the way they are, and why understanding this mapping is critical before deploying your first Application resource.

---

## Application CRD vs Application Manifests

This distinction is critical and often misunderstood.

| Aspect     | Application Resource       | Kubernetes Manifests        |
| ---------- | -------------------------- | --------------------------- |
| Owned by   | Argo CD                    | Your application            |
| Lives in   | Cluster (argocd namespace) | Git repository              |
| Declares   | What Argo CD should manage | What Kubernetes should run  |
| Managed by | Argo CD controller         | Kubernetes controllers      |
| Purpose    | Git → Cluster mapping      | Runtime workload definition |

---

## One Argo CD, Multiple Clusters

A key design principle of Argo CD:

You do **not** need Argo CD installed in every cluster.

A single Argo CD instance can:

* Watch multiple Git repositories
* Deploy to multiple clusters
* Reconcile applications across environments

This is why the Application resource explicitly defines both **source** and **destination**.

---

## Demo: Deploying a Sample Application Using Argo CD

In this demo, we will deploy a **sample application using an Argo CD Application resource** and observe how Argo CD reconciles desired state from Git into the cluster.

---

### Prerequisites

Before starting, ensure:

* A **KIND cluster** is running
* **Argo CD is installed**
* All Argo CD pods are in `Running` state

Verify:

```bash
kubectl get pods -n argocd
```

---

### Step 1: Access the Argo CD UI

For this demo, we will use **port-forwarding** to access Argo CD locally.

```bash
kubectl port-forward service/my-argo-cd-argocd-server -n argocd 8080:443
```

Access the UI at:

```
http://localhost:8080
```

> This is a **learning-only setup**.
> In production, Argo CD is exposed via Ingress or LoadBalancer.

---

### Step 2: Create the Application Manifest

We will use the **same sample application** referenced in the previous section.

Create a file named `sample-app.yaml` and add the following content:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
```

**What this declares:**

* Git repository and path containing desired state
* Target cluster (in-cluster Kubernetes API)
* Target namespace where resources should be created

---

### Step 3: Apply the Application Resource

Apply the manifest:

```bash
kubectl apply -f sample-app.yaml
```

Verify that Argo CD has registered the Application:

```bash
kubectl get app -n argocd
```

Expected output:

```
NAME        SYNC STATUS   HEALTH STATUS
guestbook   OutOfSync     Missing
```

**Why OutOfSync and Missing?**

* Desired state exists in Git
* Live state does not yet exist in the cluster
* Argo CD has detected drift but has not reconciled yet

---

### Step 4: Observe the Application in the UI

Open the Argo CD UI at:

```
http://localhost:8080
```

You will see the **guestbook** application listed on the home page.

Important observations:

* Argo CD is reading manifests from the `guestbook/` directory at the repository root
* That directory contains Kubernetes `Deployment` and `Service` manifests
* Argo CD automatically adds **annotations** to managed resources
  These annotations are informational and used by tooling, not Kubernetes itself

---

### Step 5: Attempt Synchronization (Expected Failure)

Click:

**Sync → Synchronize**

The sync will **fail**.

Check the logs or error message in the UI.
You will see an error indicating that the **namespace does not exist**.

This is expected.

Argo CD **does not create namespaces automatically by default**.

---

### Step 6: Create the Target Namespace

Create the namespace manually:

```bash
kubectl create ns guestbook
```

---

### Step 7: Re-Sync the Application

Return to the Argo CD UI and click:

**Sync → Synchronize**

This time, the synchronization will succeed.

Observe:

* Resources are created in the `guestbook` namespace
* Sync status changes to **Synced**
* Health status transitions to **Healthy**

Explore the application tabs in the UI:

* Tree
* Events
* Resource details
* History and diff views

---

### Step 8: Access the Application

Port-forward the service to access the application UI:

```bash
kubectl port-forward service/guestbook-ui -n guestbook 8081:80
```

Open:

```
http://localhost:8081
```

You should now see the **Guestbook application running**.

---

### Key Argo CD Status Concepts

**Sync Status**
Indicates whether **live state matches desired state**.

* **Synced** – Live state matches Git
* **OutOfSync** – Drift detected
* **Progressing** – Reconciliation in progress

**Health Status**
Indicates **runtime health**, independent of sync.

* **Healthy** – Application running as expected
* **Degraded** – Application synced but unhealthy (for example, crashing pods)

> An application can be **Synced but Degraded**.
> Sync answers *“did we apply?”*, health answers *“is it working?”*.

---

### What This Demo Demonstrates

* The Application resource is **pure intent**
* Git declares desired state
* Argo CD detects drift
* Reconciliation happens only when prerequisites are met
* UI reflects **real-time reconciliation state**

This is the **first tangible GitOps loop** in action.

---

## Conclusion

By the end of this lecture, we connected **Kubernetes internals, CRDs, controllers, and GitOps** into a single, consistent model.

We saw that Kubernetes enforces consistency through **schemas and resource definitions**, becomes extensible through **CRDs**, and relies on **controllers** for continuous reconciliation. CRDs define *what is allowed*; controllers define *what happens*.

Building on this foundation, we explored the **Application CRD**, Argo CD’s Kubernetes-native way of modeling a deployed application instance. We saw how an Application resource declaratively defines the **source of desired state**, the **destination cluster and namespace**, and the **intent** that Argo CD continuously enforces.

We also mapped Application resources to real-world architectures, reinforcing that **one Argo CD Application always represents one independently deployable unit**.

Finally, through the demo, we observed GitOps in action by creating an Application resource, resolving drift, synchronizing state, and interpreting **sync** and **health** statuses.

At this point, Application CRDs should feel natural, not magical. They are simply **Kubernetes-native APIs backed by controllers**.

In the next lecture, we will build on this by exploring **sync policies and automated reconciliation**, moving closer to production-grade GitOps usage.

---

## References

**Kubernetes**

* Kubernetes API Concepts
  [https://kubernetes.io/docs/concepts/overview/kubernetes-api/](https://kubernetes.io/docs/concepts/overview/kubernetes-api/)

* Kubernetes Controllers
  [https://kubernetes.io/docs/concepts/architecture/controller/](https://kubernetes.io/docs/concepts/architecture/controller/)

* Custom Resource Definitions (CRDs)
  [https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)


**Argo CD and GitOps**

* Argo CD Documentation
  [https://argo-cd.readthedocs.io/en/stable/](https://argo-cd.readthedocs.io/en/stable/)

* Argo CD Declarative Setup
  [https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/)

* Argo CD Architecture
  [https://argo-cd.readthedocs.io/en/stable/operator-manual/architecture/](https://argo-cd.readthedocs.io/en/stable/operator-manual/architecture/)

* OpenGitOps Principles
  [https://opengitops.dev/](https://opengitops.dev/)

---
