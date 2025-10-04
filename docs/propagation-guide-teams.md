# Microsoft Teams Propagation Guide

## Overview

Microsoft Teams GIF sharing is **tenant-specific** with **immediate propagation** via message extensions and adaptive cards. Content is visible instantly within your organization.

## Propagation Timeline

```
Upload → Teams Extension → Message Post → Adaptive Card Render
  ↓            ↓                 ↓                ↓
Instant   Search/Select    Channel/Chat      VISIBLE
```

**Expected time to visibility:** Immediate (no review process)

## Distribution Model

### Tenant-Scoped Content

**Key characteristics:**
- Content visible only within Microsoft 365 tenant
- No cross-organization discovery
- Respects Teams/channel permissions
- Immediate availability

**Visibility scope:**
```
Public teams     → All org members (who can access team)
Private teams    → Team members only
Channels         → Channel members only
1:1 Chats        → Conversation participants only
Group chats      → Chat members only
```

## Sharing Methods

### Method 1: Message Extension

**Teams Messaging Extension (Primary):**
```
User clicks compose extension → Searches GIFDistributor → Selects GIF → Posts as adaptive card
```

**How it works:**
1. Click "..." in Teams message box
2. Select "GIFDistributor" extension
3. Search your GIF library
4. Preview and select
5. GIF posts as rich adaptive card

**Features:**
- Inline search within Teams
- Preview before posting
- Metadata displayed (title, tags, duration)
- Playable directly in feed

### Method 2: Link Unfurling

**Automatic preview from URL:**
```
User posts: https://gifdistributor.example/g/abc123
Teams unfurls: [Adaptive card with playback controls]
```

**Unfurl card includes:**
- GIF preview/playback
- Title and description
- Author information
- View/share actions
- Quick reactions

**Enable unfurling:**
```
Teams Admin Center → Apps → GIFDistributor → Link unfurling: ON
```

### Method 3: Bot Commands

**GIFDistributor Teams Bot:**
```
@GIFDistributor search celebration    → Search GIF library
@GIFDistributor recent                → Recent uploads
@GIFDistributor share [id]            → Share specific GIF
@GIFDistributor upload                → Upload from Teams
```

**Installation:**
```
Teams → Apps → Search "GIFDistributor" → Add → Authorize
```

**Bot capabilities:**
- 1:1 chat with bot
- Mention in channels (@GIFDistributor)
- Proactive notifications (upload complete)

### Method 4: Tab Integration

**GIFDistributor Tab for Teams:**
```
Add as channel tab:
  - Shows full GIF library
  - In-Teams management
  - Quick sharing to channel
  - Team-specific collections
```

**Setup:**
```
Channel → + (Add tab) → GIFDistributor → Configure
```

## Adaptive Card Format

### Card Structure

**GIF Adaptive Card:**
```json
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    {
      "type": "TextBlock",
      "text": "Happy Celebration Dance",
      "weight": "bolder",
      "size": "large"
    },
    {
      "type": "Media",
      "poster": "https://cdn.gifdistributor.example/abc123-thumb.jpg",
      "sources": [
        {
          "mimeType": "video/mp4",
          "url": "https://cdn.gifdistributor.example/abc123.mp4"
        }
      ]
    },
    {
      "type": "FactSet",
      "facts": [
        {"title": "Duration", "value": "3.2s"},
        {"title": "Tags", "value": "celebration, happy, dance"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "View Full Size",
      "url": "https://gifdistributor.example/g/abc123"
    }
  ]
}
```

**Features:**
- Native Teams playback
- Responsive design (desktop/mobile)
- Action buttons
- Metadata display

### Card Customization

**Brand your cards:**
```
Settings → Teams Integration → Card Appearance
  - Logo/watermark
  - Color scheme
  - Footer text
  - Action buttons
```

## Content Optimization for Teams

### Technical Requirements

**Recommended specs:**
- **Format:** MP4 (preferred over GIF in Teams)
- **Size:** Under 5MB (faster loading)
- **Resolution:** 720p (1280x720) or 1080p
- **Duration:** 2-5 seconds (adaptive card optimal)
- **Codec:** H.264 (wide compatibility)

**Teams rendering:**
- Inline playback in cards
- Auto-play (respects user settings)
- Mobile-optimized
- Supports captions/subtitles

### Visual Design

**Teams interface:**
- Light and dark themes
- Desktop and mobile apps
- Web client compatibility
- Accessibility features

**Design considerations:**
- Test on both themes
- Clear visual hierarchy
- Readable at various sizes
- Professional appearance (business context)

### Accessibility

**Teams accessibility features:**
- Screen reader support
- Keyboard navigation
- High contrast mode
- Caption support

**GIFDistributor accessibility:**
```
Upload settings:
  ✓ Alt text (required)
  ✓ Caption file (optional)
  ✓ Descriptive title
  ✓ Transcription (for audio)
```

## Message Extension Features

### Search-Based Extension

**Query your library:**
```
Type in search box:
  "celebration" → Shows matching GIFs
  "#happy" → Filter by tag
  "recent:7d" → Last 7 days
```

**Search features:**
- Real-time results
- Thumbnail previews
- Metadata filtering
- Favorites quick access

### Action-Based Extension

**Quick actions:**
- Upload from Teams
- Share to channel
- Create collection
- Generate share link

**Context menu:**
```
Right-click message → GIFDistributor → "Find similar GIF"
```

## Organization Setup

### For Teams Admins

**1. Deploy GIFDistributor App**
```
Teams Admin Center → Manage apps → Upload/Find GIFDistributor
  → Set org-wide availability
  → Configure policies
  → Set permissions
```

**2. App Policies**
```
Setup policies:
  ✓ Allow in all teams
  ✓ Allow in chats
  ✓ Pin by default (optional)
  ✓ Pre-install for users (optional)
```

**3. Permission Policies**
```
Settings:
  - Who can install: All users / Admins only
  - Data access: User profile, Teams membership
  - External content: Allowed domains
  - Compliance: Data residency, retention
```

**4. Compliance & Security**
```
DLP policies:
  - Block sensitive data in GIFs
  - Audit GIF sharing
  - Retention policies
  - eDiscovery support
```

### For End Users

**1. Install Extension**
```
Teams → Apps → Search "GIFDistributor" → Add
```

**2. Authenticate**
```
First use:
  → Sign in to GIFDistributor
  → Authorize Teams integration
  → Link account
```

**3. Pin for Quick Access**
```
Teams message box → ... → Right-click GIFDistributor → Pin
```

## Use Cases

### Internal Communications

**Team engagement:**
- Celebrate milestones
- Acknowledge good work
- Build team culture
- Break the ice in meetings

**Examples:**
```
Project milestone reached:
  → Share celebration GIF in team channel

New team member:
  → Welcome GIF in chat

Friday afternoon:
  → Weekend anticipation GIF
```

### Training & Onboarding

**Visual instructions:**
- Process demonstrations
- Feature highlights
- Step-by-step guides
- Quick tips

**Example workflow:**
```
New employee onboarding:
  1. Welcome message with GIF
  2. Tutorial GIFs for common tasks
  3. Resource links with visual previews
  4. Culture/value GIFs
```

### Sales & Marketing

**Internal enablement:**
- Product launch announcements
- Sales wins celebrations
- Campaign kick-offs
- Motivational content

**External (with caution):**
- Customer presentations (professional GIFs only)
- Proposal materials
- Follow-up emails (via Outlook integration)

### Customer Support

**Internal team communication:**
- Acknowledge support tickets
- Celebrate resolutions
- Team morale boosters

**Not recommended for:**
- Direct customer communication (unprofessional)
- Formal support channels

## Tracking and Analytics

### Teams-Specific Metrics

**GIFDistributor dashboard:**
```
Teams Engagement:
  ├─ Shares: 89 (across 12 teams)
  ├─ Views: 1,456
  ├─ Reactions: 234 (👍 89, ❤️ 67, 😂 45)
  ├─ Re-shares: 23 (forwarded)
  └─ Saved: 34 (bookmarked)
```

**Per-team analytics:**
- Which teams engage most
- Popular content by department
- Peak usage times
- Adoption rates

### Compliance Reporting

**For IT admins:**
- Usage audit logs
- Data access reports
- User activity tracking
- Policy violation alerts

**Export reports:**
```
Teams Admin Center → Analytics → Custom reports
  → GIFDistributor usage
  → Export to CSV/Excel
```

## Troubleshooting

### Extension Not Appearing

**Problem:** Can't find GIFDistributor in message extensions

**Solutions:**
1. **Check app installation:**
   - Teams → Apps → Search "GIFDistributor"
   - Click "Add" if not installed

2. **Verify org policy:**
   - Admin may have blocked app
   - Contact IT administrator

3. **Clear cache:**
   - Teams → Settings → Clear cache
   - Restart Teams

### Link Not Unfurling

**Problem:** GIFDistributor links don't show preview

**Solutions:**
1. **Enable link previews:**
   - Teams Settings → Privacy → Link previews: ON

2. **Check app permissions:**
   - App must have link unfurling capability
   - Admin must approve domain

3. **Verify URL format:**
   - Must be recognized GIFDistributor domain
   - HTTPS required

### Playback Issues

**Problem:** GIF won't play in adaptive card

**Causes:**
- Unsupported format/codec
- File too large
- Network issues
- Client compatibility

**Fixes:**
1. **Use MP4 format:**
   - Better compatibility than GIF
   - Smaller file size
   - Higher quality

2. **Optimize file:**
   - GIFDistributor auto-optimization for Teams
   - Target <5MB
   - H.264 codec

3. **Check network:**
   - Corporate firewall may block CDN
   - Test on different network

### Slow Loading

**Problem:** Cards load slowly

**Optimization:**
```
GIFDistributor settings:
  → Teams Integration
  → Performance mode: ON
  → Preload thumbnails
  → Regional CDN selection
```

**Best practices:**
- Use Teams-optimized format (MP4)
- Enable caching
- Choose nearby CDN region

## Best Practices

### Professional Context

**Appropriate usage in business:**
- Keep content professional
- Avoid controversial topics
- Respect cultural differences
- Consider international audience

**When to use GIFs:**
✅ Team celebrations
✅ Light-hearted acknowledgments
✅ Internal communications
✅ Breaking up long text

**When NOT to use GIFs:**
❌ Formal client communications
❌ Legal/compliance discussions
❌ Crisis communications
❌ Performance reviews (usually)

### Governance

**Establish guidelines:**
```
Team GIF Policy:
  1. Professional content only
  2. Respect company values
  3. No offensive material
  4. Consider accessibility
  5. Don't overuse (spam)
```

**Content approval (optional):**
- Review before org-wide sharing
- Department-specific collections
- Approved template library

### Organization

**Team-specific collections:**
```
Sales Team:
  - wins-celebration
  - quota-achievement
  - prospecting-motivation

Engineering:
  - deployment-success
  - bug-squashed
  - code-review-approved
```

**Naming conventions:**
```
Format: [department]-[purpose]-[emotion/action]

Examples:
  - sales-win-celebration
  - support-ticket-resolved
  - hr-welcome-new-hire
```

## Advanced Integration

### Power Automate

**Automate GIF workflows:**
```
Flow example:
  Trigger: New Teams channel created
  Action: Post welcome GIF
  Data: Link to resources
```

**Use cases:**
- Auto-celebrate milestones
- Scheduled motivational GIFs
- Event-triggered shares
- Cross-platform posting

### Outlook Integration

**Share GIFs via email:**
```
Outlook add-in:
  - Search GIFDistributor library
  - Insert in email as image
  - Or share as link (recipient sees adaptive card)
```

**Professional email usage:**
- Internal emails only (usually)
- Appropriate for company culture
- Not for formal communications

### SharePoint Integration

**Embed in SharePoint:**
```
SharePoint page:
  → Add GIFDistributor web part
  → Show curated collection
  → Team/department gallery
```

## Enterprise Features

### Multi-Geo Support

**Microsoft 365 Multi-Geo:**
- Content stored in tenant region
- Respects data residency
- Compliance with local regulations

**Configuration:**
```
GIFDistributor Enterprise settings:
  → Data residency: [Select region]
  → Geo-specific CDN
  → Local compliance rules
```

### Advanced Security

**DLP integration:**
- Scan GIFs for sensitive data
- Block uploads with violations
- Audit trail for compliance
- Retention policies

**Conditional access:**
- Restrict to managed devices
- MFA requirements
- Location-based restrictions

## Resources

- **Microsoft Teams Developer Portal**: https://dev.teams.microsoft.com
- **Adaptive Cards Designer**: https://adaptivecards.io/designer
- **Teams Admin Center**: https://admin.teams.microsoft.com
- **GIFDistributor Teams Docs**: [Extension details](./teams-extension.md)
- **Support**: [Main guide](./propagation-guide-overview.md)

## FAQ

**Q: Can external users (guests) see shared GIFs?**
A: Yes, if they have access to the team/channel where GIF is shared.

**Q: Are GIFs stored in Microsoft 365 or externally?**
A: Stored on GIFDistributor CDN. Only adaptive card metadata stored in Teams.

**Q: Can I use GIFs in Teams meetings?**
A: Yes, share in meeting chat. Not recommended to interrupt presentations.

**Q: How do I remove a GIF from Teams?**
A: Delete the message containing it. Original remains on GIFDistributor.

**Q: Can I restrict who can share GIFs?**
A: Yes, via Teams app permission policies (admin control).

**Q: Is there a limit to GIF sharing?**
A: No hard limit, but respect team norms and avoid spam.

**Q: Can I schedule GIF posts in Teams?**
A: Yes, via Power Automate or GIFDistributor scheduling.

---

**Last Updated:** 2025-10-04
