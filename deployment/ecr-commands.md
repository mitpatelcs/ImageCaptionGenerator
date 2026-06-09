# ECR — Build & Push the Docker Image

**Amazon ECR** is a private container registry in your AWS account. ECS pulls the
image from here. Below are the exact commands to create the repo and push the image
you built in Phase 5.

> Replace `<AWS_ACCOUNT_ID>` and `<REGION>` (e.g. `us-east-1`) with your values.
> Run these from the project root (the folder with the `Dockerfile`).

---

## Step 1 — Create the ECR repository (one time)

```bash
aws ecr create-repository \
  --repository-name image-caption-generator \
  --region <REGION>
```

This prints a `repositoryUri` like:
`<AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/image-caption-generator`

---

## Step 2 — Log Docker in to ECR

This gives your local Docker permission to push to your private registry.

```bash
aws ecr get-login-password --region <REGION> \
  | docker login --username AWS \
    --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
```

You should see `Login Succeeded`.

---

## Step 3 — Build the image (with the model baked in)

Build **on the machine that has the trained artifacts** (`artifacts/model.h5`,
etc.), so the model ends up inside the image.

```bash
docker build -t image-caption-generator:latest .
```

> On Apple Silicon (M1/M2/M3) Macs, ECS Fargate runs on **x86_64**, so build for
> that platform to avoid "exec format error":
>
> ```bash
> docker build --platform linux/amd64 -t image-caption-generator:latest .
> ```

---

## Step 4 — Tag the image for ECR

```bash
docker tag image-caption-generator:latest \
  <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/image-caption-generator:latest
```

---

## Step 5 — Push the image

```bash
docker push \
  <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/image-caption-generator:latest
```

The first push uploads the whole image (~3 GB, so it can take a while). Later
pushes only upload the layers that changed.

---

## Step 6 — Verify it's there

```bash
aws ecr list-images \
  --repository-name image-caption-generator \
  --region <REGION>
```

You should see your `latest` tag.

---

## The full image URI (you'll need this next)

```
<AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/image-caption-generator:latest
```

Put this value into the `"image"` field of
[`ecs-task-definition.json`](ecs-task-definition.json).

---

## Pushing a new version later

Whenever you retrain or change code, repeat **Steps 3–5** (build → tag → push).
Then tell ECS to use the new image by forcing a new deployment:

```bash
aws ecs update-service \
  --cluster image-caption-cluster \
  --service image-caption-service \
  --force-new-deployment
```
