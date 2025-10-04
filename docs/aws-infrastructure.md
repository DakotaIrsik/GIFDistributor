# AWS Infrastructure Guide (Alternative Deployment)

> **Slug:** `infra-alt-aws`
> **Priority:** P1
> **Labels:** infra, cdn, docs

## Overview

This document provides a complete AWS-based infrastructure deployment plan for GIFDistributor as an alternative to the Cloudflare-first approach. This option is designed for teams already invested in AWS ecosystem or requiring AWS-specific features.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    CloudFront CDN                         │   │
│  │     (Global Edge Network + Origin Shield)                 │   │
│  └─────────────────┬────────────────────────┬────────────────┘   │
│                    │                        │                    │
│      ┌─────────────▼──────────┐  ┌─────────▼─────────────┐      │
│      │   S3 Buckets           │  │   API Gateway         │      │
│      │ (Media Storage)        │  │   + Lambda@Edge       │      │
│      │ - media-prod           │  │                       │      │
│      │ - cache-prod           │  └───────────┬───────────┘      │
│      │ - transcode-prod       │              │                  │
│      └────────────────────────┘              │                  │
│                                   ┌──────────▼───────────┐      │
│      ┌─────────────────────┐     │   ECS Fargate        │      │
│      │   DynamoDB          │◄────┤   (API Containers)   │      │
│      │ - metadata          │     │   + Auto Scaling     │      │
│      │ - analytics         │     └──────────────────────┘      │
│      │ - sessions          │                                    │
│      └─────────────────────┘     ┌──────────────────────┐      │
│                                   │   SQS + EventBridge  │      │
│      ┌─────────────────────┐     │   (Job Queue)        │      │
│      │   ElastiCache       │     └──────────┬───────────┘      │
│      │   (Redis)           │                │                  │
│      │ - rate limiting     │     ┌──────────▼───────────┐      │
│      │ - sessions          │     │   ECS Fargate        │      │
│      └─────────────────────┘     │   (Media Workers)    │      │
│                                   │   + ffmpeg           │      │
│                                   └──────────────────────┘      │
│                                                                  │
│      ┌─────────────────────┐     ┌──────────────────────┐      │
│      │   CloudWatch        │     │   Secrets Manager    │      │
│      │   (Logs + Metrics)  │     │   (API Keys, Creds)  │      │
│      └─────────────────────┘     └──────────────────────┘      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   End Users      │
                    └──────────────────┘
```

## Components

### 1. S3 Buckets (Object Storage)

S3 provides industry-standard object storage with rich feature set and multi-region replication options.

#### Primary Media Bucket (`gifdistributor-media-prod`)
- **Purpose**: Store original uploaded GIFs, MP4s, and source media
- **Access**: Private, CloudFront signed URLs only
- **Storage Class**: S3 Intelligent-Tiering (auto cost optimization)
- **Versioning**: Enabled for data protection
- **Replication**: Optional cross-region to `us-west-2` for DR
- **Custom Domain**: `cdn.gifdistributor.com` (via CloudFront)

#### Cache Bucket (`gifdistributor-cache-prod`)
- **Purpose**: Store CDN-optimized assets (compressed, resized)
- **Access**: Public via CloudFront only (bucket policy restricts direct access)
- **Storage Class**: S3 Standard (hot data, frequent access)
- **Lifecycle**: Transition to S3 Infrequent Access after 30 days, delete after 90 days
- **Custom Domain**: `cache.gifdistributor.com`

#### Transcode Bucket (`gifdistributor-transcode-prod`)
- **Purpose**: Store platform-specific renditions (Discord MP4, Slack GIF, etc.)
- **Access**: Private, signed URLs only
- **Storage Class**: S3 Standard → IA after 30 days
- **Lifecycle**: Delete after 90 days of no access
- **Object Tags**: Platform type for analytics

#### Logs Bucket (`gifdistributor-logs-prod`)
- **Purpose**: Store CloudFront access logs, application logs, audit trails
- **Access**: Private, analysis tools only
- **Storage Class**: S3 Standard → Glacier after 30 days
- **Lifecycle**: Delete after 180 days (compliance requirement)
- **Encryption**: SSE-S3 mandatory

### 2. CloudFront (CDN)

Global content delivery network with 450+ edge locations worldwide.

#### Distribution Configuration
- **Origins**:
  - S3 media bucket (OAI for private access)
  - API Gateway (custom origin)
  - S3 cache bucket (OAI)
- **Price Class**: Use All Edge Locations (or PriceClass_100 for cost savings)
- **SSL Certificate**: ACM certificate for `*.gifdistributor.com`
- **HTTP/3**: Enabled (QUIC protocol support)

#### Cache Behaviors
```
Priority | Path Pattern          | Origin        | TTL      | Compress
---------|----------------------|---------------|----------|----------
1        | /api/*               | API Gateway   | 0s       | Yes
2        | /assets/*.gif        | S3 Media      | 31536000 | Yes
3        | /assets/*.mp4        | S3 Media      | 31536000 | Yes
4        | /cache/*             | S3 Cache      | 86400    | Yes
5        | /transcode/*         | S3 Transcode  | 3600     | Yes
Default  | /*                   | S3 Media      | 3600     | Yes
```

#### Lambda@Edge Functions
- **Viewer Request**: Auth token validation, rate limiting
- **Origin Request**: Add custom headers, signed URL generation
- **Origin Response**: Security headers, custom error pages
- **Viewer Response**: Add CORS headers, cache control

### 3. ECS Fargate (API & Workers)

Serverless container orchestration for API and media processing workloads.

#### API Service (`gifdistributor-api-prod`)
- **Task Definition**:
  - **Image**: `gifdistributor/api:latest` (ECR)
  - **CPU**: 0.5 vCPU (scalable to 4 vCPU)
  - **Memory**: 1 GB (scalable to 8 GB)
  - **Port**: 3000 (HTTP)
- **Service Configuration**:
  - **Desired Count**: 2 (min), 10 (max)
  - **Auto Scaling**: Target tracking on CPU 70% + ALB requests
  - **Health Check**: `/health` endpoint
  - **Deployment**: Rolling update, 50% minimum healthy
- **Load Balancer**: Application Load Balancer (ALB)
  - Target Group with health checks
  - Sticky sessions via ALB cookie

#### Media Worker Service (`gifdistributor-workers-prod`)
- **Task Definition**:
  - **Image**: `gifdistributor/worker:latest` (includes ffmpeg)
  - **CPU**: 2 vCPU (scalable to 8 vCPU for 4K encoding)
  - **Memory**: 4 GB (scalable to 16 GB)
  - **Ephemeral Storage**: 100 GB (for temp video processing)
- **Service Configuration**:
  - **Desired Count**: 1 (min), 20 (max)
  - **Auto Scaling**: SQS queue depth metric (scale at >10 messages)
  - **Spot Instances**: 70% Spot + 30% On-Demand for cost optimization
- **Container Features**:
  - ffmpeg with hardware acceleration (if available)
  - S3 multipart upload for large files
  - Job status updates to DynamoDB

### 4. API Gateway

HTTP API (v2) for REST endpoints with WebSocket support for real-time features.

#### REST API Endpoints
- `POST /v1/upload` - Initiate multipart upload, return presigned URLs
- `POST /v1/upload/complete` - Finalize upload, trigger transcode job
- `GET /v1/asset/:id` - Fetch asset metadata
- `GET /v1/s/:shortCode` - Resolve short link (cached)
- `POST /v1/analytics/track` - Track view/play events
- `GET /v1/metrics/:assetId` - Aggregated analytics

#### WebSocket API (Optional)
- `/ws` - Real-time upload progress, transcode status updates

#### Integration
- **Lambda Proxy**: For lightweight endpoints (auth, short links)
- **ALB/NLB**: For ECS Fargate API service
- **Direct S3**: For static assets (deprecated in favor of CloudFront)

#### Authentication
- **AWS IAM**: For internal service-to-service
- **Custom Authorizer**: Lambda function validating JWT tokens
- **API Keys**: For third-party integrations (GIPHY, Tenor publishers)

### 5. DynamoDB (NoSQL Database)

Serverless, fully managed NoSQL database with single-digit millisecond latency.

#### Tables

##### `Assets` Table
- **Partition Key**: `asset_id` (String, UUID)
- **Attributes**: `user_id`, `title`, `tags`, `upload_date`, `status`, `s3_key`, `file_size`, `mime_type`
- **GSI**: `UserAssetsIndex` (Partition: `user_id`, Sort: `upload_date`)
- **Capacity**: On-Demand (auto-scaling)
- **Encryption**: AWS-managed KMS key
- **TTL**: `expires_at` attribute (optional for temp assets)

##### `ShareLinks` Table
- **Partition Key**: `short_code` (String, 8 chars)
- **Attributes**: `asset_id`, `created_at`, `clicks`, `metadata`
- **Capacity**: Provisioned (read-heavy, 1000 RCU)
- **Cache**: ElastiCache Redis for hot links

##### `Analytics` Table
- **Partition Key**: `asset_id` (String)
- **Sort Key**: `timestamp#event` (String, ISO8601#view|play|share)
- **Attributes**: `user_agent`, `ip_hash`, `referrer`, `platform`
- **Capacity**: On-Demand
- **Stream**: DynamoDB Streams → Lambda for real-time aggregation

##### `Sessions` Table
- **Partition Key**: `session_id` (String, UUID)
- **Attributes**: `user_id`, `created_at`, `expires_at`, `metadata`
- **TTL**: `expires_at` (auto-delete after 7 days)
- **Capacity**: On-Demand

##### `Users` Table
- **Partition Key**: `user_id` (String, UUID)
- **Attributes**: `email`, `oauth_provider`, `oauth_id`, `roles`, `created_at`, `plan`
- **GSI**: `EmailIndex` (Partition: `email`)
- **Capacity**: On-Demand
- **Encryption**: Customer-managed KMS key (sensitive PII)

### 6. ElastiCache for Redis

In-memory cache for rate limiting, session storage, and hot data.

#### Cluster Configuration
- **Engine**: Redis 7.0
- **Node Type**: `cache.t3.micro` (dev), `cache.r6g.large` (prod)
- **Cluster Mode**: Enabled (3 shards, 1 replica per shard)
- **Multi-AZ**: Enabled for automatic failover
- **Encryption**: In-transit (TLS) + At-rest

#### Use Cases
- **Rate Limiting**: IP-based and user-based limits (sliding window)
- **Session Cache**: Fast session lookup (TTL 30 min)
- **Analytics Cache**: Pre-aggregated metrics (TTL 5 min)
- **Short Link Cache**: Hot short codes (TTL 1 hour)

### 7. SQS & EventBridge (Job Queue)

#### SQS Queues

##### `transcode-jobs.fifo`
- **Type**: FIFO (ordering guarantee per user)
- **Message Retention**: 14 days
- **Visibility Timeout**: 900 seconds (15 min for long jobs)
- **Dead Letter Queue**: `transcode-dlq.fifo` (3 retries)
- **Consumers**: ECS Fargate media workers

##### `analytics-events`
- **Type**: Standard (high throughput)
- **Batching**: Yes (up to 10 messages per batch)
- **Consumers**: Lambda function for DynamoDB writes

#### EventBridge Rules
- **Schedule**: Cron-based cleanup jobs (S3 lifecycle, temp files)
- **Event Pattern**: S3 `ObjectCreated` → trigger transcode job
- **Targets**: SQS, Lambda, SNS for notifications

### 8. Secrets Manager & Parameter Store

#### Secrets Manager (Sensitive Credentials)
- `gifdistributor/prod/openai-api-key` - OpenAI API key for moderation
- `gifdistributor/prod/giphy-api-key` - GIPHY publisher credentials
- `gifdistributor/prod/tenor-api-key` - Tenor API credentials
- `gifdistributor/prod/oauth-client-secret` - OAuth client secrets
- `gifdistributor/prod/jwt-signing-key` - JWT token signing key
- **Rotation**: Automatic 90-day rotation via Lambda

#### Systems Manager Parameter Store (Configuration)
- `/gifdistributor/prod/cdn-domain` - CloudFront distribution domain
- `/gifdistributor/prod/api-url` - API Gateway endpoint
- `/gifdistributor/prod/s3-media-bucket` - S3 media bucket name
- `/gifdistributor/prod/feature-flags` - Feature toggles (JSON)

## Setup Instructions

### Prerequisites

1. **AWS Account**
   - Root account with billing enabled
   - IAM user with AdministratorAccess (for initial setup)
   - MFA enabled for root and IAM users

2. **Domain & SSL Certificate**
   - Domain registered (Route 53 or external registrar)
   - ACM certificate requested for `*.gifdistributor.com` in `us-east-1` (CloudFront requirement)

3. **CLI Tools**
   ```bash
   # AWS CLI v2
   aws --version

   # Terraform (Infrastructure as Code)
   terraform --version

   # Docker (for building container images)
   docker --version
   ```

### Step 1: Create S3 Buckets

```bash
# Production buckets (us-east-1)
aws s3api create-bucket \
  --bucket gifdistributor-media-prod \
  --region us-east-1

aws s3api create-bucket \
  --bucket gifdistributor-cache-prod \
  --region us-east-1

aws s3api create-bucket \
  --bucket gifdistributor-transcode-prod \
  --region us-east-1

aws s3api create-bucket \
  --bucket gifdistributor-logs-prod \
  --region us-east-1

# Enable versioning for media bucket (data protection)
aws s3api put-bucket-versioning \
  --bucket gifdistributor-media-prod \
  --versioning-configuration Status=Enabled

# Enable server-side encryption (AES-256)
aws s3api put-bucket-encryption \
  --bucket gifdistributor-media-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      },
      "BucketKeyEnabled": true
    }]
  }'

# Block public access (CloudFront OAI only)
aws s3api put-public-access-block \
  --bucket gifdistributor-media-prod \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

#### Configure Lifecycle Policies

```bash
# Cache bucket lifecycle (30 days)
aws s3api put-bucket-lifecycle-configuration \
  --bucket gifdistributor-cache-prod \
  --lifecycle-configuration file://lifecycle-cache.json

# lifecycle-cache.json
{
  "Rules": [{
    "Id": "transition-to-ia-then-delete",
    "Status": "Enabled",
    "Transitions": [{
      "Days": 30,
      "StorageClass": "STANDARD_IA"
    }],
    "Expiration": { "Days": 90 }
  }]
}

# Logs bucket lifecycle (archive to Glacier)
aws s3api put-bucket-lifecycle-configuration \
  --bucket gifdistributor-logs-prod \
  --lifecycle-configuration file://lifecycle-logs.json

# lifecycle-logs.json
{
  "Rules": [{
    "Id": "archive-old-logs",
    "Status": "Enabled",
    "Transitions": [
      { "Days": 30, "StorageClass": "GLACIER_IR" },
      { "Days": 90, "StorageClass": "DEEP_ARCHIVE" }
    ],
    "Expiration": { "Days": 180 }
  }]
}
```

### Step 2: Create DynamoDB Tables

```bash
# Assets table
aws dynamodb create-table \
  --table-name Assets \
  --attribute-definitions \
    AttributeName=asset_id,AttributeType=S \
    AttributeName=user_id,AttributeType=S \
    AttributeName=upload_date,AttributeType=S \
  --key-schema AttributeName=asset_id,KeyType=HASH \
  --global-secondary-indexes '[
    {
      "IndexName": "UserAssetsIndex",
      "KeySchema": [
        {"AttributeName": "user_id", "KeyType": "HASH"},
        {"AttributeName": "upload_date", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' \
  --billing-mode PAY_PER_REQUEST \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

# ShareLinks table
aws dynamodb create-table \
  --table-name ShareLinks \
  --attribute-definitions AttributeName=short_code,AttributeType=S \
  --key-schema AttributeName=short_code,KeyType=HASH \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=1000,WriteCapacityUnits=100

# Analytics table
aws dynamodb create-table \
  --table-name Analytics \
  --attribute-definitions \
    AttributeName=asset_id,AttributeType=S \
    AttributeName=timestamp_event,AttributeType=S \
  --key-schema \
    AttributeName=asset_id,KeyType=HASH \
    AttributeName=timestamp_event,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_IMAGE

# Sessions table (with TTL)
aws dynamodb create-table \
  --table-name Sessions \
  --attribute-definitions AttributeName=session_id,AttributeType=S \
  --key-schema AttributeName=session_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb update-time-to-live \
  --table-name Sessions \
  --time-to-live-specification Enabled=true,AttributeName=expires_at

# Users table
aws dynamodb create-table \
  --table-name Users \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=email,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --global-secondary-indexes '[
    {
      "IndexName": "EmailIndex",
      "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' \
  --billing-mode PAY_PER_REQUEST
```

### Step 3: Create ElastiCache Redis Cluster

```bash
# Create subnet group (use your VPC subnets)
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name gifdistributor-redis-subnet \
  --subnet-ids subnet-abc123 subnet-def456 subnet-ghi789 \
  --cache-subnet-group-description "Subnet group for GIFDistributor Redis"

# Create replication group (cluster mode enabled)
aws elasticache create-replication-group \
  --replication-group-id gifdistributor-redis-prod \
  --replication-group-description "GIFDistributor Redis cluster" \
  --engine redis \
  --engine-version 7.0 \
  --cache-node-type cache.r6g.large \
  --num-node-groups 3 \
  --replicas-per-node-group 1 \
  --cache-subnet-group-name gifdistributor-redis-subnet \
  --security-group-ids sg-abc12345 \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --multi-az-enabled \
  --automatic-failover-enabled \
  --snapshot-retention-limit 5
```

### Step 4: Create SQS Queues

```bash
# Transcode FIFO queue
aws sqs create-queue \
  --queue-name transcode-jobs.fifo \
  --attributes '{
    "FifoQueue": "true",
    "ContentBasedDeduplication": "true",
    "MessageRetentionPeriod": "1209600",
    "VisibilityTimeout": "900"
  }'

# Dead letter queue
aws sqs create-queue \
  --queue-name transcode-dlq.fifo \
  --attributes '{"FifoQueue": "true"}'

# Set DLQ redrive policy
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/transcode-jobs.fifo \
  --attributes '{
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:123456789012:transcode-dlq.fifo\",\"maxReceiveCount\":\"3\"}"
  }'

# Analytics events queue (standard)
aws sqs create-queue \
  --queue-name analytics-events \
  --attributes '{"MessageRetentionPeriod": "604800"}'
```

### Step 5: Deploy ECS Fargate Services

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name gifdistributor-prod \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1 \
    capacityProvider=FARGATE_SPOT,weight=3

# Register task definition for API service
aws ecs register-task-definition \
  --cli-input-json file://api-task-definition.json

# Create API service with ALB
aws ecs create-service \
  --cluster gifdistributor-prod \
  --service-name gifdistributor-api \
  --task-definition gifdistributor-api:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-abc123", "subnet-def456"],
      "securityGroups": ["sg-api12345"],
      "assignPublicIp": "DISABLED"
    }
  }' \
  --load-balancers '[{
    "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/api/abc123",
    "containerName": "api",
    "containerPort": 3000
  }]'

# Register task definition for media workers
aws ecs register-task-definition \
  --cli-input-json file://worker-task-definition.json

# Create worker service (SQS-driven autoscaling)
aws ecs create-service \
  --cluster gifdistributor-prod \
  --service-name gifdistributor-workers \
  --task-definition gifdistributor-worker:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-abc123", "subnet-def456"],
      "securityGroups": ["sg-worker12345"],
      "assignPublicIp": "DISABLED"
    }
  }'
```

### Step 6: Create CloudFront Distribution

```bash
# Create Origin Access Identity (OAI) for S3
aws cloudfront create-cloud-front-origin-access-identity \
  --cloud-front-origin-access-identity-config \
    CallerReference=gifdistributor-oai-$(date +%s),Comment="OAI for GIFDistributor media bucket"

# Create distribution
aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json

# Update S3 bucket policy to allow OAI access
aws s3api put-bucket-policy \
  --bucket gifdistributor-media-prod \
  --policy file://s3-cloudfront-policy.json
```

### Step 7: Configure API Gateway

```bash
# Create HTTP API
aws apigatewayv2 create-api \
  --name gifdistributor-api \
  --protocol-type HTTP \
  --target arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/api-alb/abc123/def456

# Create custom domain
aws apigatewayv2 create-domain-name \
  --domain-name api.gifdistributor.com \
  --domain-name-configurations '{
    "CertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/abc-123",
    "EndpointType": "REGIONAL"
  }'

# Map domain to API
aws apigatewayv2 create-api-mapping \
  --domain-name api.gifdistributor.com \
  --api-id abc123xyz \
  --stage $default
```

### Step 8: Store Secrets

```bash
# Store OpenAI API key
aws secretsmanager create-secret \
  --name gifdistributor/prod/openai-api-key \
  --secret-string "sk-proj-xxxx" \
  --description "OpenAI API key for content moderation"

# Store GIPHY credentials
aws secretsmanager create-secret \
  --name gifdistributor/prod/giphy-api-key \
  --secret-string '{"api_key":"xxx","channel_id":"yyy"}' \
  --description "GIPHY publisher credentials"

# Enable automatic rotation (90 days)
aws secretsmanager rotate-secret \
  --secret-id gifdistributor/prod/openai-api-key \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:rotate-openai-key \
  --rotation-rules AutomaticallyAfterDays=90
```

## Security Configuration

### 1. IAM Roles & Policies

#### ECS Task Execution Role
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Attached Policies:
- `AmazonECSTaskExecutionRolePolicy` (managed)
- Custom policy for Secrets Manager and ECR access

#### ECS Task Role (API)
Permissions:
- S3: `GetObject`, `PutObject` on media buckets
- DynamoDB: `GetItem`, `PutItem`, `Query` on all tables
- SQS: `SendMessage` to transcode queue
- Secrets Manager: `GetSecretValue` for API keys
- CloudWatch Logs: `CreateLogStream`, `PutLogEvents`

#### ECS Task Role (Workers)
Permissions:
- S3: Full access to media, cache, transcode buckets
- SQS: `ReceiveMessage`, `DeleteMessage` on transcode queue
- DynamoDB: `UpdateItem` on Assets table (status updates)
- CloudWatch Logs: `CreateLogStream`, `PutLogEvents`

### 2. VPC Configuration

```
VPC CIDR: 10.0.0.0/16

Subnets:
- Public Subnet A (us-east-1a):  10.0.1.0/24  (NAT Gateway, ALB)
- Public Subnet B (us-east-1b):  10.0.2.0/24  (NAT Gateway, ALB)
- Private Subnet A (us-east-1a): 10.0.11.0/24 (ECS, ElastiCache)
- Private Subnet B (us-east-1b): 10.0.12.0/24 (ECS, ElastiCache)
- Private Subnet C (us-east-1c): 10.0.13.0/24 (ECS, ElastiCache)

Security Groups:
- ALB-SG: Inbound 443 from 0.0.0.0/0, Outbound to ECS-SG:3000
- ECS-SG: Inbound 3000 from ALB-SG, Outbound to Redis-SG:6379, DynamoDB via VPC endpoint
- Redis-SG: Inbound 6379 from ECS-SG only
```

### 3. CloudFront Security Headers

Lambda@Edge function to add security headers:

```javascript
exports.handler = async (event) => {
  const response = event.Records[0].cf.response;
  response.headers['strict-transport-security'] = [{
    key: 'Strict-Transport-Security',
    value: 'max-age=31536000; includeSubDomains; preload'
  }];
  response.headers['x-content-type-options'] = [{
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  }];
  response.headers['x-frame-options'] = [{
    key: 'X-Frame-Options',
    value: 'DENY'
  }];
  response.headers['x-xss-protection'] = [{
    key: 'X-XSS-Protection',
    value: '1; mode=block'
  }];
  return response;
};
```

### 4. WAF Configuration

AWS WAF Web ACL attached to CloudFront:

- **AWS Managed Rule: Core Rule Set** - OWASP Top 10 protection
- **AWS Managed Rule: Known Bad Inputs** - Block malicious patterns
- **AWS Managed Rule: IP Reputation List** - Block known malicious IPs
- **Rate Limiting Rule**: 100 requests per 5 minutes per IP
- **Geo Blocking** (optional): Block specific countries if needed

## Monitoring & Observability

### 1. CloudWatch Dashboards

Create comprehensive dashboard:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name GIFDistributor-Prod \
  --dashboard-body file://dashboard-config.json
```

Widgets:
- ECS API service CPU/Memory utilization
- ECS worker service task count + SQS queue depth
- ALB request count, latency (P50, P99), error rate
- CloudFront request count, cache hit rate, origin latency
- DynamoDB consumed capacity, throttled requests
- ElastiCache CPU, memory, evictions, cache hit rate

### 2. CloudWatch Alarms

```bash
# High API error rate
aws cloudwatch put-metric-alarm \
  --alarm-name API-High-Error-Rate \
  --alarm-description "Alert when API error rate > 5%" \
  --metric-name 5XXError \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts

# DynamoDB throttling
aws cloudwatch put-metric-alarm \
  --alarm-name DynamoDB-Throttled-Requests \
  --metric-name UserErrors \
  --namespace AWS/DynamoDB \
  --dimensions Name=TableName,Value=Assets \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts

# SQS queue depth (workers not keeping up)
aws cloudwatch put-metric-alarm \
  --alarm-name Transcode-Queue-Depth-High \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --dimensions Name=QueueName,Value=transcode-jobs.fifo \
  --statistic Average \
  --period 300 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

### 3. X-Ray Tracing

Enable distributed tracing:

```bash
# Enable X-Ray on ECS tasks (add to task definition)
{
  "portMappings": [...],
  "environment": [
    {"name": "AWS_XRAY_DAEMON_ADDRESS", "value": "xray-daemon:2000"}
  ]
}

# Deploy X-Ray daemon as sidecar container
{
  "name": "xray-daemon",
  "image": "public.ecr.aws/xray/aws-xray-daemon:latest",
  "cpu": 32,
  "memoryReservation": 256,
  "portMappings": [{
    "containerPort": 2000,
    "protocol": "udp"
  }]
}
```

### 4. Logging

Centralized logging with CloudWatch Logs Insights:

```sql
-- Find slow API requests
fields @timestamp, @message
| filter @message like /duration/
| parse @message /duration: (?<duration>\d+)ms/
| filter duration > 1000
| sort @timestamp desc
| limit 100

-- Track transcode job failures
fields @timestamp, asset_id, error
| filter error like /transcode failed/
| stats count() by bin(5m)
```

## Cost Estimation

### Monthly Cost Breakdown (Estimated)

#### Scenario: 10,000 active users, 100,000 GIFs, 1M monthly views

**Compute (ECS Fargate)**
- API service: 2 tasks × 0.5 vCPU × 1 GB × 730 hours = $35
- Workers: Avg 3 tasks × 2 vCPU × 4 GB × 300 hours = $90
- **Subtotal: $125**

**Storage (S3)**
- Media: 500 GB × $0.023/GB = $11.50
- Cache: 100 GB × $0.023/GB = $2.30
- Transcode: 200 GB × $0.023/GB = $4.60
- **Subtotal: $18.40**

**S3 Requests**
- GET: 5M requests × $0.0004/1000 = $2.00
- PUT: 100K requests × $0.005/1000 = $0.50
- **Subtotal: $2.50**

**CloudFront**
- Data transfer: 2 TB × $0.085/GB = $170
- Requests: 10M × $0.0075/10000 = $7.50
- **Subtotal: $177.50**

**DynamoDB**
- On-Demand: ~$30 (estimated based on read/write patterns)

**ElastiCache Redis**
- cache.r6g.large × 3 nodes × 730 hours × $0.226/hour = $495 (High! Consider t3.medium for dev)

**API Gateway**
- HTTP API: 1M requests × $1.00/million = $1.00

**Data Transfer**
- S3 → CloudFront: Free (within AWS)
- CloudFront → Internet: Included in CloudFront pricing

**Other**
- CloudWatch Logs: ~$10
- Secrets Manager: $2 (4 secrets × $0.40)
- Route 53: $1 (hosted zone + queries)

**TOTAL (Production Scale): ~$862/month**

> **Cost Optimization Tips:**
> - Use Fargate Spot for workers (70% discount)
> - Use S3 Intelligent-Tiering for automatic cost optimization
> - Use ElastiCache t3.medium instead of r6g.large for smaller workloads ($25 vs $495)
> - Enable CloudFront Origin Shield only if needed (adds cost but reduces origin load)
> - Use DynamoDB provisioned capacity with auto-scaling instead of on-demand if traffic is predictable

**Development/Staging Environment: ~$150/month**
- Smaller instance sizes
- Reduced redundancy
- Spot instances for all compute

## Disaster Recovery

### Backup Strategy

#### S3 Versioning & Cross-Region Replication
```bash
# Enable cross-region replication (media bucket)
aws s3api put-bucket-replication \
  --bucket gifdistributor-media-prod \
  --replication-configuration file://replication-config.json

# replication-config.json
{
  "Role": "arn:aws:iam::123456789012:role/s3-replication-role",
  "Rules": [{
    "Status": "Enabled",
    "Priority": 1,
    "Filter": {},
    "Destination": {
      "Bucket": "arn:aws:s3:::gifdistributor-media-dr",
      "ReplicationTime": {"Status": "Enabled", "Time": {"Minutes": 15}},
      "Metrics": {"Status": "Enabled", "EventThreshold": {"Minutes": 15}}
    },
    "DeleteMarkerReplication": {"Status": "Enabled"}
  }]
}
```

#### DynamoDB Point-in-Time Recovery
```bash
# Enable PITR for all tables
for table in Assets ShareLinks Analytics Sessions Users; do
  aws dynamodb update-continuous-backups \
    --table-name $table \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
done

# Create on-demand backup
aws dynamodb create-backup \
  --table-name Assets \
  --backup-name Assets-Backup-$(date +%Y%m%d)
```

#### Automated Snapshots (ElastiCache)
```bash
# ElastiCache automatic snapshots (configured during creation)
# Retention: 5 days
# Snapshot window: 03:00-05:00 UTC (low traffic)
```

### Recovery Procedures

#### RTO (Recovery Time Objective): 1 hour
#### RPO (Recovery Point Objective): 15 minutes

**Procedure for Region Failure:**
1. Update Route 53 DNS to point to DR region (5 min)
2. Promote DynamoDB global tables in DR region (automatic)
3. Restore ElastiCache from latest snapshot (15 min)
4. Deploy ECS services in DR region from ECR images (10 min)
5. Update CloudFront origin to DR ALB (5 min)
6. Validate functionality via health checks (5 min)

## Migration from Cloudflare

### Data Migration

```bash
# Install rclone (S3-compatible transfer tool)
# Configure Cloudflare R2 remote
rclone config create r2 s3 \
  provider=Cloudflare \
  access_key_id=$CF_ACCESS_KEY \
  secret_access_key=$CF_SECRET_KEY \
  endpoint=https://$CF_ACCOUNT_ID.r2.cloudflarestorage.com

# Configure AWS S3 remote (default)
rclone config create s3 s3 \
  provider=AWS \
  region=us-east-1

# Sync R2 → S3 (media bucket)
rclone sync r2:gifdistributor-media-prod s3:gifdistributor-media-prod \
  --progress \
  --transfers 32 \
  --checkers 16 \
  --fast-list

# Verify transfer
rclone check r2:gifdistributor-media-prod s3:gifdistributor-media-prod
```

### Metadata Migration (KV → DynamoDB)

```python
# Export Cloudflare KV data
import requests
import boto3

# Fetch all KV keys from Cloudflare
cf_kv_data = requests.get(
    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/keys",
    headers={"Authorization": f"Bearer {cf_api_token}"}
).json()

# Write to DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ShareLinks')

with table.batch_writer() as batch:
    for item in cf_kv_data['result']:
        # Fetch value
        value = requests.get(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{item['name']}",
            headers={"Authorization": f"Bearer {cf_api_token}"}
        ).json()

        # Write to DynamoDB
        batch.put_item(Item={
            'short_code': item['name'],
            'asset_id': value['asset_id'],
            'created_at': value['created_at'],
            'clicks': value.get('clicks', 0)
        })
```

### DNS Cutover

```bash
# Update Route 53 records (zero-downtime cutover)
# 1. Lower TTL on existing Cloudflare records (24h before cutover)
# 2. At cutover time, update records:

# Main site (CloudFront)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123ABC \
  --change-batch file://dns-change-cloudfront.json

# API endpoint
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123ABC \
  --change-batch file://dns-change-api.json

# CDN subdomain
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123ABC \
  --change-batch file://dns-change-cdn.json
```

## Comparison: AWS vs Cloudflare

| Feature | Cloudflare | AWS |
|---------|-----------|-----|
| **Compute** | Workers (V8 isolates, 50ms limit) | Fargate (containers, no hard limit) |
| **Storage** | R2 (S3-compatible, $0.015/GB) | S3 (standard, $0.023/GB) |
| **CDN** | Cloudflare CDN (included) | CloudFront ($0.085/GB + requests) |
| **Database** | KV + Durable Objects | DynamoDB + ElastiCache |
| **Egress** | Free (R2 → CF CDN) | $0.09/GB (S3 → Internet), Free (S3 → CF) |
| **Cold Start** | None (Workers always warm) | 1-3s (Fargate cold start) |
| **Max Request Time** | 50ms (Workers), 900s (Durable Objects) | No limit (Fargate) |
| **Scalability** | Automatic, global | Auto-scaling, regional (multi-region requires setup) |
| **Pricing Model** | Pay-per-request (predictable) | Complex (many services, data transfer) |
| **Best For** | Edge compute, global low-latency | Long-running jobs, complex workflows, AWS ecosystem |

## Conclusion

AWS provides a robust, feature-rich alternative to Cloudflare with:
- **Pros**: Mature ecosystem, unlimited processing time, full control over infrastructure, integration with other AWS services
- **Cons**: Higher cost (especially CloudFront + data egress), more complex setup, regional by default (global requires multi-region deployment)

**Recommendation**: Use AWS if:
- You need >50ms compute time (e.g., complex image processing, ML inference)
- You're already using AWS services (RDS, Lambda, etc.)
- You need advanced features (VPC, custom networking, GPU instances for encoding)
- Cost is less sensitive (willing to pay 2-3x more for flexibility)

Use Cloudflare if:
- You prioritize global low latency and simple edge deployment
- Budget is constrained (R2 egress savings are significant)
- Workloads fit within Workers' 50ms CPU limit
- You want fully managed, zero-ops infrastructure

---

**Last Updated**: 2025-10-04
**Owner**: Infrastructure Team
**Review Cycle**: Quarterly
