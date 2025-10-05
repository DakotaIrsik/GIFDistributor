# CI/CD Quick Start Guide

Quick reference for setting up CI/CD credentials for GIFDistributor.

## 1. Cloudflare Setup (5 minutes)

### Get Credentials
```bash
# 1. Login to Cloudflare Dashboard
# 2. Navigate to My Profile → API Tokens
# 3. Create token with these permissions:
#    - Workers Scripts: Edit
#    - Pages: Edit
#    - Zone DNS: Edit
#    - Zone: Read
#    - R2: Edit
```

### Copy IDs
```bash
# Account ID: Workers & Pages → Overview → Right sidebar
CLOUDFLARE_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Zone ID: Websites → [your domain] → Overview → Right sidebar → API section
CLOUDFLARE_ZONE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 2. GitHub Secrets (2 minutes)

Navigate to: **Repository Settings → Secrets and variables → Actions → New repository secret**

Add these 3 required secrets:

| Name | Value | Where to find |
|------|-------|--------------|
| `CLOUDFLARE_API_TOKEN` | [Your API Token] | From step 1 |
| `CLOUDFLARE_ACCOUNT_ID` | [Account ID] | From step 1 |
| `CLOUDFLARE_ZONE_ID` | [Zone ID] | From step 1 |

## 3. Verify Setup (1 minute)

### Test API Token
```bash
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

Expected: `"status": "active"`

### Test Wrangler
```bash
wrangler whoami
wrangler deployments list
```

## 4. Deploy

```bash
# Deploy worker
wrangler deploy

# Deploy Pages (from CI/CD)
git push origin main
```

## Common Issues

| Error | Solution |
|-------|----------|
| "Invalid API Token" | Regenerate token with correct permissions |
| "Zone not found" | Double-check Zone ID is correct |
| "Account ID mismatch" | Ensure Account ID matches the zone's account |

## Next Steps

- See [bootstrap-credentials.md](./bootstrap-credentials.md) for detailed setup
- Configure [wrangler.toml](../wrangler.toml) for your environment
- Set up R2 buckets for media storage
- Enable billing alerts

---

**Total Setup Time:** ~8 minutes
