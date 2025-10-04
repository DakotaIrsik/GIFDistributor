# Security Checklist for Bootstrap Credentials

## Initial Setup

### Cloudflare API Tokens
- [ ] API tokens created with minimum required permissions (least privilege)
- [ ] Separate tokens for different purposes (deployment, DNS, R2)
- [ ] Tokens stored only in GitHub Secrets, never committed to repo
- [ ] IP restrictions applied to API tokens (GitHub Actions IP ranges)
- [ ] Token expiration dates set or rotation schedule established

### GitHub Secrets
- [ ] All Cloudflare credentials stored as encrypted secrets
- [ ] Secret names follow consistent naming convention
- [ ] No secrets in environment variables in workflow logs
- [ ] GitHub secret scanning enabled
- [ ] Dependabot alerts enabled

### DNS Security
- [ ] DNSSEC enabled on Cloudflare zones
- [ ] CAA records configured to restrict certificate issuance
- [ ] Rate limiting enabled for DNS queries
- [ ] Audit logging enabled for DNS changes

### Access Control
- [ ] Two-factor authentication (2FA) enabled on Cloudflare account
- [ ] 2FA enabled on domain registrar
- [ ] 2FA enabled on GitHub account
- [ ] Admin access limited to necessary personnel only
- [ ] Service account tokens used in CI/CD (not personal tokens)

## Ongoing Security

### Monthly Reviews
- [ ] Review Cloudflare audit logs for suspicious API activity
- [ ] Check billing for unexpected usage patterns
- [ ] Verify all API tokens are still in use
- [ ] Review GitHub Actions workflow runs for anomalies
- [ ] Scan for accidentally committed secrets

### Quarterly Tasks
- [ ] Rotate all API tokens
- [ ] Update IP allowlists with current GitHub Actions ranges
- [ ] Review and update access permissions
- [ ] Test token rotation procedures
- [ ] Audit list of users with access to secrets

### Security Monitoring
- [ ] Cloudflare Web Application Firewall (WAF) rules configured
- [ ] Rate limiting rules in place
- [ ] Alerts configured for:
  - Failed authentication attempts
  - Unusual API usage patterns
  - Billing threshold exceeded
  - DNS changes
- [ ] Log retention policy established and documented

## Incident Response

### Preparation
- [ ] Incident response plan documented
- [ ] Emergency contact list maintained
- [ ] Token revocation procedure documented
- [ ] Backup credentials stored securely offline
- [ ] Rollback procedures tested

### In Case of Compromise
1. [ ] Immediately revoke compromised API token(s)
2. [ ] Generate new API token(s) with fresh credentials
3. [ ] Update GitHub Secrets with new tokens
4. [ ] Review audit logs for unauthorized activities
5. [ ] Assess scope of potential data exposure
6. [ ] Document incident and lessons learned
7. [ ] Update security procedures based on findings

## Compliance

### Documentation
- [ ] Bootstrap procedure documented
- [ ] API token purposes and scopes documented
- [ ] Rotation schedule documented
- [ ] Access control policy documented
- [ ] Data retention policy documented

### Audit Trail
- [ ] All credential changes logged
- [ ] Regular access reviews scheduled
- [ ] Compliance reports generated quarterly
- [ ] External security audit scheduled annually

## Best Practices

### Do's ✅
- Use API tokens instead of Global API Key
- Implement principle of least privilege
- Enable all available security features
- Regularly rotate credentials
- Use separate credentials for staging/production
- Monitor and log all API access
- Keep dependencies up to date
- Use secure channels for credential sharing

### Don'ts ❌
- Never commit credentials to version control
- Never share API tokens between environments
- Never use personal accounts for service credentials
- Never disable security features for convenience
- Never skip security updates
- Never log sensitive data in plain text
- Never use same token for multiple purposes
- Never skip testing token rotation

## Emergency Contacts

| Role | Contact | Purpose |
|------|---------|---------|
| Security Lead | [Name/Email] | Security incidents |
| Infrastructure Lead | [Name/Email] | Service outages |
| Cloudflare Support | support@cloudflare.com | Platform issues |
| Domain Registrar | [Support contact] | DNS/domain issues |

## Security Tools

### Recommended Tools
- **Secret Scanning:** GitHub secret scanning, GitGuardian, TruffleHog
- **Token Management:** HashiCorp Vault, AWS Secrets Manager
- **Monitoring:** Cloudflare Analytics, Datadog, New Relic
- **Vulnerability Scanning:** Snyk, Dependabot
- **SAST/DAST:** SonarQube, OWASP ZAP

### Security Headers
Ensure these headers are configured:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

## Verification

### Weekly Automated Checks
```bash
#!/bin/bash
# Add to .github/workflows/security-check.yml

# Check for exposed secrets
git secrets --scan

# Verify API token is valid
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"

# Check DNS configuration
dig +short yourdomain.com

# Verify SSL certificate
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

---

**Last Review:** 2025-10-04
**Next Review:** 2025-11-04
**Owner:** Security Team
