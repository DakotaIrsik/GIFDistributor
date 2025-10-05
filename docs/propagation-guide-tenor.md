# Tenor Propagation Guide

## Overview

Tenor (owned by Google) powers GIF search in Google Images, Android keyboards, and many third-party applications. Content propagates faster than GIPHY but follows different optimization strategies.

## Propagation Timeline

```
Upload → API Submission → Automated Review → Indexing → Search Results
  ↓           ↓                ↓                ↓            ↓
Instant   <5 mins         5-30 mins         30 min-6 hrs   LIVE
```

**Expected time to public visibility:** 30 minutes - 24 hours (average: 2-4 hours)

## Account Types

### Standard Developer Account
- Automated review process
- API rate limits apply
- Public search indexing
- Basic analytics

### Partner Account
- Higher API rate limits
- Featured content opportunities
- Advanced analytics dashboard
- Priority support
- Custom integration options

**How to become a Partner:**
- Apply via Tenor Developer Portal
- Demonstrate consistent upload quality
- Show significant user engagement
- No policy violations

## Upload Process

### 1. Content Submission

GIFDistributor submits to Tenor API v2:
```
GIFDistributor → Tenor Upload API → Automated Processing → Content Indexing
```

**What gets sent:**
- Media file (MP4 or GIF)
- Tags (up to 30 per upload)
- Content description
- Source URL (optional)
- Locale/language metadata

### 2. Automated Review

Tenor uses automated scanning:
- **AI moderation** - Content safety scan
- **Quality checks** - Format, resolution, duration
- **Duplicate detection** - Hash-based deduplication
- **Metadata validation** - Tag relevance scoring

**Processing time:**
- Simple GIFs: 5-15 minutes
- Complex/long content: 15-30 minutes
- High-traffic periods: Up to 2 hours

**Spot checks:**
- Random manual review for quality
- Flagged content gets human review
- Reports trigger manual review

### 3. Indexing Strategy

Tenor's search indexing is faster than GIPHY:

**Initial index:**
- Content searchable in 30 minutes to 2 hours
- Appears in API results immediately after approval
- Mobile keyboard integration: 2-6 hours

**Search ranking:**
- Engagement signals (clicks, shares)
- Tag relevance to queries
- Content freshness (newer = boost)
- Source quality/authority

## Tag Strategy for Tenor

### Tenor-Specific Best Practices

Tenor emphasizes **natural language** and **search intent**:

**Query-focused tags:**
```
Think: "What would someone type to find this?"

Good: "excited yes", "fist bump celebration", "eye roll annoyed"
Bad: "reaction", "emotion", "people"
```

**Mobile keyboard optimization:**
```
Users type short queries on mobile:

Good: "omg", "lol", "congrats", "ugh"
Bad: "oh my goodness gracious", "congratulations on your achievement"
```

### Tag Categories

**1. Search queries (most important)**
- Actual phrases people search
- Include shorthand/slang (when appropriate)
- Common autocomplete suggestions

**2. Emotions and reactions**
- Specific feelings: "frustrated", "relieved", "awkward"
- Not just "happy" or "sad"

**3. Context and use case**
- When people would use this: "monday morning", "long day"
- Situations: "traffic jam", "deadline stress"

**4. Subjects and objects**
- Main visual elements: "dog", "coffee", "computer"
- Actions: "typing", "running", "eating"

### Tag Limits and Best Practices

- **Minimum:** 5 tags (10+ recommended)
- **Maximum:** 30 tags
- **Optimal:** 15-20 high-value tags
- **Language:** English primary, localized tags for other markets

### Tag Examples

**Example 1: Celebration GIF**
```
Excellent tags:
- "yes", "celebration", "excited", "won", "success"
- "fist pump", "celebrate good news", "nailed it"
- "achievement unlocked", "goal scored", "victory"

Mediocre tags:
- "happy", "good", "positive", "reaction"
```

**Example 2: Frustrated GIF**
```
Excellent tags:
- "ugh", "frustrated", "annoyed", "eye roll"
- "are you serious", "come on", "not again"
- "monday mood", "done with this", "over it"

Mediocre tags:
- "angry", "mad", "emotion", "feeling"
```

## Integration Points

### Google Products

Tenor powers GIF search in:
- **Google Images** - GIF search results
- **Gboard** (Google Keyboard) - Mobile typing
- **Google Messages** - SMS/RCS messaging
- **Android Keyboard** - System-wide

**Propagation to Google:**
- Google Images: 6-24 hours after Tenor indexing
- Gboard: 2-6 hours after indexing
- Search ranking varies by engagement

### Third-Party Integrations

Tenor API is used by many apps:
- Messaging apps (WhatsApp, Messenger, etc.)
- Social media platforms
- Productivity tools
- Gaming platforms

**Your content appears in:** Any app using Tenor API

## Troubleshooting

### Content Not Appearing in Search

**Check Tenor dashboard:**
1. Login to Tenor Developer Portal
2. Navigate to "My GIFs"
3. Check upload status and views

**Status indicators:**
- **Processing** - Still under review (wait 30 mins)
- **Live** - Approved and indexed
- **Rejected** - Failed review (see reason)

**If live but not searchable:**
- Try exact tag matches
- Check Google Images (may lag by hours)
- Search in Gboard keyboard
- Test via Tenor API directly

### Content Rejected

Common rejection reasons and fixes:

| Reason | Solution |
|--------|----------|
| **Policy violation** | Review Tenor Guidelines - ensure SFW |
| **Low quality** | Min 320x320px, good compression |
| **Duplicate** | Content too similar to existing GIF |
| **Invalid format** | Use MP4 or GIF (GIFDistributor handles this) |
| **Spam metadata** | Remove excessive/irrelevant tags |
| **Copyright claim** | Ensure content ownership or rights |

**Appeal process:**
1. Review rejection in dashboard
2. Fix issues if applicable
3. Contact Tenor support for wrongful rejections
4. Don't repeatedly upload identical rejected content

### Low Visibility

If content is indexed but getting no views:

**Tag optimization:**
- Replace vague tags with specific search queries
- Add more natural language phrases
- Include trending topics (when relevant)

**Quality improvements:**
- Increase resolution (720p+ ideal)
- Ensure smooth looping
- Optimize file size (<3MB)

**Engagement signals:**
- Share Tenor links to drive initial views
- Use in messaging apps to boost clicks
- Cross-promote from other platforms

## Best Practices for Success

### Content Quality

**Technical specs:**
- Minimum: 320x320px (480x480px+ recommended)
- Maximum file size: 5MB (under 3MB ideal)
- Duration: 1-8 seconds (2-5 seconds optimal)
- Format: MP4 preferred (better compression)

**Visual quality:**
- High-quality source material
- Smooth loops (seamless transitions)
- Clear subject/action
- Good compression balance (quality vs. size)

### Mobile-First Optimization

Tenor is primarily mobile-focused:

**Design for small screens:**
- Clear focal point
- Simple compositions
- Readable text (if any)
- High contrast

**Mobile search behavior:**
- Short queries ("lol", "omg", "yay")
- Emotion-based searches
- Quick browsing
- Immediate relevance

### Upload Timing

**Tenor processes 24/7** but consider:
- Peak usage: Evenings/weekends (more competition)
- Off-peak uploads may index faster
- Trending events: Upload early to capture searches

### Metadata Strategy

**Description field:**
- Short sentence describing content
- Natural language
- Includes primary tags organically

**Example:**
```
Title: "Excited Celebration Dance"
Description: "Happy person celebrating with excited dance moves after good news"
Tags: yes, celebration, excited, happy dance, good news, pumped, let's go
```

## Content Categories

Tenor organizes content into categories:

**Popular categories:**
- Reactions
- Love & Romance
- Sad & Cry
- Greetings & Hello
- Thank You
- Dance & Party
- Animals
- Sports

**Strategic tagging:**
- Include category-relevant tags
- Think about browsing vs. search
- Consider featured category placement

## Tracking Performance

### Tenor Analytics

Available in Developer Portal:
- **Views** - Total impressions
- **Clicks** - User interactions
- **Shares** - Share activity
- **Search terms** - Queries that led to your content

### Success Metrics

**Good propagation indicators:**
- Searchable within 2-4 hours
- Views in first 24 hours
- Appears for multiple tag queries
- Shows in mobile keyboard suggestions

**Red flags:**
- Not indexed after 24 hours
- Zero views after 48 hours
- Doesn't appear for exact tags
- Rejection notices

## Advanced Features

### Locale/Language Support

Tenor supports international markets:
- Tag in multiple languages
- Locale-specific metadata
- Regional trending content

**GIFDistributor config:**
```
Locales: en, es, pt, ja, ko, de, fr, it
Primary: en (English)
Secondary: Add relevant locales for your content
```

### Content Collections

Organize related content:
- Group by theme/topic
- Easier discovery for users
- Better organization in dashboard
- Potential featured collection status

### API Integration

GIFDistributor uses Tenor API v2:
- Upload via `/posts` endpoint
- Status checks via `/posts/{id}`
- Analytics via `/analytics`

**Rate limits:**
- Standard: 1000 requests/day
- Partner: Custom limits

## Comparison: Tenor vs. GIPHY

| Feature | Tenor | GIPHY |
|---------|-------|-------|
| **Review speed** | Automated (30 min) | Manual (24-48 hrs) |
| **Indexing** | 2-4 hours | 24-48 hours |
| **Tag limit** | 30 tags | 20 tags |
| **Mobile focus** | High (Gboard, etc.) | Moderate |
| **Discoverability** | Google ecosystem | Standalone platform |
| **Engagement** | Click-based | View + share-based |

**Strategy:** Upload to both for maximum reach.

## Resources

- **Tenor Developer Portal**: https://developers.google.com/tenor
- **Tenor API Docs**: https://tenor.com/gifapi/documentation
- **Tenor Guidelines**: https://tenor.com/legal-terms
- **GIFDistributor Support**: See [overview guide](./propagation-guide-overview.md)

## FAQ

**Q: Does Tenor content appear in Google Image Search?**
A: Yes, usually within 6-24 hours of Tenor indexing.

**Q: Can I update tags after upload?**
A: Limited editing via Tenor dashboard. May require re-upload for major changes.

**Q: Why is Tenor faster than GIPHY?**
A: Automated review vs. manual review. Tenor uses AI for moderation.

**Q: Which platform gets more views?**
A: Depends on content type. Tenor gets mobile keyboard traffic; GIPHY gets direct search.

**Q: Can I schedule uploads?**
A: Yes, via GIFDistributor's scheduling feature.

---

**Last Updated:** 2025-10-04
