# Secrets Management & Rotation

## Overview

This document outlines the secrets management strategy for GIFDistributor, focusing on secure storage, access control, and regular rotation of sensitive credentials.

## GitHub Actions Secrets

### Required Secrets

#### Production Secrets
- `OPENAI_API_KEY` - OpenAI API key for AI safety scanning
  - **Rotation Schedule**: Every 90 days
  - **Access**: Production workflows only
  - **Backup**: Store previous key for 7-day rollback period

#### Development/Staging Secrets
- `OPENAI_API_KEY_DEV` - Separate key for development/staging
  - **Rotation Schedule**: Every 90 days
  - **Access**: Development and staging workflows

### Secret Configuration

#### Setting Up Secrets

1. **Repository Secrets** (Settings → Secrets and variables → Actions)
   ```
   OPENAI_API_KEY          # Production key
   OPENAI_API_KEY_DEV      # Development key
   ```

2. **Environment-Specific Secrets**

   Create environments: `production`, `staging`, `development`

   **Production Environment:**
   - Protection rules: Required reviewers
   - Secrets: `OPENAI_API_KEY`

   **Staging Environment:**
   - Secrets: `OPENAI_API_KEY_DEV`

   **Development Environment:**
   - Secrets: `OPENAI_API_KEY_DEV`

#### Using Secrets in Workflows

```yaml
jobs:
  safety-scan:
    runs-on: ubuntu-latest
    environment: production  # Uses environment-specific secrets

    steps:
      - name: Run AI Safety Scanner
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python ai_safety_scanner.py
```

### Secret Rotation Strategy

#### Rotation Process

1. **Generate New Key**
   - Create new OpenAI API key from dashboard
   - Test key in development environment

2. **Update GitHub Secrets**
   - Add new key as `OPENAI_API_KEY_NEW`
   - Test workflows with new key
   - Update `OPENAI_API_KEY` with new value
   - Delete `OPENAI_API_KEY_NEW`

3. **Revoke Old Key**
   - Wait 7 days for rollback period
   - Revoke old key from OpenAI dashboard
   - Document rotation in changelog

#### Rotation Schedule

| Secret | Rotation Frequency | Next Rotation |
|--------|-------------------|---------------|
| OPENAI_API_KEY | 90 days | Auto-reminder |
| OPENAI_API_KEY_DEV | 90 days | Auto-reminder |

#### Automated Rotation Reminders

A GitHub Actions workflow runs monthly to check rotation status and create issues for expiring secrets.

See: `.github/workflows/secret-rotation-check.yml`

### Security Best Practices

#### Do's ✅
- Use environment-specific secrets for different deployment stages
- Rotate secrets every 90 days minimum
- Use GitHub Environments for production secret protection
- Limit secret access to specific workflows/environments
- Audit secret usage regularly via workflow logs
- Use separate API keys for development and production

#### Don'ts ❌
- Never log secret values (even masked)
- Don't share secrets between environments unnecessarily
- Don't hardcode secrets in code or config files
- Don't use the same API key across multiple services
- Never commit `.env` files with real secrets

### Secret Hygiene Checklist

- [ ] All secrets stored in GitHub Actions Secrets (not in code)
- [ ] Production secrets use Environment protection rules
- [ ] Separate keys for production and development
- [ ] Rotation schedule documented and automated
- [ ] Workflow logs reviewed for secret exposure
- [ ] Old keys revoked after rotation
- [ ] Team members trained on secret handling

### Incident Response

If a secret is compromised:

1. **Immediate Actions** (within 1 hour)
   - Revoke compromised key from provider
   - Generate and deploy new key
   - Review access logs for unauthorized usage

2. **Investigation** (within 24 hours)
   - Identify how secret was exposed
   - Determine scope of potential access
   - Document incident timeline

3. **Remediation** (within 1 week)
   - Implement additional controls
   - Update security procedures
   - Conduct team training if needed

### Monitoring & Auditing

#### Usage Monitoring
- Review GitHub Actions logs weekly
- Monitor OpenAI API usage dashboard
- Set up alerts for unusual activity

#### Audit Trail
- All secret access logged in workflow runs
- Rotation history maintained in `docs/changelog.md`
- Incident reports stored in `docs/security/incidents/`

### Alternative Secret Management

For production deployments beyond GitHub Actions:

#### Cloud Providers
- **AWS**: AWS Secrets Manager + IAM roles
- **Azure**: Azure Key Vault + Managed Identity
- **GCP**: Secret Manager + Workload Identity

#### Secret Managers
- HashiCorp Vault
- Doppler
- 1Password Secrets Automation

### References

- [GitHub Actions Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [OpenAI API Key Best Practices](https://platform.openai.com/docs/guides/production-best-practices/api-keys)
