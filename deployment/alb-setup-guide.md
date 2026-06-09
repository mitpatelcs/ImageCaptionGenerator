# Application Load Balancer (ALB) Setup

The **ALB** is the public front door. It receives traffic on port 80 and forwards
it to your container on port 8000. It also **health-checks** each container at
`/health` and only sends traffic to healthy ones.

Do this **before** creating the ECS service, because the service needs the target
group ARN.

> Replace `<REGION>`, `<VPC_ID>`, `<SUBNET_A>`, `<SUBNET_B>` with your values.
> Use **two public subnets in different Availability Zones** (an ALB requires ≥2).

---

## Find your default VPC and subnets (if you don't know them)

```bash
# Default VPC id
aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
  --query "Vpcs[0].VpcId" --output text

# Subnets in that VPC (pick two in different AZs)
aws ec2 describe-subnets --filters Name=vpc-id,Values=<VPC_ID> \
  --query "Subnets[].{Id:SubnetId,AZ:AvailabilityZone}" --output table
```

---

## Step 1 — Create two security groups (firewalls)

**ALB security group** — allow public web traffic in:
```bash
ALB_SG=$(aws ec2 create-security-group \
  --group-name image-caption-alb-sg \
  --description "Allow HTTP to the ALB" \
  --vpc-id <VPC_ID> --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG --protocol tcp --port 80 --cidr 0.0.0.0/0
```

**ECS task security group** — allow traffic **only from the ALB** on port 8000:
```bash
ECS_SG=$(aws ec2 create-security-group \
  --group-name image-caption-ecs-sg \
  --description "Allow ALB to reach the container" \
  --vpc-id <VPC_ID> --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG --protocol tcp --port 8000 --source-group $ALB_SG
```

> Keep the `$ALB_SG` and `$ECS_SG` values — you'll need `$ECS_SG` in the service guide.

---

## Step 2 — Create the load balancer

```bash
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name image-caption-alb \
  --type application \
  --scheme internet-facing \
  --subnets <SUBNET_A> <SUBNET_B> \
  --security-groups $ALB_SG \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)
```

---

## Step 3 — Create the target group

This is where the ALB sends traffic. Important: **type `ip`** (Fargate uses IPs),
port **8000**, and health check path **`/health`**.

```bash
TG_ARN=$(aws elbv2 create-target-group \
  --name image-caption-tg \
  --protocol HTTP --port 8000 \
  --vpc-id <VPC_ID> \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --query "TargetGroups[0].TargetGroupArn" --output text)
```

> The model loads on the **first request**, which can be slow. The `/health`
> endpoint is lightweight (it does **not** load the model), so health checks stay
> fast and the task is marked healthy quickly.

---

## Step 4 — Create a listener (port 80 → target group)

```bash
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

---

## Step 5 — Note the values you need next

```bash
echo "Target Group ARN: $TG_ARN"      # used by the ECS service
echo "ECS Security Group: $ECS_SG"    # used by the ECS service

# Public URL of your app:
aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN \
  --query "LoadBalancers[0].DNSName" --output text
```

Open `http://<that-dns-name>/` after the ECS service is running and healthy.

---

## (Optional, later) Add HTTPS

For a real domain + HTTPS you would: request a certificate in **AWS Certificate
Manager (ACM)**, then add a second listener on port **443** that forwards to the
same target group, and point your domain at the ALB with **Route 53**. Not needed
for a portfolio demo.
