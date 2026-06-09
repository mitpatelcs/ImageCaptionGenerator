# ECS Cluster + Service Setup

This is the final step: create an **ECS cluster** (a logical group for your tasks),
register the **task definition**, and create a **service** that runs the container
and connects it to the ALB.

Do this **after** the image is in ECR ([`ecr-commands.md`](ecr-commands.md)) and the
ALB/target group exist ([`alb-setup-guide.md`](alb-setup-guide.md)).

> You will reuse: `$TG_ARN`, `$ECS_SG`, and your two subnets (`<SUBNET_A>`, `<SUBNET_B>`).

---

## Step 1 — Create the CloudWatch log group

The task definition writes logs here. Create it once:

```bash
aws logs create-log-group --log-group-name /ecs/image-caption-generator
```

---

## Step 2 — Create the ECS cluster (Fargate)

```bash
aws ecs create-cluster --cluster-name image-caption-cluster
```

---

## Step 3 — Fill in and register the task definition

1. Open [`ecs-task-definition.json`](ecs-task-definition.json).
2. Replace `<AWS_ACCOUNT_ID>` and `<REGION>` (in `image`, `executionRoleArn`, and
   `awslogs-region`).
3. Register it:

```bash
aws ecs register-task-definition \
  --cli-input-json file://deployment/ecs-task-definition.json
```

This prints a `taskDefinitionArn` ending in `image-caption-task:1` (the revision
number goes up each time you register).

**About the size (`cpu: 2048`, `memory: 4096` = 2 vCPU / 4 GB):** the app loads
VGG16 (~500 MB) + the caption model + TensorFlow, so it needs a few GB of RAM.
- For lower cost / light traffic you can try **1 vCPU / 3 GB** (`"cpu":"1024"`,
  `"memory":"3072"`) — captions will be a bit slower.
- For faster captions, **2 vCPU / 8 GB** (`"memory":"8192"`).

---

## Step 4 — Create the service (behind the ALB)

```bash
aws ecs create-service \
  --cluster image-caption-cluster \
  --service-name image-caption-service \
  --task-definition image-caption-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_A>,<SUBNET_B>],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=image-caption-container,containerPort=8000"
```

Key options explained:
- `--desired-count 1` → run one copy of the container (raise it for more capacity).
- `assignPublicIp=ENABLED` → gives the task internet access so it can **pull the
  image from ECR** and call **gTTS** for audio (simplest setup; uses public
  subnets). The more secure alternative is private subnets + a NAT gateway (extra cost).
- `--load-balancers ...` → registers the task with the ALB target group so traffic
  flows ALB → container.

---

## Step 5 — Watch it come up

```bash
# Service + task status
aws ecs describe-services --cluster image-caption-cluster \
  --services image-caption-service \
  --query "services[0].{running:runningCount,desired:desiredCount,status:status}"

# Target health (wait until "healthy")
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[].TargetHealth.State"
```

It can take 1–3 minutes for the task to start, register, and pass health checks.
When the target shows **`healthy`**, open the ALB DNS name in a browser.

If something is wrong, read the logs:
```bash
aws logs tail /ecs/image-caption-generator --follow
```

---

## Updating the app later (new image)

After pushing a new image to ECR (same `:latest` tag):

```bash
aws ecs update-service \
  --cluster image-caption-cluster \
  --service image-caption-service \
  --force-new-deployment
```

ECS does a rolling update: it starts a new task, waits for it to be healthy, then
stops the old one — no downtime.

---

## Pausing to save money

```bash
# Stop running the container (you stop paying for the task; ALB still costs)
aws ecs update-service --cluster image-caption-cluster \
  --service image-caption-service --desired-count 0

# Resume later
aws ecs update-service --cluster image-caption-cluster \
  --service image-caption-service --desired-count 1
```

Full teardown is in [`deployment-guide.md`](deployment-guide.md) (section 8).
