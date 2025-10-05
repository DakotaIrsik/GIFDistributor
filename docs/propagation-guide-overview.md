# GIF Propagation Guide: Overview

## Introduction

This guide helps you understand how your GIFs propagate across different platforms after uploading to GIFDistributor. Content distribution is **not instantaneous** - each platform has its own review process, indexing timeline, and discovery mechanisms.

## Quick Reference

| Platform | Typical Propagation Time | Review Process | Searchability |
|----------|-------------------------|----------------|---------------|
| **GIPHY** | 1-48 hours | Manual review for Partner accounts | Global search after approval |
| **Tenor** | 30 minutes - 24 hours | Automated + spot checks | Immediate in search (after indexing) |
| **Discord** | Immediate | None (direct embed) | Platform-wide search varies |
| **Slack** | Immediate | None (direct share) | Workspace-only |
| **Microsoft Teams** | Immediate | None (direct message) | Workspace-only |

## Platform-Specific Guides

For detailed information about each platform's propagation process:

- [GIPHY Propagation Guide](./propagation-guide-giphy.md)
- [Tenor Propagation Guide](./propagation-guide-tenor.md)
- [Discord Propagation Guide](./propagation-guide-discord.md)
- [Slack Propagation Guide](./propagation-guide-slack.md)
- [Microsoft Teams Propagation Guide](./propagation-guide-teams.md)

## General Best Practices

### 1. Optimize Your Metadata

**Tags are critical** for discoverability:
- Use 5-15 relevant tags per GIF
- Include both specific and general terms
- Add trending/seasonal tags when relevant
- Use natural language (how people actually search)

**Title guidelines:**
- Keep titles descriptive but concise (under 60 characters)
- Use searchable keywords
- Avoid special characters or emojis

### 2. Understand Platform Differences

**Public Platforms (GIPHY, Tenor):**
- Content is publicly searchable
- Requires moderation/review
- Propagation takes time
- Global audience reach

**Private Platforms (Discord, Slack, Teams):**
- Content is workspace/server-specific
- No review process
- Immediate availability
- Limited audience (your community only)

### 3. Content Policy Compliance

All platforms enforce SFW (Safe For Work) policies:
- No nudity or sexually suggestive content
- No violence or gore
- No hate speech or discriminatory content
- No copyright infringement

See our [Content Policy](../CONTENT_POLICY.md) for full details.

### 4. Tracking Propagation Status

GIFDistributor provides propagation tracking:

```
Status Indicators:
├─ PENDING     → Upload successful, awaiting platform processing
├─ PROCESSING  → Platform is reviewing/indexing your content
├─ LIVE        → Content is searchable and publicly available
└─ REJECTED    → Content did not pass platform review
```

Check your dashboard for real-time status updates.

## Troubleshooting

### Content Not Appearing in Search

**Check propagation time:**
- GIPHY: Wait 24-48 hours
- Tenor: Wait 1-24 hours
- Private platforms: Should be immediate

**Verify tags:**
- Are your tags too generic or too specific?
- Try searching exact tag terms
- Check for typos in metadata

**Review status:**
- Check if content is marked as LIVE
- Look for rejection notices
- Verify account standing

### Content Rejected

Common rejection reasons:
1. **Policy Violations** - Content doesn't meet SFW requirements
2. **Quality Issues** - Low resolution, excessive compression
3. **Metadata Problems** - Missing tags, inappropriate title
4. **Duplicate Content** - Content already exists on platform

**Next steps:**
- Review rejection reason in dashboard
- Fix issues and re-upload if appropriate
- Contact support if you believe rejection was in error

### Slow Propagation

Factors affecting propagation speed:
- **Platform load** - High traffic periods slow processing
- **Account tier** - Partner/verified accounts may process faster
- **Content complexity** - Some formats require additional processing
- **Review queue** - Manual reviews take longer

## Platform Rate Limits

Be aware of upload limits to avoid throttling:

| Platform | Free Tier | Pro Tier | Enterprise |
|----------|-----------|----------|------------|
| GIPHY | 10/day | 100/day | Custom |
| Tenor | 25/day | 250/day | Custom |
| Discord | Unlimited* | Unlimited* | Unlimited* |
| Slack | Unlimited* | Unlimited* | Unlimited* |
| Teams | Unlimited* | Unlimited* | Unlimited* |

*Private platforms don't limit uploads but may throttle based on workspace size/usage.

## Getting Help

- **Documentation**: Check platform-specific guides linked above
- **Dashboard**: Review propagation status and error messages
- **Support**: Contact support@gifdistributor.example for assistance
- **Community**: Join our Discord server for community help

## Next Steps

1. Read the [platform-specific guide](./propagation-guide-giphy.md) for your target platform
2. Optimize your content following [best practices](./content-optimization.md)
3. Review our [moderation FAQ](../MODERATION_FAQ.md) to avoid rejections

---

**Last Updated:** 2025-10-04
