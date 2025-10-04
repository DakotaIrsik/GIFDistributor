# OIDC to Cloudflare + GitHub Actions Secrets Hygiene

## Overview

This document describes how to set up OpenID Connect (OIDC) authentication between GitHub Actions and Cloudflare, eliminating the need for long-lived API tokens and improving secrets hygiene.

## Why OIDC?

### Benefits

✅ **No Long-Lived Secrets**: Short-lived tokens issued per workflow run
✅ **Automatic Rotation**: Tokens expire after each workflow execution
✅ **Audit Trail**: Built-in identity verification and logging
✅ **Reduced Attack Surface**: No secrets to steal or leak
✅ **Fine-Grained Access**: Scope tokens to specific repositories and branches

### Traditional vs OIDC Authentication

| Aspect | Traditional API Token | OIDC |
|--------|----------------------|------|
| **Lifespan** | Long-lived (months/years) | Short-lived (minutes) |
| **Rotation** | Manual, every 90 days | Automatic, per workflow |
| **Storage** | GitHub Secrets | No storage needed |
| **Revocation** | Manual | Automatic expiration |
| **Compromise Risk** | High | Low |
| **Audit Trail** | Limited | Comprehensive |

## Architecture

```
┌─────────────────┐
│ GitHub Actions  │
│   Workflow      │
└────────┬────────┘
         │ 1. Request OIDC token
         │    (with audience=cloudflare)
         ▼
┌─────────────────┐
│  GitHub OIDC    │
│   Provider      │
└────────┬────────┘
         │ 2. Issue signed JWT token
         │    (claims: repo, actor, ref)
         ▼
┌─────────────────┐
│   Cloudflare    │
│  API Gateway    │
└────────┬────────┘
         │ 3. Verify JWT signature
         │ 4. Check trust policy
         │ 5. Issue API token
         ▼
┌─────────────────┐
│   Cloudflare    │
│    Services     │
└─────────────────┘
```

## Setup Instructions

### Step 1: Configure Cloudflare Trust Relationship

1. **Enable OIDC in Cloudflare**

   Go to Cloudflare Dashboard → Account Settings → API Tokens → OIDC

2. **Add GitHub as OIDC Provider**

   ```json
   {
     "name": "GitHub Actions",
     "issuer": "https://token.actions.githubusercontent.com",
     "jwks_uri": "https://token.actions.githubusercontent.com/.well-known/jwks",
     "audiences": ["cloudflare"],
     "subject_claims": [
       "repo:<org>/<repo>:ref:refs/heads/main",
       "repo:<org>/<repo>:environment:production"
     ]
   }
   ```

3. **Configure Trust Policy**

   Create a trust policy that maps GitHub claims to Cloudflare permissions:

   ```json
   {
     "trust_policy": {
       "conditions": {
         "StringEquals": {
           "token.actions.githubusercontent.com:aud": "cloudflare",
           "token.actions.githubusercontent.com:sub": "repo:<org>/<repo>:ref:refs/heads/main"
         }
       },
       "permissions": [
         "pages:deploy",
         "workers:deploy",
         "r2:write"
       ]
     }
   }
   ```

### Step 2: Configure GitHub Repository

1. **Set Repository Secrets** (minimal set)

   Only store non-sensitive identifiers:
   ```
   CLOUDFLARE_ACCOUNT_ID=<your-account-id>
   ```

   ❌ Do NOT store:
   - `CLOUDFLARE_API_TOKEN` (use OIDC instead)
   - `CLOUDFLARE_API_KEY` (legacy, insecure)

2. **Enable Required Permissions**

   In `.github/workflows/oidc-cloudflare.yml`:
   ```yaml
   permissions:
     id-token: write    # Required for OIDC
     contents: read     # Required for checkout
   ```

3. **Create Production Environment**

   Repository Settings → Environments → New Environment → `production`
   - Enable "Required reviewers" for production deployments
   - Add `CLOUDFLARE_ACCOUNT_ID` to environment secrets

### Step 3: Update Workflow

Use the provided `.github/workflows/oidc-cloudflare.yml` workflow that:
1. Requests OIDC token from GitHub
2. Exchanges it for Cloudflare API token
3. Uses token for deployment
4. Token expires after workflow completes

### Step 4: Verify Setup

1. **Test OIDC Authentication**

   ```bash
   # Trigger workflow manually
   gh workflow run oidc-cloudflare.yml
   ```

2. **Check Workflow Logs**

   Verify:
   - OIDC token successfully obtained
   - Cloudflare authentication succeeded
   - Deployment completed
   - Token was masked in logs

3. **Audit Cloudflare Activity**

   Cloudflare Dashboard → Audit Logs
   - Check for OIDC authentication events
   - Verify correct repository/branch claims

## Secrets Hygiene Best Practices

### Current State Assessment

#### ✅ Good Practices Already in Place
- Separate keys for production and development
- Automated rotation reminders (90-day schedule)
- Environment-based secret protection
- Self-hosted runners for sensitive workflows

#### 🔄 Improvements with OIDC
- Eliminate long-lived Cloudflare API tokens
- Automatic token rotation per workflow
- Built-in audit trail for all deployments
- Reduced secrets management overhead

### Secrets Hygiene Checklist

#### Critical Secrets (Require OIDC or Rotation)
- [x] `CLOUDFLARE_API_TOKEN` → Migrated to OIDC
- [x] `OPENAI_API_KEY` → Automated rotation (90 days)
- [x] `OPENAI_API_KEY_DEV` → Automated rotation (90 days)

#### Non-Sensitive Identifiers (Safe to Store)
- [ ] `CLOUDFLARE_ACCOUNT_ID` (public identifier)
- [ ] `CLOUDFLARE_PROJECT_NAME` (public identifier)
- [ ] `CLOUDFLARE_ZONE_ID` (public identifier)

#### Secrets to NEVER Store
- ❌ Database passwords (use managed identities)
- ❌ Private keys (use OIDC/SSO)
- ❌ OAuth client secrets (use PKCE flow where possible)

### Migration from Traditional Tokens

#### Before (Traditional)
```yaml
- name: Deploy to Cloudflare
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}  # Long-lived
  run: npx wrangler deploy
```

#### After (OIDC)
```yaml
- name: Authenticate via OIDC
  id: auth
  run: |
    OIDC_TOKEN=$(curl -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
      "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=cloudflare" | jq -r '.value')
    # Exchange for Cloudflare token

- name: Deploy to Cloudflare
  env:
    CLOUDFLARE_API_TOKEN: ${{ env.CLOUDFLARE_API_TOKEN }}  # Short-lived
  run: npx wrangler deploy
```

### Monitoring & Compliance

#### Automated Monitoring
- OIDC token issuance logged in GitHub audit log
- Cloudflare access logged in API audit log
- Deployment events tracked in workflow summaries

#### Compliance Requirements
- **SOC 2**: OIDC provides non-repudiation and audit trail
- **ISO 27001**: Eliminates long-lived credential risks
- **PCI DSS**: Short-lived tokens reduce exposure window

#### Regular Audits
- Weekly: Review GitHub Actions logs for OIDC usage
- Monthly: Audit Cloudflare access patterns
- Quarterly: Review and update trust policies

### Troubleshooting

#### Common Issues

**Issue**: OIDC token request fails
```
Error: Failed to get OIDC token
```
**Solution**: Ensure `id-token: write` permission is set in workflow

**Issue**: Cloudflare rejects OIDC token
```
Error: Invalid subject claim
```
**Solution**: Verify trust policy subject claims match your repository

**Issue**: Token exchange fails
```
Error: Unable to exchange OIDC token
```
**Solution**: Check Cloudflare OIDC configuration and audience parameter

#### Debug Mode

Enable debug logging:
```yaml
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

### Security Incident Response

#### If OIDC Configuration is Compromised

1. **Immediate Actions** (within 1 hour)
   - Revoke Cloudflare OIDC trust policy
   - Disable affected workflows
   - Review Cloudflare audit logs

2. **Investigation** (within 24 hours)
   - Identify unauthorized deployments
   - Check for data exfiltration
   - Document incident timeline

3. **Remediation** (within 1 week)
   - Reconfigure OIDC trust policy with stricter claims
   - Update workflow permissions
   - Conduct security training

### References

- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Cloudflare Zero Trust OIDC](https://developers.cloudflare.com/cloudflare-one/identity/idp-integration/generic-oidc/)
- [OIDC Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)

## Roadmap

### Phase 1: OIDC Implementation (Complete)
- [x] Configure Cloudflare OIDC trust
- [x] Update GitHub Actions workflows
- [x] Document setup process

### Phase 2: Extended OIDC Adoption
- [ ] Migrate AWS deployments to OIDC
- [ ] Implement OIDC for GCP services
- [ ] Add OIDC for database access (if applicable)

### Phase 3: Advanced Security
- [ ] Implement keyless signing with Sigstore
- [ ] Add attestation for deployments
- [ ] Enable GitHub Advanced Security features
