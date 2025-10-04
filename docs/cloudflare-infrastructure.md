# Cloudflare Infrastructure Guide

> **Slug:** `infra-cloudflare`
> **Priority:** P0
> **Labels:** infra, cdn

## Overview

This document describes the complete Cloudflare infrastructure setup for GIFDistributor, including R2 storage, CDN configuration, Cloudflare Pages for the web app, and Workers for the API.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloudflare Edge Network                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Pages     │  │   Workers   │  │   R2 Buckets        │ │
│  │  (Web App)  │  │    (API)    │  │  (Media Storage)    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │     CDN     │  │  KV Store   │  │  Durable Objects    │ │
│  │  (R2 URLs)  │  │ (Metadata)  │  │   (Real-time)       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   End Users      │
                    └──────────────────┘
```

## Components

### 1. R2 Buckets (Object Storage)

R2 provides S3-compatible object storage with zero egress fees when accessed via Cloudflare CDN.

#### Primary Media Bucket (`gifdistributor-media`)
- **Purpose**: Store original uploaded GIFs, MP4s, and source media
- **Access**: Private, signed URLs only
- **Lifecycle**: Keep indefinitely unless user deletes
- **Custom Domain**: `cdn.gifdistributor.com`

#### Cache Bucket (`gifdistributor-cache`)
- **Purpose**: Store CDN-optimized assets (compressed, resized)
- **Access**: Public via CDN
- **Lifecycle**: 30-day TTL for unused assets
- **Custom Domain**: `cache.gifdistributor.com`

#### Transcode Bucket (`gifdistributor-transcode`)
- **Purpose**: Store platform-specific renditions (Discord MP4, Slack optimized GIF, etc.)
- **Access**: Private, signed URLs only
- **Lifecycle**: 90-day TTL for unused renditions

#### Logs Bucket (`gifdistributor-logs`)
- **Purpose**: Store access logs, audit trails, and analytics data
- **Access**: Private, analytics system only
- **Lifecycle**: 180-day retention

### 2. Cloudflare Pages (Web Application)

- **Framework**: Next.js (Static Site Generation + Server-Side Rendering)
- **Deployment**: Automatic on git push to `main` branch
- **Preview Deployments**: Automatic for all pull requests
- **Custom Domain**: `gifdistributor.com`, `www.gifdistributor.com`

#### Build Configuration
```yaml
Build command: npm run build
Build output directory: .next
Root directory: web
Node version: 18
```

### 3. Cloudflare Workers (API)

- **Runtime**: V8 isolates, Node.js compatibility enabled
- **Routes**:
  - `api.gifdistributor.com/*` - Production API
  - `api-staging.gifdistributor.com/*` - Staging API
- **CPU Limit**: 50ms per request (P99 should be <10ms)

#### Worker Endpoints
- `POST /upload` - Direct browser upload with resumable support
- `GET /a/:assetId` - Canonical asset URL
- `GET /s/:shortCode` - Short link redirect
- `POST /analytics/track` - Analytics event tracking
- `GET /api/metrics/:assetId` - Get asset metrics

### 4. KV Namespaces (Key-Value Store)

#### Share Links KV (`SHARE_LINKS`)
- **Purpose**: Map short codes to asset IDs
- **TTL**: None (permanent until deleted)
- **Keys**: `short_code` → `{asset_id, metadata, clicks}`

#### Analytics Cache KV (`ANALYTICS_CACHE`)
- **Purpose**: Cache aggregated analytics data
- **TTL**: 5 minutes
- **Keys**: `metrics:{asset_id}` → `{views, plays, ctr}`

#### Rate Limit KV (`RATE_LIMIT`)
- **Purpose**: Store rate limit state per IP/user
- **TTL**: Window duration (60 seconds default)
- **Keys**: `ratelimit:{ip}:{user}` → `{count, window_start}`

#### Auth Tokens KV (`AUTH_TOKENS`)
- **Purpose**: Store user session tokens and OAuth state
- **TTL**: Session duration (7 days default)
- **Keys**: `session:{token}` → `{user_id, expires_at}`

### 5. Durable Objects

#### Analytics Durable Object (`ANALYTICS_DO`)
- **Purpose**: Real-time analytics aggregation
- **State**: In-memory counters with periodic persistence to KV
- **Use Case**: High-frequency view/play tracking

#### Job Queue Durable Object (`QUEUE_DO`)
- **Purpose**: Coordinate media processing jobs
- **State**: Job queue, worker pool status
- **Use Case**: Transcode jobs, thumbnail generation

### 6. CDN Configuration

#### R2 Custom Domains
Connect R2 buckets to custom domains for CDN access:

```bash
# Media bucket
wrangler r2 bucket domain add gifdistributor-media-prod --domain cdn.gifdistributor.com

# Cache bucket
wrangler r2 bucket domain add gifdistributor-cache-prod --domain cache.gifdistributor.com
```

#### Cache Rules
- **Immutable Assets** (hashed filenames): Cache for 1 year
- **Dynamic Assets**: Cache for 24 hours with revalidation
- **API Responses**: Cache for 5 minutes (if cacheable)

#### Transform Rules
- **Auto WebP**: Serve WebP to supporting browsers
- **Image Resizing**: On-the-fly resize with Cloudflare Images
- **Compression**: Auto Brotli/Gzip based on Accept-Encoding

## Setup Instructions

### Prerequisites

1. **Cloudflare Account**
   - Free tier is sufficient to start
   - Upgrade to Workers Paid plan for production ($5/month)

2. **Domain Setup**
   - Domain registered and added to Cloudflare
   - DNS managed by Cloudflare nameservers

3. **CLI Tools**
   ```bash
   npm install -g wrangler
   wrangler login
   ```

### Step 1: Create R2 Buckets

```bash
# Production buckets
wrangler r2 bucket create gifdistributor-media-prod
wrangler r2 bucket create gifdistributor-cache-prod
wrangler r2 bucket create gifdistributor-transcode-prod
wrangler r2 bucket create gifdistributor-logs-prod

# Staging buckets
wrangler r2 bucket create gifdistributor-media-staging
wrangler r2 bucket create gifdistributor-cache-staging
wrangler r2 bucket create gifdistributor-transcode-staging
wrangler r2 bucket create gifdistributor-logs-staging
```

#### Configure Bucket Lifecycle Rules

```bash
# Set TTL for cache bucket (30 days)
wrangler r2 bucket lifecycle put gifdistributor-cache-prod \
  --rule '{"id":"expire-unused","status":"enabled","expiration":{"days":30}}'

# Set TTL for transcode bucket (90 days)
wrangler r2 bucket lifecycle put gifdistributor-transcode-prod \
  --rule '{"id":"expire-unused","status":"enabled","expiration":{"days":90}}'

# Set TTL for logs bucket (180 days)
wrangler r2 bucket lifecycle put gifdistributor-logs-prod \
  --rule '{"id":"expire-old-logs","status":"enabled","expiration":{"days":180}}'
```

#### Add Custom Domains to R2

```bash
# Production
wrangler r2 bucket domain add gifdistributor-media-prod \
  --domain cdn.gifdistributor.com

wrangler r2 bucket domain add gifdistributor-cache-prod \
  --domain cache.gifdistributor.com

# Staging
wrangler r2 bucket domain add gifdistributor-media-staging \
  --domain cdn-staging.gifdistributor.com
```

### Step 2: Create KV Namespaces

```bash
# Production namespaces
wrangler kv:namespace create "SHARE_LINKS" --preview
wrangler kv:namespace create "ANALYTICS_CACHE" --preview
wrangler kv:namespace create "RATE_LIMIT" --preview
wrangler kv:namespace create "AUTH_TOKENS" --preview

# Staging namespaces (optional)
wrangler kv:namespace create "SHARE_LINKS_STAGING" --preview
wrangler kv:namespace create "ANALYTICS_CACHE_STAGING" --preview
wrangler kv:namespace create "RATE_LIMIT_STAGING" --preview
wrangler kv:namespace create "AUTH_TOKENS_STAGING" --preview
```

Copy the namespace IDs and update `wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "SHARE_LINKS"
id = "<namespace-id-from-output>"
preview_id = "<preview-namespace-id>"
```

### Step 3: Configure DNS Records

Add the following DNS records in Cloudflare Dashboard:

```
# Root domain
A       @           192.0.2.1        Proxied (will be overridden by Pages)

# WWW subdomain
CNAME   www         gifdistributor.com   Proxied

# API subdomain (Worker routes)
AAAA    api         100::              Proxied
AAAA    api-staging 100::              Proxied

# CDN subdomains (R2 custom domains)
CNAME   cdn         gifdistributor-media-prod.r2.cloudflarestorage.com   Proxied
CNAME   cdn-staging gifdistributor-media-staging.r2.cloudflarestorage.com Proxied
CNAME   cache       gifdistributor-cache-prod.r2.cloudflarestorage.com   Proxied
```

### Step 4: Deploy Workers

```bash
# Deploy to staging
wrangler deploy --env staging

# Deploy to production (requires approval if using GitHub Actions)
wrangler deploy --env production
```

### Step 5: Deploy Cloudflare Pages

#### Option A: Automatic Deployment (Recommended)

1. Go to Cloudflare Dashboard → Pages
2. Click "Create a project" → "Connect to Git"
3. Select repository: `gifdistributor`
4. Configure build settings:
   - **Framework preset**: Next.js
   - **Build command**: `npm run build`
   - **Build output directory**: `.next`
   - **Root directory**: `web`
5. Add environment variables:
   - `NEXT_PUBLIC_API_URL`: `https://api.gifdistributor.com`
   - `NEXT_PUBLIC_CDN_URL`: `https://cdn.gifdistributor.com`
6. Click "Save and Deploy"

#### Option B: Manual Deployment (CLI)

```bash
cd web
npm run build
npx wrangler pages deploy .next --project-name gifdistributor-web
```

### Step 6: Configure Worker Routes

Worker routes are automatically configured via `wrangler.toml`, but you can verify:

```bash
# List routes
wrangler routes list

# Expected output:
# api.gifdistributor.com/*        → gifdistributor-api-prod
# api-staging.gifdistributor.com/* → gifdistributor-api-staging
```

### Step 7: Enable Durable Objects

Deploy Durable Object workers:

```bash
# Deploy Analytics DO
wrangler deploy api/durable-objects/analytics.js --name gifdistributor-analytics-do

# Deploy Queue DO
wrangler deploy api/durable-objects/queue.js --name gifdistributor-queue-do
```

## Security Configuration

### 1. Configure CORS

In your Worker code (`api/index.js`):

```javascript
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': 'https://gifdistributor.com',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};
```

### 2. Enable WAF Rules

Cloudflare Dashboard → Security → WAF:

- **OWASP Core Ruleset**: Enabled
- **Cloudflare Managed Ruleset**: Enabled
- **Rate Limiting**: 100 requests/minute per IP

### 3. Configure Signed URLs for R2

Generate signed URLs for private media access:

```javascript
import { SignedURL } from './cdn.js';

const signer = new SignedURL(env.SIGNING_SECRET);
const signedUrl = signer.generate_signed_url(
  'https://cdn.gifdistributor.com/asset/abc123.gif',
  3600  // 1 hour expiration
);
```

### 4. Enable DDoS Protection

Cloudflare Dashboard → Security → DDoS:

- **HTTP DDoS Attack Protection**: Enabled
- **Network-layer DDoS Attack Protection**: Enabled

## Monitoring & Observability

### 1. Workers Analytics

Built-in metrics available in Cloudflare Dashboard:

- Requests per second
- CPU time (P50, P99)
- Success rate (2xx/3xx responses)
- Error rate (4xx/5xx responses)

### 2. Logpush (Paid Plan)

Stream logs to R2 for analysis:

```bash
wrangler logpush create \
  --destination r2://gifdistributor-logs-prod/workers \
  --dataset workers_trace_events \
  --filter '{"outcome": ["ok", "exception"]}'
```

### 3. Custom Observability

Use the `observability.py` module integrated with Workers:

```javascript
import { ObservabilityStack } from './observability.js';

const obs = new ObservabilityStack('gifdistributor-api');

export default {
  async fetch(request, env, ctx) {
    const span = obs.start_trace('handle_request');

    try {
      // Handle request
      obs.finish_span(span, 'success');
    } catch (error) {
      obs.logger.error('Request failed', { error: error.message });
      obs.finish_span(span, 'error');
    }
  }
}
```

### 4. Alerts

Set up alerts in Cloudflare Dashboard:

- **High Error Rate**: > 5% errors for 5 minutes
- **High CPU Usage**: P99 > 30ms for 5 minutes
- **R2 Storage Threshold**: > 80% of quota

## Cost Estimation

### Free Tier Limits
- **Workers**: 100,000 requests/day
- **Pages**: Unlimited requests, 500 builds/month
- **R2 Storage**: 10 GB/month
- **R2 Class A Operations**: 1M/month (PUT, LIST)
- **R2 Class B Operations**: 10M/month (GET, HEAD)
- **KV**: 100,000 reads/day, 1,000 writes/day

### Paid Plans (Estimated Monthly Cost)

#### Workers Paid ($5/month + usage)
- **Included**: 10M requests
- **Overage**: $0.50 per additional 1M requests

#### R2 (Storage-based pricing)
- **Storage**: $0.015/GB/month
- **Class A Operations**: $4.50/million (after free tier)
- **Class B Operations**: $0.36/million (after free tier)
- **Egress to Internet**: $0.00 (free via Cloudflare CDN)

#### Example: 1M monthly views
- Workers: $5 (base) + ~$0.05 (100k API requests) = **$5.05**
- R2 Storage (100 GB): $1.50
- R2 Operations: ~$0.50
- **Total**: ~**$7/month**

## Troubleshooting

### Common Issues

#### Issue: R2 bucket not accessible
```
Error: NoSuchBucket
```
**Solution**: Verify bucket name and ensure it's created in the correct account
```bash
wrangler r2 bucket list
```

#### Issue: KV namespace binding fails
```
Error: KV namespace SHARE_LINKS not found
```
**Solution**: Update namespace IDs in `wrangler.toml` after creating namespaces

#### Issue: Custom domain not resolving
```
Error: DNS_PROBE_FINISHED_NXDOMAIN
```
**Solution**: Verify DNS records are proxied (orange cloud) and wait for propagation (up to 5 minutes)

#### Issue: Worker exceeds CPU limit
```
Error: Script exceeded CPU time limit
```
**Solution**: Optimize hot paths, use caching, or increase limit in `wrangler.toml`

### Debug Commands

```bash
# View live Worker logs
wrangler tail --env production

# Check R2 bucket contents
wrangler r2 object list gifdistributor-media-prod --prefix assets/

# View KV namespace data
wrangler kv:key list --namespace-id=<SHARE_LINKS_ID>

# Test Worker locally
wrangler dev --env staging
```

## Backup & Disaster Recovery

### R2 Bucket Backup

Use S3-compatible tools to backup R2:

```bash
# Using rclone
rclone sync r2:gifdistributor-media-prod s3:backup-bucket --progress
```

### KV Snapshot

Export KV data periodically:

```bash
# Export all keys
wrangler kv:key list --namespace-id=<ID> > kv-backup.json

# Restore
cat kv-backup.json | jq -r '.[] | .name' | while read key; do
  wrangler kv:key get "$key" --namespace-id=<ID> | \
  wrangler kv:key put "$key" --namespace-id=<NEW_ID> --stdin
done
```

### Worker Rollback

```bash
# List deployments
wrangler deployments list --name gifdistributor-api-prod

# Rollback to previous deployment
wrangler rollback --deployment-id <PREVIOUS_DEPLOYMENT_ID>
```

## Migration Path

### From Other Providers

#### AWS → Cloudflare
- **S3 → R2**: Use `rclone` or AWS DataSync
- **Lambda → Workers**: Refactor to use Workers API
- **CloudFront → Cloudflare CDN**: Update DNS to Cloudflare

#### GCP → Cloudflare
- **Cloud Storage → R2**: Use `gsutil` + S3 compatibility
- **Cloud Functions → Workers**: Rewrite with Workers runtime

## References

- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [Cloudflare Pages Documentation](https://developers.cloudflare.com/pages/)
- [Wrangler CLI Reference](https://developers.cloudflare.com/workers/wrangler/commands/)
- [KV Documentation](https://developers.cloudflare.com/workers/runtime-apis/kv/)
- [Durable Objects Documentation](https://developers.cloudflare.com/workers/runtime-apis/durable-objects/)

---

**Last Updated**: 2025-10-04
**Owner**: Infrastructure Team
**Review Cycle**: Quarterly
