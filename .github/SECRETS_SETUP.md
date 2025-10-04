# GitHub Actions Secrets Setup Guide

This guide walks through setting up secrets for the GIFDistributor project.

## Quick Start

### 1. Create OpenAI API Keys

1. Go to [OpenAI API Keys Dashboard](https://platform.openai.com/api-keys)
2. Create two separate API keys:
   - `GIFDistributor-Production` - for production use
   - `GIFDistributor-Dev` - for development/staging

### 2. Configure GitHub Environments

Navigate to: `Settings → Environments`

#### Create Production Environment
1. Click "New environment"
2. Name: `production`
3. Add protection rules:
   - ✅ Required reviewers (select team members)
   - ✅ Wait timer: 5 minutes (optional)
4. Add environment secret:
   - Name: `OPENAI_API_KEY`
   - Value: [Production API key from step 1]

#### Create Staging Environment
1. Click "New environment"
2. Name: `staging`
3. Add environment secret:
   - Name: `OPENAI_API_KEY`
   - Value: [Dev API key from step 1]

#### Create Development Environment
1. Click "New environment"
2. Name: `development`
3. Add environment secret:
   - Name: `OPENAI_API_KEY`
   - Value: [Dev API key from step 1]

### 3. Add Repository Secrets (Optional)

For workflows that don't use environments:

Navigate to: `Settings → Secrets and variables → Actions → New repository secret`

Add:
- `OPENAI_API_KEY_DEV` - Development key (for testing workflows)

> **Note:** Production key should ONLY be in the production environment, not as a repository secret.

## Using Secrets in Workflows

### Environment-Specific Workflow

```yaml
name: AI Safety Scan

on: [push]

jobs:
  scan-production:
    runs-on: ubuntu-latest
    environment: production  # Uses production environment secrets

    steps:
      - uses: actions/checkout@v4

      - name: Run safety scan
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python ai_safety_scanner.py

  scan-development:
    runs-on: ubuntu-latest
    environment: development  # Uses development environment secrets

    steps:
      - uses: actions/checkout@v4

      - name: Run safety scan
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python ai_safety_scanner.py
```

### Repository Secret Workflow

```yaml
name: Test

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Run tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY_DEV }}
        run: npm test
```

## Secret Rotation

### Rotation Schedule

Rotate secrets every **90 days** minimum.

### Automated Reminders

The `secret-rotation-check.yml` workflow runs monthly and creates issues when rotation is needed.

### Manual Rotation Process

1. **Generate new key** from OpenAI dashboard
2. **Test new key** in development environment first
3. **Update GitHub secret** with new value
4. **Verify workflows** run successfully
5. **Revoke old key** after 7-day grace period
6. **Update rotation date** in `secret-rotation-check.yml`

## Security Checklist

- [ ] Production secrets use Environment protection rules
- [ ] Separate API keys for production and development
- [ ] Repository secrets NOT used for production credentials
- [ ] Secret rotation workflow enabled
- [ ] Team trained on secret handling procedures
- [ ] `.env` files added to `.gitignore`
- [ ] No secrets committed to version control

## Testing Secret Configuration

Run this command to verify secrets are configured correctly:

```bash
# Test development secret is accessible
gh secret list

# Test workflow can access secrets (will show masked value)
gh workflow run test.yml
```

## Troubleshooting

### "Secret not found" error

- Verify secret name matches exactly (case-sensitive)
- Check if workflow has access to the environment
- Ensure environment protection rules are satisfied

### "Unauthorized" error with OpenAI API

- Verify API key is valid and not expired
- Check OpenAI account has sufficient credits
- Ensure key has correct permissions

### Workflow can't access environment secret

- Verify `environment:` key is set in workflow job
- Check environment protection rules (required reviewers, etc.)
- Ensure runner has permission to access environment

## Additional Resources

- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Using Environments for Deployment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [OpenAI API Keys Best Practices](https://platform.openai.com/docs/guides/production-best-practices/api-keys)
- [Secrets Management Documentation](../docs/secrets-management.md)
