# GitHub Actions (CI/CD) Guide

This explains the CI workflow at
[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml): what it does,
how to turn it on, and how to extend it into a real AWS deployment later.

---

## What is GitHub Actions?

GitHub Actions is GitHub's built-in automation. You put a YAML file in
`.github/workflows/`, and GitHub automatically runs it on a fresh cloud machine
("runner") when something happens — for example, every time you push code.

A file = a **workflow**. A workflow has **jobs**, and each job has **steps**
(checkout code, install Python, run a command, etc.).

---

## What our workflow does (today)

It runs on every push / pull request to `main` (and can be run manually). It does
**build + validation only — no deployment**:

```
push to main
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ GitHub Actions runner (ubuntu-latest)                    │
│  1. Checkout repository                                   │
│  2. Set up Python 3.10                                    │
│  3. Install requirements.txt                              │
│  4. Run tests (skips automatically if tests/ is empty)   │
│  5. Build the Docker image                                │
│  6. Validate the image built successfully                 │
└─────────────────────────────────────────────────────────┘
     │
     ▼
  ✅ green check on the commit  (or ❌ if something broke)
```

This catches problems early: if a dependency is broken or the Dockerfile stops
building, the workflow fails and you see it on the commit/PR.

> Note: the runner does **not** have the trained model (`artifacts/model.h5` is
> git-ignored), so the image it builds is for **validation only**, not for
> deployment. The deployable image (with the model baked in) is built locally and
> pushed to ECR — see [`ecr-commands.md`](ecr-commands.md).

---

## How to enable it

It's automatic — just commit and push the workflow file:

```bash
git add .github/workflows/deploy.yml
git commit -m "Add CI workflow"
git push
```

Then open your repo on GitHub → **Actions** tab → you'll see the run. No extra
setup is needed for the build-and-validate workflow (it uses no secrets).

---

## Required GitHub Secrets (only for the FUTURE deploy step)

The deploy steps are commented out in `deploy.yml`. To enable them later, add these
in your repo under **Settings → Secrets and variables → Actions → New repository
secret**:

| Secret name | Example value | Purpose |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | AWS programmatic access key |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` | Matching secret key |
| `AWS_REGION` | `us-east-1` | Region to deploy in |
| `ECR_REPOSITORY` | `image-caption-generator` | ECR repo name |

> Best practice: create a dedicated IAM user (or use OIDC) with **only** the
> permissions needed (ECR push + `ecs:UpdateService`), not your root account.
> Never commit these values into the repo — Secrets are encrypted and hidden in logs.

---

## How to connect ECS deployment later

The bottom of `deploy.yml` has a ready-to-uncomment block. The flow it adds:

```
build & validate  ──►  configure AWS creds  ──►  login to ECR
      ──►  build + push image to ECR  ──►  force new ECS deployment
                                                  │
                                                  ▼
                                       ECS rolling update → live
```

Steps to turn it on:
1. Add the 4 secrets above.
2. Make sure the AWS resources exist (ECR repo, ECS cluster `image-caption-cluster`,
   service `image-caption-service`) — see the other docs in this folder.
3. Uncomment the `FUTURE` block in `deploy.yml`.
4. Decide how the **model** gets into the CI-built image. Two options:
   - **Pull artifacts from S3** in the workflow before `docker build`
     (e.g. `aws s3 cp s3://<bucket>/model.h5 artifacts/model.h5`), or
   - Keep building/pushing the deployable image **locally** and let CI handle only
     non-deploy validation.

That's it — pushing to `main` would then build, push to ECR, and trigger a rolling
ECS update automatically.

---

## Common gotchas

- **First Docker build is slow** in CI (installs TensorFlow + downloads VGG16
  weights). That's expected; later runs reuse pip cache where possible.
- **`exec format error` on ECS** → you built an ARM image on an Apple-Silicon Mac.
  Build with `--platform linux/amd64` (see [`ecr-commands.md`](ecr-commands.md)).
- **Workflow didn't run** → confirm the file is at exactly
  `.github/workflows/deploy.yml` on the `main` branch.
