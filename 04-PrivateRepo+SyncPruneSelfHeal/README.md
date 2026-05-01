# Argo CD Hands-On Project Demo | Private Git, Secrets, Pruning & Self-Healing

## Video reference for this lecture is the following:

[![Watch the video](https://img.youtube.com/vi/8PGOWrn1YW4/maxresdefault.jpg)](https://www.youtube.com/watch?v=8PGOWrn1YW4&ab_channel=CloudWithVarJosh)

---
## ⭐ Support the Project  
If this **repository** helps you, give it a ⭐ to show your support and help others discover it! 

---
## 📑 Table of Contents

* [Introduction](#introduction)  
* [Demo: Production-Style GitOps with Argo CD](#demo-production-style-gitops-with-argo-cd)  
  * [Demo Objective: What We Will Build and Prove](#demo-objective-what-we-will-build-and-prove)  
  * [Step 1: Create Two Private GitHub Repositories](#step-1-create-two-private-github-repositories)   
  * [Step 2: Create a GitHub Personal Access Token (PAT)](#step-2-create-a-github-personal-access-token-pat)  
  * [Step 3: Prepare Local Project Structure](#step-3-prepare-local-project-structure)  
  * [Step 4: Create a Private DockerHub Repository and Token](#step-4-create-a-private-dockerhub-repository-and-token)  
  * [Step 5: Build and Push the Container Image](#step-5-build-and-push-the-container-image)  
  * [Step 6: Create Kubernetes Namespace and Image Pull Secret](#step-6-create-kubernetes-namespace-and-image-pull-secret)   
  * [Step 7: Kubernetes Manifests (Config Repository)](#step-7-kubernetes-manifests-config-repository)  
  * [Step 8: Create the Argo CD Application (Config Repository)](#step-8-create-the-argo-cd-application-config-repository)  
  * [Step 9: Push Code to Both Repositories](#step-9-push-code-to-both-repositories)  
  * [Step 10: Add Private Repository Credentials to Argo CD](#step-10-add-private-repository-credentials-to-argo-cd)  
  * [Step 11: Synchronization and Verification](#step-11-synchronization-and-verification)  
* [Argo CD Features With Demos](#argo-cd-features-with-demos)  
  * [Automated Sync](#automated-sync)  
    * [Demo: Automated Sync](#demo-automated-sync)  
  * [Pruning](#pruning)  
    * [Demo: Pruning](#demo-pruning)  
    * [What We Observed During the Demo (Important Argo CD Behavior)](#what-we-observed-during-the-demo-important-argo-cd-behavior)
  * [Self-healing](#self-healing)  
    * [Demo: Self-healing](#demo-self-healing)  
  * [Enabling All Three Features Together](#enabling-all-three-features-together)  
  * [Final Mental Model](#final-mental-model)  
* [Conclusion](#conclusion)  
* [References](#references)  

---

## Introduction

In real-world GitOps environments, **nothing is public by default**.
Source code lives in private Git repositories, container images are stored in private registries, and every interaction requires explicit authentication and authorization.

In this lecture, we combine **two critical aspects of Argo CD that are inseparable in production**:

1. How Argo CD connects to **private Git repositories and private container registries**
2. How Argo CD enforces and automates the **desired state** using features like **Automated Sync, Pruning, and Self-healing**

Rather than treating these as isolated topics, we walk through a **single, end-to-end production-style demo** using the `app1` application. We start by establishing secure access to private systems and then layer Argo CD’s advanced reconciliation features on top of that foundation.

The objective of Lecture 4 is to help you build a **complete mental model** of:

* Where credentials live and who consumes them
* Why secrets cannot be treated as part of GitOps desired state
* How Argo CD behaves once it has full visibility into Git and the cluster
* What really happens when automation features are enabled in a GitOps system

This lecture represents the transition from **basic Argo CD usage** to **production-grade GitOps operations**.

---

# Demo: Production-Style GitOps with Argo CD
***From Private Source Code to Reconciled Kubernetes State***

Before we start executing any steps, let’s understand **what this demo represents** and **why it is structured this way**.

In real-world environments, almost everything you deploy lives in **private repositories**. Public repositories are typically limited to open source projects or learning experiments. If you are building or operating production systems, you will deal with **private Git repositories**, **private container images**, and **controlled access** at every layer.

The good news is that the **core GitOps concepts remain the same** regardless of the Git provider. Whether you use GitHub, GitLab, Bitbucket, or Azure Repos, Argo CD integrates with them in a very similar way. In this demo, we will use **GitHub** as the reference implementation.

Official reference:
[https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/](https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/)

---

## Demo Objective: What We Will Build and Prove

![Alt text](/images/4a.png)

This demo walks end-to-end through a **production-style GitOps flow**, showing how **private source code** is transformed into a **reconciled Kubernetes runtime state** using **Argo CD**.

We will first focus on **artifact creation**, then transition into **GitOps reconciliation**, exactly as shown in the diagram.

In this demo, we will:

* Create **private Git repositories** to clearly separate application code and platform configuration ownership
* Generate and use **authenticated access** for Git and container registries, avoiding public or insecure shortcuts
* Build a **versioned container image** and store it in a **private registry**
* Declare the application’s **desired runtime state** using Kubernetes manifests stored in Git
* Connect Git to Kubernetes using an **Argo CD Application**, establishing Git as the single source of truth
* Observe how Argo CD **reconciles live cluster state** to match what is defined in Git

This demo intentionally does **not** use CI automation yet. Image builds and pushes are performed manually to keep the focus on **GitOps fundamentals**.

Only after this foundation is clear will we explore **advanced Argo CD features** such as **automated sync, pruning, and self-healing**.

---


## Step 1: Create Two Private GitHub Repositories

We deliberately use **two separate private repositories** to mirror how GitOps is implemented in production, with clear ownership and responsibility boundaries.

---

### Application Code Repository

**Repository details**

* GitHub → New Repository
* Name: `cwvj-app1`
* Visibility: **Private**

**Purpose and ownership**

* Owned primarily by the **application team**
* Contains:

  * Application source code
  * Dockerfile
* Focused on building application artifacts, not deployment logic

---

### Configuration Repository

**Repository details**

* GitHub → New Repository
* Name: `cwvj-app1-config`
* Visibility: **Private**

**Purpose and ownership**

* Owned primarily by the **platform / DevOps team**
* Contains:

  * Kubernetes manifests
  * Argo CD Application configuration
* Represents the **desired runtime state** monitored by Argo CD

---

### Why this separation matters

* Developers own **what the application is**
* Platform teams own **how the application runs**
* Git becomes the **single source of truth** for deployment state

---

## Step 2: Create a GitHub Personal Access Token (PAT)

For this demo, we will use a **GitHub Personal Access Token** to authenticate against private repositories.

> In production, you typically use **separate credentials** for different systems.
> For simplicity, we will reuse a single token here.

#### Create the PAT

* GitHub → Settings → Developer Settings → Personal Access Tokens
* Create **Fine-grained token**
* Name: `argocd-demo`
* Expiration: 7 days (choose based on policy in real setups)
* Repository access: **Selected repositories**

  * Select both private repositories created earlier
* Permissions:

  * Contents: **Read and write**

Copy the token immediately. GitHub will not show it again.

#### Why this token is being used

In this demo, the same token is used for:

1. Developers pushing code to the app repo
2. DevOps pushing config to the config repo
3. Argo CD reading desired state from Git

> In production, Argo CD should have **read-only access** to configuration repositories.

> **Note:** In this demo, we are using a **Personal Access Token (PAT)** for Argo CD to Git communication, which is **tied to a user identity**. As we progress through the course, we will improve this setup by switching to **deploy keys**. Unlike PATs, deploy keys have a **one-to-one relationship with a repository** and are **not tied to any user identity**, making them the **preferred and more secure approach** for GitOps tools and CI systems to access repositories.


---

## Step 3: Prepare Local Project Structure

Create two directories:

#### app1-code

Contains:

* Python application files
* Dockerfile

#### app1-config

Contains:

* Kubernetes Deployment and Service manifests
* Argo CD Application CRD

This mirrors how code and configuration evolve independently.

---

## Step 4: Create a Private DockerHub Repository and Token

#### Create the Repository

* Log in to DockerHub
* Create repository: `cwvj-app1`
* Visibility: **Private**

#### Create DockerHub Access Token

* Profile → Account Settings → Personal Access Tokens
* Token name: `argocd-demo`
* Access: **Read-only**

This token will be used by the **container runtime** to pull images.

---

## Step 5: Build and Push the Container Image

From the application directory:

```bash
docker build -t cloudwithvarjosh/cwvj-app1:v1.0.0 .
docker push cloudwithvarjosh/cwvj-app1:v1.0.0
```

> For now, this is manual. Later in the course, Jenkins will automate this.

---

## Step 6: Create Kubernetes Namespace and Image Pull Secret

Before Kubernetes can run our application pods, it needs to **pull the container image**. For **private images**, the container runtime (CRI) must authenticate with the image registry. Kubernetes achieves this using **image pull secrets**, which are then referenced inside the Pod or Deployment spec.

#### Create the Namespace

We first create a dedicated namespace for the application:

```bash
kubectl create ns app1-ns
```

This keeps application resources logically isolated and mirrors real production clusters where namespaces represent ownership boundaries.

---

#### Create Docker Registry Secret

Now we create a Kubernetes secret that stores Docker registry credentials. This secret will later be referenced in the Deployment manifest using `imagePullSecrets`.

```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=cloudwithvarjosh \
  --docker-password=DOCKERHUB_ACCESS_TOKEN \
  --docker-email=cloudwithvarjosh@gmail.com \
  --namespace=app1-ns
```

**Explanation**

* `docker-registry`
  Tells Kubernetes this secret is specifically meant for container registry authentication.

* `--docker-server`
  The registry endpoint. For DockerHub, this is `https://index.docker.io/v1/`.

* `--docker-username`
  Your DockerHub username.

* `--docker-password`
  The DockerHub **access token** (not your actual password).

* `--docker-email`
  Required for legacy compatibility. Not used for authentication.

* `--namespace`
  The namespace where the secret will live. The secret must exist in the same namespace as the Pod.

---

#### Verifying the Secret

You can view the secret using:

```bash
kubectl get secret dockerhub-secret -n app1-ns -o yaml
```

The credentials are stored inside the `.dockerconfigjson` field, base64-encoded.

To decode it:

```bash
echo -n <value-from-.dockerconfigjson> | base64 --decode
```

You will see the registry login details in JSON format.

> Important: Base64 encoding is **not encryption**. Anyone with permission to read secrets can decode them.

---

#### Image Registry Authentication Options (From weakest to strongest)

**1. DockerHub Password (Not recommended)**

* **What it is:** Uses your actual DockerHub account password for authenticating to the container registry.
* **How it is used:** Stored in a Kubernetes secret and referenced via `imagePullSecrets` for pulling private images.
* **Why it is not recommended:** High risk credential with broad access, hard to rotate safely, and violates the principle of least privilege.

**2. DockerHub Access Tokens (Minimum baseline)**

* **What it is:** Scoped tokens generated from DockerHub that can be limited to read-only registry access.
* **How it is used:** Stored in a Kubernetes registry secret and used by the container runtime to authenticate and pull images.
* **Why it is the minimum baseline:** Safer than passwords and supports least privilege, but still relies on static secrets that must be managed and rotated.

**3. External Secrets + Secret Manager (Production standard)**

* **What it is:** Secrets are stored outside the cluster in systems like AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault.
* **How it is used:** An external secrets controller syncs or injects the secret into Kubernetes at runtime.
* **Why it is the production standard:** Centralized management, better auditing, easier rotation, and reduced direct exposure of credentials inside the cluster.

> With passwords and access tokens, secrets usually need to be created **imperatively** (manually or via CI) because secret values **cannot** be committed to Git. This breaks **GitOps**, as Git no longer represents the full **desired state**. **External Secrets** solve this by allowing secret **manifests** to be version controlled while keeping the actual secret values in a secure external store. At runtime, a **controller** syncs the values into Kubernetes secrets.

**4. Cloud-native Registry IAM (Best option)**

* **What it is:** Native identity-based authentication provided by cloud registries such as ECR, GAR, and ACR.
* **How it is used:** Kubernetes workloads authenticate to the registry using cloud IAM roles or identities instead of stored secrets.
* **Why it is the best option:** Eliminates static secrets entirely, integrates with cloud IAM, and provides the strongest security posture with least operational overhead.



> **Important note:** **Cloud-native IAM integration** (e.g., **IRSA with Amazon ECR**) works seamlessly only with registries that are **native to the cloud provider**, since those services trust **IAM identities** directly. **External registries** such as **DockerHub** or other **third-party providers** do not support **IAM-based access**. In these cases, the **production best practice** is to use a **Secret Manager** with an **External Secrets Operator** to inject credentials securely at runtime.
The same principle applies to **external Git providers** (**GitHub/GitLab**). While modern **CI/CD systems** increasingly support **OIDC federation** to assume **cloud IAM roles** without secrets, within **Kubernetes clusters** you typically still rely on **Secret Manager + External Secrets** to supply **SSH keys or tokens** securely.


--- 

### Security Considerations (Critical)

Even if you use **AWS Secrets Manager**, **Vault**, or any other external secret store, the secret will eventually be **materialized inside Kubernetes** so that the container runtime can read it.

This means:

* Secrets must be protected using **RBAC**
* `get`, `list`, and `watch` access on secrets should be **very tightly scoped**
* Encoding only provides obfuscation, not security

#### Important concept

An engineer can be allowed to **create or update Deployments** without having any access to secrets. The container runtime will still pull images using the credentials defined in the secret.

---

## Step 7: Kubernetes Manifests (Config Repository)

All Kubernetes manifests used to deploy the application live in the **app1-config repository**. This repository represents the **desired state** that Argo CD continuously monitors and reconciles.

The main manifest used here is **`deploy-svc.yaml`**, which contains:

* A **Deployment** to run the application pods
* A **ClusterIP Service** to expose the application internally

For this demo, we deliberately use a ClusterIP service so that we can later access the application using **kubectl port-forward**, without exposing it outside the cluster.

---

### Deployment Manifest

The Deployment is responsible for running the application container and ensuring the desired number of replicas.

Key points:

* The Deployment runs in the `app1-ns` namespace
* The container image is pulled from a **private DockerHub repository**
* `imagePullSecrets` supplies the registry credentials to the container runtime

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app1
  namespace: app1-ns
  labels:
    app: app1
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app1
  template:
    metadata:
      labels:
        app: app1
    spec:
      imagePullSecrets:
        - name: dockerhub-secret
      containers:
        - name: app1
          image: cloudwithvarjosh/cwvj-app1:v1.0.0
          ports:
            - containerPort: 5000
```

---

### Service Manifest

The Service provides stable internal networking for the application pods.

Key points:

* A **ClusterIP** service exposes the application **only within the cluster**
* Traffic is routed to pods matching the label `app=app1`
* Port `80` is mapped to container port `5000`
* This service will later be used with **kubectl port-forward** to access the application locally for testing

```yaml
apiVersion: v1
kind: Service
metadata:
  name: app1-svc
  namespace: app1-ns
spec:
  type: ClusterIP
  selector:
    app: app1
  ports:
    - name: http
      port: 80
      targetPort: 5000
```

---

## Step 8: Create the Argo CD Application (Config Repository)

The **Argo CD Application CRD itself is version controlled**, just like any other Kubernetes resource. Since it represents the desired state of how the application should be deployed, it belongs in the **app1-config repository** along with the Kubernetes manifests.

This ensures that:

* Application onboarding is declarative
* Cluster state is reproducible
* Argo CD setup follows GitOps principles

---

### Argo CD Application Manifest

Create the following file in the **app1-config repository**:

**`app1-app-crd.yaml`**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app1
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/CloudWithVarJosh/cwvj-app1-config.git
    targetRevision: HEAD
    path: .  # Manifests are stored at the root of the repo
  destination:
    server: https://kubernetes.default.svc
    namespace: app1-ns
```

Key points:

* `repoURL` points to the **private config repository**
* `targetRevision: HEAD` tracks the latest commit on the default branch
* `path: .` is used because Kubernetes manifests live in the repo root
* The application is deployed into the `app1-ns` namespace

---

### Apply the Application CRD

Apply the Application resource to the cluster:

```bash
kubectl apply -f app1-app-crd.yaml
```

---

### Expected State After Applying

If you open the **Argo CD UI** at this point, you will see that:

* The `app1` application exists
* The application is in an **Error** or **Missing credentials** state

This is **expected behavior**.

Argo CD cannot yet access the private Git repository because **no repository credentials have been configured**. In the next step, we will explicitly provide Argo CD with access to the private config repository so it can read the desired state and begin synchronization.

---

## Step 9: Push Code to Both Repositories

> **Note:** You must use your **GitHub username** and **Personal Access Token (PAT)** when pushing to these private repositories.


### Push Application Code

```bash
# Move to the application code directory
cd app1-code

# Initialize a new Git repository
git init

# Stage all application files
git add .

# Commit the application code
git commit -m "Initial commit with application code"

# Rename the default branch to main
git branch -M main

# Add the remote application repository
git remote add origin https://github.com/CloudWithVarJosh/cwvj-app1.git

# Update the remote URL to include your GitHub username and PAT
git remote set-url origin https://<GITHUB-PAT>@github.com/CloudWithVarJosh/cwvj-app1.git

# Push the code to the main branch
git push origin main
```

---

### Push Configuration

```bash
# Move to the configuration directory
cd app1-config

# Initialize a new Git repository
git init

# Stage all Kubernetes and Argo CD manifests
git add .

# Commit the configuration files
git commit -m "Initial commit with config files"

# Rename the default branch to main
git branch -M main

# Add the remote configuration repository
git remote add origin https://github.com/CloudWithVarJosh/cwvj-app1-config.git

# Update the remote URL to include your GitHub username and PAT
git remote set-url origin https://<GITHUB-PAT>@github.com/CloudWithVarJosh/cwvj-app1-config.git

# Push the configuration to the main branch
git push origin main
```

---

## Step 10: Add Private Repository Credentials to Argo CD

Argo CD needs credentials to read private Git repositories.

This is similar to how Kubernetes uses secrets for private images.

### Install Argo CD CLI

Follow official instructions:
[https://argo-cd.readthedocs.io/en/stable/cli_installation/](https://argo-cd.readthedocs.io/en/stable/cli_installation/)

Verify:

```bash
argocd version
```

Login:

```bash
argocd login localhost:8080
```

### Add Repository via CLI

```bash
argocd repo add https://github.com/CloudWithVarJosh/cwvj-app1-config.git \
  --name app1-config-repo \
  --username cloudwithvarjosh \
  --password <GITHUB-PAT>
```

Argo CD creates a Kubernetes secret internally and stores it in etcd.

Verify:

```bash
argocd repo list
kubectl get secrets -n argocd
```

You can also add repositories via UI:
Settings → Repositories

---

## Authentication Methods and Best Practices

* Username and PAT works and is easy to understand
* SSH deploy keys are commonly preferred in production
* Deploy keys are repository bound, not user bound
* Default usage is read-only pull, which fits GitOps
* Smaller blast radius and cleaner audit trails

Mental model:

* PAT: user acting like a system
* Deploy key: system without identity
* GitHub App: first-class system identity

A dedicated machine user like `gitops-bot` also works, but it is still a user identity that needs lifecycle management.

---

## Step 11: Synchronization and Verification

In the Argo CD UI:

* Click **Refresh**
* Application should show **OutOfSync**
* Click **Synchronize**

To access the application:

```bash
kubectl port-forward -n app1-ns svc/app1-svc 8081:80
```

---

## Argo CD Features With Demos

This section is a **direct continuation of the demo we just concluded**.
So far, we deployed `app1` using an Argo CD `Application` CRD and performed **manual syncs** to understand the Git vs cluster reconciliation model.

In this section, we evolve the **same application** to explore how Argo CD behaves when its core **sync automation features** are enabled.
No new application is introduced. We only extend the existing one.

---

## Baseline Application CRD

All changes in this section apply to the same Application definition:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app1
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/CloudWithVarJosh/cwvj-app1-config.git
    targetRevision: HEAD
    path: .
  destination:
    server: https://kubernetes.default.svc
    namespace: app1-ns
```

---

## Important Context

Argo CD ships with several **powerful automation features**, all of which are **disabled by default**.

This is an intentional design decision:

* GitOps systems should not make destructive or irreversible changes without explicit intent.
* Manual sync acts as a safety gate, allowing humans to review diffs and approve changes.

Not every project requires all features.
Enable them **only if the project demands it**, not because they are available.

A feature used blindly can easily become a bug.

---

## Features Covered

![Alt text](/images/4b.png)

We will discuss and demo the following **official Argo CD features**:

* **Automated Sync**
* **Pruning**
* **Self-healing**

Each feature is introduced incrementally using the **same application**, so the effect of each change is isolated and easy to reason about.

---

# Automated Sync

**Purpose:** Automatically apply approved Git changes to the cluster without requiring manual synchronization.

* Removes the need to click **Synchronize** after every detected change
* Shifts deployment approval responsibility fully to Git workflows
* Allows Argo CD to act immediately once desired state is detected

**What it controls:** Speed and consistency of applying Git-defined desired state.

* Determines how quickly Git changes propagate into Kubernetes
* Relies on reconciliation cycles for detection, not a fixed sync timer
* Ensures consistent behavior across environments once enabled

**Default:** Disabled, requiring manual approval for every detected configuration drift.

* Encourages operators to review diffs before applying changes
* Reduces risk during early GitOps adoption or migrations
* Prevents unintended rollouts caused by incorrect commits

**Production insight:** Best used when Git review processes are already trusted.

* Code review, not Argo CD, becomes the real approval gate
* Auto-sync amplifies both good and bad Git practices

> **Note:** Even when **automated sync** is not enabled, **Argo CD continuously reconciles** the application by checking the **desired state in Git** against the **live state in the cluster** approximately every **3 minutes**. In this mode, Argo CD only updates the **sync status** (InSync or OutOfSync) and does **not** apply any changes. When **automated sync** is enabled, Argo CD not only detects drift but also **automatically applies** the Git-defined changes to the cluster.

---

## Demo: Automated Sync

### Step A: Enable Automated Sync

Add the following to the existing `Application` CRD:

```yaml
spec:
  syncPolicy:
    automated: {}
```

Apply the change:

```bash
kubectl apply -f app1-app-crd.yaml
```

You can verify this:

* Using `kubectl get applications -n argocd`
* Or via Argo CD UI → Application → Details

---

### Step B: Simulate a real DevOps workflow

Modify the Deployment manifest in the config repo:

* Change replica count from `1` to `2`

Commit and push the change:

```bash
git add .
git commit -m "Changed the replica count from 1 to 2"
git push origin main
```

This mimics how a DevOps Engineer would normally introduce a change.

---



### Step C: Observe Behavior

* Argo CD reconciles application state approximately every **3 minutes** by default (`timeout.reconciliation: 180s`).
* Auto-sync is **event-driven**, not time-scheduled. It triggers immediately **after** a change is detected.
* If a Git commit occurs just after a reconciliation cycle, it will be picked up during the **next** reconciliation run.
* Once the change is detected and the application becomes **OutOfSync**, Argo CD automatically applies the desired state from Git.

Click **Refresh** in the Argo CD UI to force an immediate Git check.
Note that **Refresh** only re-evaluates Git and live state; it does **not** manually apply changes like **Synchronize**.

Verify the result in the cluster:

```bash
kubectl get pods -n app1-ns
```

You should now see **2 running replicas**, matching the desired state defined in Git.

> **Refresh** asks Argo CD to re-check Git and cluster state.
> **Hard Refresh** forces Argo CD to forget cache and recalculate everything.


---

# Pruning

**Purpose:** Automatically delete Kubernetes resources removed intentionally from Git.

* Treats Git deletions as explicit lifecycle decisions
* Prevents leftover resources after architectural changes
* Keeps cluster state aligned with declared desired state

**What it controls:** Lifecycle cleanup of obsolete or temporary resources.

* Removes unused Services, Deployments, or ConfigMaps
* Helps avoid configuration drift caused by stale components
* Supports clean transitions during routing or platform upgrades

**Default:** Disabled to avoid accidental or destructive deletions.

* Protects clusters from mistaken file removals
* Avoids impact from partial commits or incorrect merges
* Prioritizes safety over strict enforcement

**Production insight:** Enable only when Git represents lifecycle intent, not just config.

* Teams must treat deletions as deliberate, reviewed changes
* Pruning assumes Git accurately models desired existence

---

## Demo: Pruning

Before we demonstrate pruning, let’s establish **why** a resource would be removed from Git in the first place.

So far, the **ClusterIP Service** was created purely to support **port-forwarding** during development and demos. In real projects, this is very common. Teams often start with:

* A temporary ClusterIP service for local testing
* Port-forwarding for validation

Now assume the application is moving forward:

* You are upgrading to **Ingress** or **Gateway API**
* Traffic will no longer flow through this ClusterIP
* The Service is no longer part of the desired architecture

At this point, keeping the Service around would be unnecessary.
This is exactly the kind of scenario where **pruning** becomes relevant.

---

### Step A: Enable Pruning

Update the Application CRD:

```yaml
spec:
  syncPolicy:
    automated:
      prune: true
```

Apply the change:

```bash
kubectl apply -f app1-app-crd.yaml
```

---

### Step B: Remove the obsolete resource from Git

Since the ClusterIP Service is no longer required, remove its manifest from the configuration repository:

```bash
rm app1-svc.yaml
git add .
git commit -m "Removed ClusterIP service after ingress upgrade"
git push origin main
```

This represents a **deliberate architectural decision**, not an accidental deletion.

---

### Step C: Observe behavior

* Argo CD detects that the Service manifest has been removed from Git.
* Because pruning is enabled and Git is the source of truth:

  * Argo CD automatically deletes the corresponding Service from the cluster.

Verify:

```bash
kubectl get svc -n app1-ns
```

The ClusterIP Service no longer exists in the cluster.

---

### Key takeaway

> With pruning enabled, Argo CD treats Git deletions as intentional and cleans up obsolete resources automatically.

This is what allows GitOps systems to **evolve architectures safely** without leaving behind unused infrastructure.


---

## What We Observed During the Demo (Important Argo CD Behavior)

During this demo, we intentionally made incremental changes to the **Application CRD** to better understand how Argo CD behaves in real scenarios. In production environments, Application CRDs are usually **stabilized early** and are not modified frequently. Most day-to-day changes happen only in workload manifests. However, because we were learning, we introduced changes step by step, which surfaced an important and subtle Argo CD behavior.

### Refresh vs Sync: A Critical Distinction

One key observation is the role of **Refresh** versus **Sync** in Argo CD:

* **Refresh** only compares the desired state in Git with the live state in the cluster.
* It updates the **sync status** (InSync / OutOfSync) but **never applies changes**.
* **Actual reconciliation** of resources happens only during a **manual sync** or an **automated sync** operation.

In our case, Refresh correctly showed the application as **OutOfSync**, which confirmed that Argo CD had detected the difference between Git and the cluster.

### Why Pruning Did Not Happen Immediately

We observed that pruning did not occur even though:

* `prune: true` was added to the Application CRD
* The Service manifest was deleted from Git
* Automated sync was already enabled

This behavior is intentional.

Argo CD evaluates **whether pruning is allowed only at the start of a sync operation**. The sync that applied `prune: true` had already begun **before pruning was enabled** in the live Application spec. Because sync semantics are locked at sync start, Argo CD could not perform pruning during that same cycle.

As a result:

* The commit that **enabled pruning** could not prune anything
* Pruning became effective **only after** the Application spec was updated
* A **subsequent sync trigger** was required for pruning to act

This aligns with Argo CD’s conservative design, which prevents a single Git commit from both enabling destructive behavior and deleting resources in the same reconciliation cycle.

### Why the Next Commit Worked

In the subsequent push, we changed the replica count from **2 to 3** and committed the change. This triggered a new automated sync cycle. At this point:

* Pruning was already enabled in the live Application spec
* Argo CD evaluated deletions at sync start
* The replica count was updated successfully
* The previously removed ClusterIP Service was **pruned from the cluster**

This confirmed that pruning works as expected **once it is already enabled before the sync begins**.

### Takeaway

> Pruning is evaluated only at the **start of a sync**, not during Refresh and not dynamically during an ongoing sync.

This behavior, while not explicitly documented, is consistent with Argo CD’s sync model and reinforces an important GitOps principle:

* **Configuration changes that alter reconciliation behavior must be applied first**
* **Destructive actions happen only in subsequent sync cycles**

Understanding this nuance helps avoid confusion during demos and prevents surprises in production GitOps workflows.

---

## Troubleshooting: Application Not Appearing in ArgoCD UI

### Issue
Application CRD exists in Git repository but does not appear in ArgoCD UI even after pushing changes.

### Root Cause
ArgoCD does not auto-discover Application CRDs in Git repositories. The Application resource must exist in the Kubernetes cluster first to tell ArgoCD what to monitor. This is a bootstrap pattern by design for security and control.

### Why This Happens
1. **Bootstrap Required**: Application CRD files in Git are just manifests. ArgoCD needs the Application resource created in the cluster via kubectl first.
2. **Security Design**: You explicitly control which applications get deployed to which clusters.
3. **File Location**: YAML files must be accessible to kubectl on the cluster machine.

### Action Items to Fix
1. **Clone repository on cluster machine**:
   ```bash
   git clone https://github.com/esarath/ArgoCD-Basics-To-Production.git
   cd ArgoCD-Basics-To-Production/04-PrivateRepo+SyncPruneSelfHeal/app1-config
   ```

2. **Apply repository secret for private repo authentication**:
   ```bash
   kubectl apply -f argocd-repo-secret.yaml
   ```

3. **Apply Application CRD to cluster**:
   ```bash
   kubectl apply -f app1-app-crd.yaml
   ```

4. **Add repository to ArgoCD** (if not already added):
   ```bash
   argocd repo add https://github.com/esarath/ArgoCD-Basics-To-Production.git \
     --name app1-config-repo \
     --username esarath \
     --password <GITHUB-PAT>
   ```

### Key Takeaway
ArgoCD requires a one-time manual bootstrap (kubectl apply) to create the Application resource. After that, GitOps takes over and all future changes are automated. This bootstrap step is necessary only once per application.

---

# Self-healing

**Purpose:** Automatically revert manual cluster changes to match Git-defined desired state.

* Treats all out-of-band cluster modifications as temporary
* Enforces Git as the only source of long-term truth
* Eliminates configuration drift introduced through kubectl actions

**What it controls:** Continuous enforcement of runtime configuration consistency.

* Detects differences between live state and Git state
* Re-applies desired state without manual intervention
* Prevents silent divergence across environments

**Default:** Disabled to allow debugging and live-state investigation.

* Enables engineers to temporarily inspect or modify workloads
* Avoids masking root causes during incidents
* Allows deliberate stabilization before committing fixes to Git

**Production insight:** With self-healing enabled, manual changes are never permanent.

* Debug first, then commit to Git
* Cluster is treated as read-only at runtime

> **Note:** **Pruning** and **self-healing** work only as part of **automated sync**. When automated sync is disabled, Argo CD can **detect drift or missing resources** and mark the application **OutOfSync**, but it will **not automatically delete or correct anything**. Automatic pruning and self-healing occur **only when automated sync is enabled**; otherwise, these actions require a **manual sync**.

---

## Demo: Self-healing

Before we enable self-healing, it is important to understand **where the source of truth lives**.

The **Application CRD itself is also managed by Argo CD** and is tracked from the **configuration repository**. Since **automated sync is already enabled**, any local or imperative changes that are **not committed to Git** will eventually be reverted.

> In GitOps, even Argo CD’s own configuration must live in Git.

Keep this in mind as you follow the steps below.

---

### Step A: Enable Self-healing

Update the Application CRD manifest:

```yaml
spec:
  syncPolicy:
    automated:
      selfHeal: true
```

⚠️ **Important:**
Do not stop at `kubectl apply`.

Because the Application CRD is already under **automated sync**, you must also **commit this change to Git**.
If you only apply it locally and do not commit:

* Argo CD will re-read the Application CRD from Git
* It will detect a mismatch
* It will revert the Application back to the version **without `selfHeal`**

Commit and push the change:

```bash
git add app1-app-crd.yaml
git commit -m "Enable self-healing for app1"
git push origin main
```

Now the desired state for the Application itself is correctly defined in Git.

---

### Step B: Introduce manual drift

Manually scale the Deployment in the cluster:

```bash
kubectl scale deployment app1 --replicas=1 -n app1-ns
```

This creates drift:

* Desired state in Git: replicas = `2`
* Live cluster state: replicas = `1`

---

### Step C: Observe behavior

* Argo CD detects drift in the live cluster state.
* Since **self-healing is enabled in Git**, Argo CD re-applies the desired state.
* Replica count is automatically restored to `2`.

Verify:

```bash
kubectl get pods -n app1-ns
```

---

### Key takeaway

> If you change Argo CD behavior but do not commit it to Git, Argo CD will undo your change.

This is a **classic GitOps pitfall** and one of the most important concepts to internalize early:

* **Git is always the final authority**
* Even for Argo CD’s own configuration

---

# Enabling All Three Features Together

A commonly used production configuration:

```yaml
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

This configuration results in:

* Automatic application of Git changes
* Automatic deletion of removed resources
* Automatic correction of manual drift

---

## Final Mental Model

* **Automated Sync** applies Git changes automatically
* **Pruning** removes resources deleted from Git
* **Self-healing** corrects cluster drift

Automation should be **intentional and contextual**, not assumed by default.

This completes the Argo CD **sync feature trilogy**, demonstrated using a single evolving application, exactly how GitOps is applied in real-world environments.

---

## Conclusion

In this lecture, we implemented a **full production-style Argo CD workflow**, starting from private access and ending with automated reconciliation.

We saw that:

* Argo CD requires explicit credentials to access private configuration repositories
* Private container images are pulled by Kubernetes using registry secrets, not by Argo CD
* Kubernetes secrets are delivery mechanisms, not security boundaries
* Git remains the single source of truth even when secrets cannot be stored in it

On top of this secure foundation, we enabled and demonstrated Argo CD’s **advanced sync features**:

* **Automated Sync** to apply Git changes without manual intervention
* **Pruning** to remove resources deleted from Git
* **Self-healing** to correct manual drift in the cluster

Together, these features transform Argo CD from a deployment tool into a **continuous reconciliation system**, enforcing desired state consistently and predictably.

Most importantly, this lecture establishes a core GitOps principle that everything else builds upon:

> Argo CD manages desired state.
> Access and credentials are platform responsibilities.

With private access, reconciliation, and automation now clearly understood, subsequent lectures can safely build on this foundation to explore **external secrets, CI-driven workflows, and large-scale GitOps patterns**.

---

## References

The following official references back every concept covered in this lecture:

* Argo CD – Private Repositories
  [https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/](https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/)

* Argo CD – Application CRD
  [https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/)

* Argo CD – Automated Sync, Pruning, Self-healing
  [https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)

* Kubernetes – Secrets
  [https://kubernetes.io/docs/concepts/configuration/secret/](https://kubernetes.io/docs/concepts/configuration/secret/)

* Kubernetes – Image Pull Secrets
  [https://kubernetes.io/docs/concepts/containers/images/#specifying-imagepullsecrets-on-a-pod](https://kubernetes.io/docs/concepts/containers/images/#specifying-imagepullsecrets-on-a-pod)

* Docker – Access Tokens
  [https://docs.docker.com/security/for-developers/access-tokens/](https://docs.docker.com/security/for-developers/access-tokens/)

These references reflect **how Argo CD and Kubernetes are intended to be used in production**, not just for demos.

---