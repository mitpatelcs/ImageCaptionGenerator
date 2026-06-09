# Deployment Architecture

This document explains, in simple terms, how the Image Caption Generator runs on
AWS. The goal is to take the Docker container we already built and run it on the
cloud so anyone can use it from a public URL.

---

## The big picture

```
                          ┌──────────────────────────────────────────────┐
                          │                  AWS Cloud                     │
                          │                                                │
  User's browser          │   ┌────────────┐         ┌────────────────┐   │
  (uploads an image)      │   │   Amazon   │  pull   │   ECS Fargate  │   │
        │                 │   │    ECR     │◄────────│     Service    │   │
        │   HTTP (80)     │   │ (image     │  image  │ (runs N copies │   │
        ▼                 │   │  registry) │         │  of container) │   │
 ┌─────────────┐  HTTP    │   └────────────┘         │  port 8000     │   │
 │ Application │─────────►│                          │  ┌───────────┐ │   │
 │    Load     │  :8000   │                          │  │ FastAPI + │ │   │
 │  Balancer   │◄─────────│──────────────────────────┼─►│ frontend  │ │   │
 │   (ALB)     │  health  │      /health check       │  │ + model   │ │   │
 └─────────────┘          │                          │  └───────────┘ │   │
        ▲                 │                          └────────┬───────┘   │
        │ public DNS name │                                   │ logs      │
        │                 │                          ┌────────▼───────┐   │
   internet-facing        │                          │  CloudWatch    │   │
                          │                          │     Logs       │   │
                          │                          └────────────────┘   │
                          └──────────────────────────────────────────────┘
```

**Request flow:** User → ALB (public, port 80) → ECS Fargate task (container, port
8000) → FastAPI serves the frontend and generates the caption → response goes back
the same way.

---

## Each AWS service, explained simply

| Service | What it is | Why we use it here |
|---|---|---|
| **Amazon ECR** (Elastic Container Registry) | A private "Docker Hub" inside your AWS account. | Stores our built Docker image so ECS can pull and run it. |
| **Amazon ECS** (Elastic Container Service) | A service that runs Docker containers for you. | Runs our container and keeps it alive/restarts it if it crashes. |
| **AWS Fargate** | A "serverless" way to run ECS containers — no servers (EC2) to manage. | We just say "give my container 2 vCPU + 4 GB" and AWS runs it. No machines to patch. |
| **Application Load Balancer (ALB)** | A managed load balancer that receives public traffic and forwards it to your containers. | Gives us one stable public URL, spreads traffic across container copies, and health-checks them. |
| **VPC / Subnets / Security Groups** | Your private network in AWS, its sub-networks, and firewall rules. | The ALB and containers live here; security groups control who can talk to whom. |
| **IAM Roles** | Permissions for AWS resources (not people). | The "execution role" lets ECS pull from ECR and write logs. |
| **CloudWatch Logs** | Centralized log storage. | We can read the container's logs (`uvicorn` output) to debug. |

---

## Why these choices (interview talking points)

- **Fargate over EC2:** no servers to manage, pay only while the task runs, perfect
  for a small portfolio app.
- **ALB over a public container IP:** stable DNS name, health checks, and easy to
  add HTTPS later. Fargate task IPs change on every restart — the ALB hides that.
- **ECR over Docker Hub:** private, in-account, integrates with ECS permissions.
- **One container serves both frontend and API:** the FastAPI app mounts the
  frontend at `/`, so there is no separate web server or S3 bucket to manage.

---

## Components we will create (in order)

1. **ECR repository** → see [`ecr-commands.md`](ecr-commands.md)
2. **IAM execution role** (`ecsTaskExecutionRole`) → see [`deployment-guide.md`](deployment-guide.md)
3. **ECS task definition** → see [`ecs-task-definition.json`](ecs-task-definition.json)
4. **ALB + target group + listener + security groups** → see [`alb-setup-guide.md`](alb-setup-guide.md)
5. **ECS cluster + service** → see [`ecs-service-guide.md`](ecs-service-guide.md)

The full end-to-end order is in [`deployment-guide.md`](deployment-guide.md).
