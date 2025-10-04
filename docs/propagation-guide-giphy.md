# GIPHY Propagation Guide

## Overview

GIPHY is one of the largest GIF platforms with billions of daily searches. Content uploaded to GIPHY goes through a review process before appearing in public search results.

## Propagation Timeline

```
Upload → Partner Queue → Manual Review → Indexing → Public Search
  ↓           ↓              ↓              ↓            ↓
Instant    0-12 hrs      12-24 hrs      24-48 hrs   LIVE
```

**Expected time to public visibility:** 1-48 hours (average: 24 hours)

## Account Types

### Standard Account
- Manual review for all uploads
- 10 uploads/day limit (Free tier)
- Lower priority in review queue
- Standard indexing timeline

### Partner Account
- Higher upload limits (100+/day)
- Priority review queue
- Faster indexing
- Advanced analytics
- Channel management features

**How to get Partner status:**
- Consistent quality uploads
- Good engagement metrics
- No policy violations
- Apply via GIPHY Partner Portal

## Upload Process

### 1. Content Submission

When you upload via GIFDistributor:
```
GIFDistributor → GIPHY Upload API → GIPHY Partner Portal → Review Queue
```

**What gets sent:**
- GIF file (optimized format)
- Title and source URL
- Tags (up to 20 per GIF)
- Source attribution
- Content hash (for deduplication)

### 2. Review Process

GIPHY reviews content for:
- **Policy compliance** - SFW requirements, no copyright violations
- **Quality standards** - Resolution, compression, duration limits
- **Metadata accuracy** - Tags match content, no spam
- **Duplicate detection** - Similar content already exists

**Review timeline:**
- Peak hours (9am-5pm EST): 24-48 hours
- Off-peak hours: 12-24 hours
- Weekends: May extend to 48+ hours

### 3. Indexing

Once approved, content enters GIPHY's search index:
- **Initial indexing** - 1-4 hours after approval
- **Full propagation** - 4-12 hours (all CDN nodes)
- **Search optimization** - 24-48 hours (ranking algorithms)

## Tag Strategy for GIPHY

### Best Practices

**Use descriptive, searchable tags:**
```
Good: "happy dance", "celebration", "excited", "party time"
Bad: "gif", "animation", "cool", "viral"
```

**Tag categories to include:**
1. **Action/emotion** - What's happening (dance, laugh, cry)
2. **Context** - When to use (celebration, reaction, birthday)
3. **Style** - Visual characteristics (retro, colorful, minimal)
4. **Trending** - Current events or memes (when relevant)

**Tag limits:**
- Minimum: 5 tags (recommended)
- Maximum: 20 tags
- Optimal: 10-15 high-quality tags

### Common Mistakes

❌ **Over-tagging**
```
Tags: happy, happiness, joy, joyful, joyous, pleased, cheerful, delighted, glad, elated, ecstatic, thrilled, excited, enthusiastic...
```

✅ **Focused tagging**
```
Tags: happy, celebration, excited, party, good news, success, achievement
```

❌ **Irrelevant tags** (spam)
```
Tags for a cat GIF: dog, funny, meme, viral, trending, popular, LOL
```

✅ **Relevant tags**
```
Tags for a cat GIF: cat, kitten, cute cat, playful, pet, cat reaction
```

## Troubleshooting

### Content Not Appearing After 48 Hours

**Step 1: Check GIPHY Partner Dashboard**
- Login to GIPHY Partner Portal
- Navigate to "My GIFs"
- Check upload status

**Possible statuses:**
- **Pending Review** - Still in queue (contact support if >48hrs)
- **Needs Attention** - Metadata issues to fix
- **Rejected** - See rejection reason
- **Live** - Content is approved but may not be indexed yet

**Step 2: Verify Search**
- Search by exact title
- Search by your username/channel
- Use specific unique tags

**Step 3: Check Indexing**
- Direct URL works but search doesn't? → Still indexing
- Direct URL doesn't work? → Not approved or technical issue

### Content Rejected

**Common rejection reasons:**

| Reason | Fix |
|--------|-----|
| Low quality | Re-upload at higher resolution (min 480px width) |
| Too short/long | Keep duration between 1-10 seconds |
| Policy violation | Review GIPHY Guidelines, ensure SFW content |
| Duplicate content | Content too similar to existing GIF |
| Spam tags | Remove irrelevant or repetitive tags |
| Copyright issue | Ensure you own rights or content is public domain |

**How to appeal:**
1. Review rejection notice in Partner Portal
2. Fix identified issues
3. Re-upload (don't spam identical content)
4. Contact GIPHY support for wrongful rejections

### Poor Search Ranking

If content is live but hard to find:

**Improve engagement:**
- Share your GIPHY link on social media
- Use GIFs in Discord/Slack to drive views
- Build a following on GIPHY

**Optimize tags:**
- Replace generic tags with specific searchable terms
- Add trending/seasonal tags (when relevant)
- Match tags to actual search behavior

**Quality signals:**
- Higher resolution = better ranking
- Good loop quality (seamless)
- Appropriate file size (not too large)

## Best Practices for Success

### Content Quality

**Technical requirements:**
- Minimum width: 480px (720px+ recommended)
- Maximum file size: 8MB (under 5MB ideal)
- Duration: 1-10 seconds (2-4 seconds optimal)
- Format: GIF or MP4 (GIFDistributor handles conversion)

**Visual quality:**
- Clean, high-quality source material
- Smooth, seamless loops
- Good color palette (not over-compressed)
- Clear focal point

### Metadata Quality

**Title best practices:**
- Descriptive but concise
- Include main subject/emotion
- Natural language (how people search)
- Avoid ALL CAPS or excessive punctuation

**Examples:**
```
Good: "Happy Birthday Celebration Dance"
Bad: "AMAZING GIF!!! MUST SEE!!!"

Good: "Cat Knocking Things Off Table"
Bad: "Funny Cat Gif Animation"
```

### Upload Timing

**Optimal times for faster review:**
- Weekday mornings (EST)
- Avoid Friday afternoons
- Avoid major holidays

**Strategic timing:**
- Upload 2-3 days before events (holidays, awards shows)
- Align with trending topics (when appropriate)
- Batch uploads during optimal times

## Tracking Performance

### Metrics to Monitor

GIPHY provides analytics for Partner accounts:
- **Views** - Total times GIF was viewed
- **Shares** - How often GIF was shared
- **Sources** - Where traffic comes from
- **Searches** - What terms led to your GIF

### Success Indicators

**Good propagation:**
- Appears in search within 48 hours
- Shows in top 20 for specific tags
- Steady view growth
- Share activity

**Poor propagation:**
- Not searchable after 48 hours
- Very low views (<10 in first week)
- No shares
- Doesn't appear for exact tags

## Channel Strategy

GIPHY Channels help organize content:

**Benefits:**
- Followers get notified of new uploads
- Channel page showcases your brand
- Better discoverability for related content
- Custom URL (giphy.com/yourchannel)

**Setup via GIFDistributor:**
1. Enable GIPHY Channel in settings
2. Configure channel metadata
3. All uploads go to your channel
4. Promote channel for followers

## Getting More Visibility

### Internal GIPHY Promotion

- **Featured content** - High-quality uploads may get featured
- **Trending sections** - Content with high engagement
- **Category pages** - Relevant well-tagged content

### External Promotion

- Share direct GIPHY links on social media
- Embed GIFs in blog posts (with GIPHY links)
- Use in messaging apps (drives GIPHY traffic)
- Cross-promote on other platforms

## API and Integration

GIFDistributor uses GIPHY Partner API:
- Authenticated uploads
- Metadata submission
- Status tracking
- Analytics retrieval

**Rate limits:**
- Free tier: 10 uploads/day
- Pro tier: 100 uploads/day
- Enterprise: Custom limits

## Resources

- **GIPHY Partner Portal**: https://giphy.com/partners
- **GIPHY Guidelines**: https://support.giphy.com/hc/en-us/articles/360020027752
- **GIPHY Engineering Blog**: https://engineering.giphy.com/
- **GIFDistributor Support**: See [main documentation](./propagation-guide-overview.md)

## FAQ

**Q: Can I delete or update a GIF after it's live?**
A: Yes, via GIPHY Partner Portal. Changes may take 24 hours to propagate.

**Q: Why do some of my GIFs rank higher than others?**
A: GIPHY uses engagement signals (views, shares) and quality metrics to rank content.

**Q: Can I upload the same content to multiple platforms?**
A: Yes, GIFDistributor handles cross-platform distribution automatically.

**Q: How long does content stay on GIPHY?**
A: Indefinitely, unless you delete it or it violates policies.

---

**Last Updated:** 2025-10-04
