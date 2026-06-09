# Deployment Guide (master walkthrough)

This is the top-level guide. It ties together the other documents in this folder
and gives you the **exact order** to deploy the Image Caption Generator to AWS
using **ECR + ECS Fargate + ALB**.

> ⚠️ This guide *prepares* everything. Running the commands will create real AWS
> resources that **cost money**. Do not run them unless you intend to deploy, and
> remember to clean up afterwards (see the last section).

---

## 0. Placeholders used everywhere

Replace these with your real values when you run the commands:

| Placeholder | Example | Meaning |
|---|---|---|
| `<AWS_ACCOUNT_ID>` | `123456789012` | Your 12-digit AWS account id |
| `<REGION>` | `us-east-1` | The AWS region you deploy in |
| `<ECR_REPO>` | `image-caption-generator` | ECR repository name |
| `<IMAGE_URI>` | `<AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/<ECR_REPO>:latest` | Full image address |

Consistent names used across all docs: cluster `image-caption-cluster`, service
`image-caption-service`, task family `image-caption-task`, container
`image-caption-container`, ALB `image-caption-alb`, target group `image-caption-tg`.

---

## 1. Prerequisites

- An **AWS account** with admin (or sufficient) permissions.
- **AWS CLI v2** installed and configured: `aws configure` (set key, secret, region).
- **Docker** installed locally (you already used it in Phase 5).
- **Trained artifacts present locally**: `artifacts/model.h5`, `tokenizer.pkl`,
  `mapping.pkl`, `all_captions.pkl`. These are git-ignored, so they only exist on
  the machine where you trained — see the note in section 3.

Quick check:
```bash
aws sts get-caller-identity     # confirms the CLI is authenticated
docker --version
ls artifacts/model.h5           # confirms the model exists
```

---

## 2. Deployment order (the whole flow)

```
Build image  →  Push to ECR  →  Create IAM role  →  Register task def
     →  Create ALB + target group + listener  →  Create ECS cluster + service
     →  Test via ALB URL  →  (later) Clean up
```

| Step | What you do | Doc to follow |
|---|---|---|
| 1 | Create the ECR repo and push the image | [`ecr-commands.md`](ecr-commands.md) |
| 2 | Create the `ecsTaskExecutionRole` IAM role | section 4 below |
| 3 | Edit + register the task definition | [`ecs-task-definition.json`](ecs-task-definition.json) |
| 4 | Create the load balancer + target group | [`alb-setup-guide.md`](alb-setup-guide.md) |
| 5 | Create the cluster + service | [`ecs-service-guide.md`](ecs-service-guide.md) |
| 6 | Open the ALB DNS name in a browser | section 5 below |

---

## 3. Important: getting the model into the image

The trained model (`artifacts/model.h5`) is **not in git** (it is git-ignored). So:

- ✅ **Recommended (simplest):** build the Docker image **on your machine** (where
  the artifacts exist) and push that image to ECR. The model is baked into the
  image, so ECS just runs it. This is what [`ecr-commands.md`](ecr-commands.md) does.
- 🔁 **Alternative (advanced):** store the artifacts in an **S3 bucket**, and have
  your build step download them before `docker build`. Useful if a CI server (which
  has no model) needs to build the deployable image. See
  [`github-actions-guide.md`](github-actions-guide.md).

> The GitHub Actions CI (Phase 7) only **validates** that the image *builds*; it
> does not produce the deployable image, because the runner has no model file.

---

## 4. Create the IAM execution role (one time)

ECS needs a role that lets it pull from ECR and write logs.

```bash
# Trust policy: allow ECS tasks to assume this role
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Principal": { "Service": "ecs-tasks.amazonaws.com" },
      "Action": "sts:AssumeRole" }
  ]
}
EOF

aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

(If `ecsTaskExecutionRole` already exists in your account, skip this step.)

---

## 5. Test the deployment

After the service is running and the target group is **healthy**:

```bash
# Get the ALB public DNS name
aws elbv2 describe-load-balancers \
  --names image-caption-alb \
  --query "LoadBalancers[0].DNSName" --output text
```

Open `http://<that-dns-name>/` in a browser → you should see the frontend.
Then upload an image and generate a caption.

```bash
curl http://<that-dns-name>/health      # -> {"status":"ok"}
```

---

## 6. Environment variables

The app is intentionally simple and needs **no required environment variables** —
all paths are relative and the port is fixed at 8000 in the Dockerfile.

Optional / good-to-know:

| Variable | Where | Purpose |
|---|---|---|
| `PYTHONUNBUFFERED=1` | already set in the Dockerfile | Immediate logs in CloudWatch |
| (future) `MODEL_PATH`, `PORT` | task definition `environment` | If you later make paths/port configurable |
| AWS credentials | **do NOT put in the container** | ECS uses the IAM execution role instead |

gTTS (audio) calls Google over the internet, so the task needs **outbound internet
access** (public subnet + public IP, or a NAT gateway). If it has none, captions
still work and only audio is skipped.

---

## 7. Cost overview (high level, us-east-1, on-demand)

These are rough monthly estimates for a **single small task running 24/7**. Actual
cost depends on region, uptime, and traffic.

| Resource | Rough cost |
|---|---|
| ECS Fargate task (2 vCPU, 4 GB), 24/7 | **~$70 / month** (≈ $0.10/hr) |
| Application Load Balancer | **~$16–22 / month** + small per-request fee |
| ECR storage | ~$0.10 / GB-month (image ≈ 3 GB → ~$0.30/mo) |
| CloudWatch Logs | a few cents to ~$1 / month for low volume |
| Data transfer out | first 100 GB/mo free tier, then ~$0.09/GB |

**Ways to keep it cheap:**
- Set the service **desired count to 0** when not demoing (you pay ~nothing for the
  task while it's stopped; the ALB still costs).
- Use **1 vCPU / 3 GB** instead of 2/4 for lower cost (slower captions).
- **Delete everything** after the demo (next section).

---

## 8. Cleanup / teardown (avoid surprise bills)

Delete in roughly the reverse order of creation:

```bash
# 1. Scale the service to 0, then delete it
aws ecs update-service --cluster image-caption-cluster \
  --service image-caption-service --desired-count 0
aws ecs delete-service --cluster image-caption-cluster \
  --service image-caption-service --force

# 2. Delete the cluster
aws ecs delete-cluster --cluster image-caption-cluster

# 3. Delete the ALB, listener, and target group (see alb-setup-guide.md for ARNs)
aws elbv2 delete-load-balancer --load-balancer-arn <ALB_ARN>
aws elbv2 delete-target-group --target-group-arn <TG_ARN>

# 4. Delete the ECR repo (and its images)
aws ecr delete-repository --repository-name <ECR_REPO> --force

# 5. (Optional) delete the CloudWatch log group and IAM role
aws logs delete-log-group --log-group-name /ecs/image-caption-generator
```

> Tip: the ALB is the main thing that costs money even when idle — delete it first
> if you're done.
