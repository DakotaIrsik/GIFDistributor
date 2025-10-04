# Non-IaC Bootstrap & CI/CD Credentials Guide

> **Slug:** `non-iac-bootstrap-and-creds`
> **Priority:** P0
> **Labels:** docs, infra, security

## Overview

This guide covers the manual bootstrapping steps required before Infrastructure as Code (IaC) can be deployed. It focuses on establishing initial credentials for Cloudflare, DNS, and billing systems that will be used in CI/CD pipelines.

## Prerequisites

- GitHub repository with Actions enabled
- Cloudflare account with appropriate permissions
- Domain registrar access
- Payment method configured

## 1. Cloudflare API Credentials

### 1.1 Generate API Token

1. Log into [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Navigate to **My Profile** → **API Tokens**
3. Click **Create Token**
4. Select **Edit Cloudflare Workers** template or create custom token with:
   - **Permissions:**
     - Account: Cloudflare Workers Scripts - Edit
     - Account: Account Settings - Read
     - Zone: DNS - Edit
     - Zone: Zone - Read
     - Zone: Zone Settings - Edit
   - **Account Resources:**
     - Include: [Your Account]
   - **Zone Resources:**
     - Include: All zones from account [Your Account]

5. Set appropriate **IP Address Filtering** (optional but recommended)
6. Set **TTL** or leave as indefinite (manage rotation separately)
7. Click **Continue to summary** → **Create Token**
8. **Save the token immediately** - it won't be shown again

### 1.2 API Token vs Global API Key

**Use API Tokens (recommended):**
- Scoped permissions (principle of least privilege)
- Auditable
- Rotatable without affecting other services
- Can be restricted to specific zones/accounts

**Avoid Global API Key:**
- Full account access
- Cannot be scoped
- Higher security risk

### 1.3 Required Tokens

Create separate tokens for:

1. **CI/CD Deployment Token** (`CLOUDFLARE_API_TOKEN`)
   - Permissions: Workers Scripts (Edit), Pages (Edit)
   - Used by: GitHub Actions for deployments

2. **DNS Management Token** (`CLOUDFLARE_DNS_TOKEN`)
   - Permissions: Zone DNS (Edit), Zone (Read)
   - Used by: DNS automation, certificate management

3. **R2 Storage Token** (`CLOUDFLARE_R2_TOKEN`)
   - Permissions: R2 (Edit), Account Settings (Read)
   - Used by: Storage operations, CDN configuration

## 2. Cloudflare Account & Zone Setup

### 2.1 Account ID

1. From Cloudflare Dashboard, navigate to **Workers & Pages** or **R2**
2. Copy **Account ID** from the right sidebar
3. Store as `CLOUDFLARE_ACCOUNT_ID`

### 2.2 Zone ID (for each domain)

1. Navigate to **Websites** → Select your domain
2. Scroll down to **API** section in the right sidebar
3. Copy **Zone ID**
4. Store as `CLOUDFLARE_ZONE_ID`

## 3. DNS Configuration

### 3.1 Domain Registration

If registering a new domain:
1. Choose a registrar (Cloudflare Registrar, Namecheap, Google Domains, etc.)
2. Register domain
3. Configure billing/auto-renewal

### 3.2 Cloudflare DNS Setup

1. Add domain to Cloudflare:
   - Dashboard → **Add a Site**
   - Enter domain name
   - Select plan (Free tier is sufficient for start)

2. Update nameservers at registrar:
   - Copy Cloudflare nameservers (e.g., `ns1.cloudflare.com`, `ns2.cloudflare.com`)
   - Update at domain registrar
   - Wait for DNS propagation (can take 24-48 hours)

3. Verify nameserver change:
   ```bash
   dig NS yourdomain.com +short
   ```

### 3.3 Initial DNS Records

Set up critical DNS records:

```
# Root domain
A    @    [your-server-ip]    (or CNAME to Pages)

# WWW subdomain
CNAME    www    @

# API subdomain
CNAME    api    @

# CDN subdomain (for R2)
CNAME    cdn    @
```

## 4. GitHub Actions Secrets

### 4.1 Required Secrets

Add these secrets to GitHub repository:
**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Value | Purpose |
|------------|-------|---------|
| `CLOUDFLARE_API_TOKEN` | [API Token] | Worker/Pages deployments |
| `CLOUDFLARE_ACCOUNT_ID` | [Account ID] | Account-level operations |
| `CLOUDFLARE_ZONE_ID` | [Zone ID] | DNS operations |
| `CLOUDFLARE_DNS_TOKEN` | [DNS Token] | DNS record management |
| `CLOUDFLARE_R2_TOKEN` | [R2 Token] | Storage operations |

### 4.2 Optional Secrets (for enhanced security)

| Secret Name | Value | Purpose |
|------------|-------|---------|
| `CLOUDFLARE_EMAIL` | [Your email] | Fallback authentication |
| `ALLOWED_IPS` | [IP ranges] | Deployment IP whitelist |
| `NOTIFICATION_WEBHOOK` | [Webhook URL] | Deployment notifications |

### 4.3 Environment-Specific Secrets

For staging vs production:

**Production:**
- `CLOUDFLARE_API_TOKEN_PROD`
- `CLOUDFLARE_ZONE_ID_PROD`

**Staging:**
- `CLOUDFLARE_API_TOKEN_STAGING`
- `CLOUDFLARE_ZONE_ID_STAGING`

## 5. Wrangler CLI Setup

### 5.1 Local Development

Install Wrangler:
```bash
npm install -g wrangler
# or
npm install --save-dev wrangler
```

Authenticate:
```bash
wrangler login
```

### 5.2 CI/CD Configuration

Create `wrangler.toml`:
```toml
name = "gifdistributor-api"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[env.production]
name = "gifdistributor-api-prod"
route = "api.yourdomain.com/*"

[env.staging]
name = "gifdistributor-api-staging"
route = "api-staging.yourdomain.com/*"

[[r2_buckets]]
binding = "MEDIA_BUCKET"
bucket_name = "gifdistributor-media"

[[kv_namespaces]]
binding = "CACHE"
id = "your-kv-namespace-id"
```

## 6. R2 Storage Buckets

### 6.1 Create Buckets

1. Dashboard → **R2** → **Create bucket**
2. Create buckets:
   - `gifdistributor-media` - Primary media storage
   - `gifdistributor-cache` - CDN cache
   - `gifdistributor-logs` - Access logs (optional)

3. Configure bucket settings:
   - Enable **Public Access** (if needed)
   - Set **Storage Class** based on access patterns
   - Configure **Lifecycle Rules** for cost optimization

### 6.2 Custom Domain for R2

1. Navigate to bucket settings
2. Click **Connect Domain**
3. Enter subdomain (e.g., `cdn.yourdomain.com`)
4. Cloudflare automatically creates DNS CNAME
5. SSL certificate provisioned automatically

## 7. Billing & Cost Management

### 7.1 Payment Method

1. Dashboard → **Billing** → **Payment Info**
2. Add credit card or PayPal
3. Set billing email and notifications

### 7.2 Cost Alerts

1. Navigate to **Billing** → **Notifications**
2. Set up alerts:
   - Usage threshold (e.g., 80% of free tier)
   - Spending limit
   - Invoice generation

### 7.3 Budget Estimation

**Free Tier Limits:**
- Workers: 100,000 requests/day
- R2 Storage: 10 GB/month
- R2 Class A Operations: 1M/month
- R2 Class B Operations: 10M/month
- Pages: Unlimited requests, 500 builds/month

**Paid Usage:**
- Workers: $5/10M requests
- R2 Storage: $0.015/GB/month
- R2 Egress: Free to Cloudflare CDN

## 8. Security Best Practices

### 8.1 API Token Rotation

Schedule for quarterly rotation:
1. Generate new token with same permissions
2. Update GitHub Secrets
3. Verify deployments work
4. Delete old token from Cloudflare

### 8.2 Access Logging

Enable audit logs:
1. Dashboard → **Analytics & Logs** → **Audit Logs**
2. Monitor API token usage
3. Set up alerts for suspicious activity

### 8.3 IP Restrictions

Restrict API tokens:
1. Get GitHub Actions IP ranges:
   ```bash
   curl https://api.github.com/meta | jq '.actions'
   ```
2. Apply to Cloudflare API token configuration

### 8.4 Secret Scanning

1. Enable GitHub secret scanning:
   - Repository **Settings** → **Security** → **Secret scanning**
2. Add Cloudflare tokens to `.gitignore`:
   ```
   .env*
   .dev.vars
   wrangler.toml.local
   ```

## 9. Verification Steps

### 9.1 Test Cloudflare Access

```bash
# Test API token
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"

# Expected response: "status": "active"
```

### 9.2 Test Wrangler Deployment

```bash
# Test deploy to staging
wrangler deploy --env staging

# Test deploy to production (dry run)
wrangler deploy --env production --dry-run
```

### 9.3 Test GitHub Actions

Create `.github/workflows/test-credentials.yml`:
```yaml
name: Test Cloudflare Credentials

on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verify API Token
        run: |
          curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
            -H "Authorization: Bearer ${{ secrets.CLOUDFLARE_API_TOKEN }}" \
            -H "Content-Type: application/json"

      - name: Check Account ID
        run: |
          echo "Account ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}"
          echo "Length: ${#CLOUDFLARE_ACCOUNT_ID}"
        env:
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
```

## 10. Troubleshooting

### Common Issues

**Issue: "Invalid API Token"**
- Verify token hasn't expired
- Check token permissions match requirements
- Ensure correct token is used in CI/CD

**Issue: "Zone not found"**
- Verify Zone ID is correct
- Ensure token has access to zone
- Check domain is active in Cloudflare

**Issue: "Wrangler authentication failed"**
- Run `wrangler logout` then `wrangler login`
- Clear `~/.wrangler/config/` directory
- Regenerate API token

**Issue: "R2 bucket access denied"**
- Verify R2 token has correct permissions
- Check bucket name matches configuration
- Ensure bucket exists in correct account

### Debug Commands

```bash
# Verify Cloudflare API connectivity
wrangler whoami

# List all zones
wrangler zones list

# List R2 buckets
wrangler r2 bucket list

# Check deployment status
wrangler deployments list
```

## 11. Migration to IaC

Once manual bootstrap is complete, credentials enable IaC:

1. **Terraform/Pulumi Setup:**
   ```hcl
   provider "cloudflare" {
     api_token = var.cloudflare_api_token
   }
   ```

2. **Import Existing Resources:**
   ```bash
   terraform import cloudflare_zone.main ${CLOUDFLARE_ZONE_ID}
   terraform import cloudflare_record.api ${DNS_RECORD_ID}
   ```

3. **Gradual Migration:**
   - Start with new resources in IaC
   - Incrementally import manual resources
   - Eventually manage all infra as code

## 12. Compliance & Audit

### Documentation Requirements

Maintain record of:
- [ ] All API tokens created (purpose, scope, creation date)
- [ ] Token rotation schedule
- [ ] Access audit log review schedule
- [ ] Billing alert thresholds
- [ ] Emergency access procedures

### Regular Review Checklist

**Monthly:**
- [ ] Review API token usage in audit logs
- [ ] Check billing for unexpected charges
- [ ] Verify all tokens still needed

**Quarterly:**
- [ ] Rotate all API tokens
- [ ] Review and update IP restrictions
- [ ] Update documentation for any changes

**Annually:**
- [ ] Full security audit
- [ ] Review and update access policies
- [ ] Validate disaster recovery procedures

## References

- [Cloudflare API Documentation](https://developers.cloudflare.com/api/)
- [Wrangler CLI Documentation](https://developers.cloudflare.com/workers/wrangler/)
- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)

---

**Last Updated:** 2025-10-04
**Owner:** Infrastructure Team
**Review Cycle:** Quarterly
