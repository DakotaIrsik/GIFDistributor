# Slack Propagation Guide

## Overview

Slack GIF sharing is **workspace-specific** with **immediate propagation**. Content shared to Slack is visible instantly to workspace members, with no review process.

## Propagation Timeline

```
Upload → Slack Share → Message Post → Immediate Display
  ↓          ↓             ↓               ↓
Instant  API call     Channel post      VISIBLE
```

**Expected time to visibility:** Immediate (no review or indexing)

## Distribution Model

### Workspace-Scoped Content

**Key characteristics:**
- Content is visible only within the workspace where it's shared
- No cross-workspace search or discovery
- Private by default (based on channel permissions)
- Immediate availability (no propagation delay)

**Privacy levels:**
```
Public channels   → Visible to all workspace members
Private channels  → Visible to channel members only
DMs              → Visible to conversation participants only
```

## Sharing Methods

### Method 1: Link Unfurling

**Automatic embed from URL:**
```
User posts: https://cdn.gifdistributor.example/abc123.gif
Slack unfurls: [Rich preview with thumbnail, metadata, playback]
```

**How it works:**
1. User shares GIFDistributor URL in message
2. Slack detects media link
3. Requests unfurl metadata from GIFDistributor API
4. Displays rich embed with preview

**Unfurl metadata:**
```json
{
  "title": "Happy Celebration Dance",
  "image_url": "https://cdn.gifdistributor.example/abc123.gif",
  "author_name": "YourUsername",
  "author_link": "https://gifdistributor.example/u/username",
  "fields": [
    {"title": "Duration", "value": "3.2s"},
    {"title": "Size", "value": "2.1 MB"}
  ]
}
```

**Enable unfurling:**
```
GIFDistributor Dashboard → Integrations → Slack → Enable Link Unfurling
```

### Method 2: Slack App Integration

**GIFDistributor Slack App features:**
- `/gifdist search [query]` - Search your GIF library
- `/gifdist recent` - Show recent uploads
- `/gifdist upload` - Upload directly from Slack
- `/gifdist share [id]` - Share specific GIF to channel

**Installation:**
```
1. Visit Slack App Directory
2. Search "GIFDistributor"
3. Click "Add to Slack"
4. Authorize workspace access
5. Link your GIFDistributor account
```

**Permissions required:**
- `chat:write` - Post messages
- `files:write` - Upload files
- `links:read` - Unfurl links
- `commands` - Slash commands

### Method 3: Workflow Builder

**Automated sharing via Slack Workflows:**
```
Trigger: New GIF uploaded to GIFDistributor
Action: Post to #announcements channel
Message: "New GIF: {{title}} - {{url}}"
```

**Setup:**
1. Slack Workspace → Workflow Builder
2. Create new workflow
3. Add webhook trigger
4. Configure GIFDistributor webhook in dashboard
5. Design message template
6. Activate workflow

### Method 4: Direct File Upload

**Upload GIF file to Slack:**
```
GIFDistributor → Export GIF → Slack file upload → Channel/DM
```

**Considerations:**
- Counts toward workspace file storage
- Slower than CDN-hosted links
- Useful for offline/archival purposes

**File limits:**
- Free workspaces: 5GB total storage
- Pro/Business+: 10GB/20GB per member

## Content Optimization for Slack

### Technical Requirements

**Recommended specs:**
- **Format:** GIF or MP4
- **Size:** Under 5MB (faster loading)
- **Resolution:** 480-720px width (Slack auto-scales)
- **Duration:** 2-5 seconds (short loops work best)

**Slack rendering:**
- Auto-plays GIFs in feed
- Click to pause/resume
- Hover to see controls
- Supports inline playback

### Visual Design

**Slack interface considerations:**
- Light and dark modes
- Desktop and mobile apps
- Inline message display
- Thread view compatibility

**Design tips:**
- Test on both light/dark backgrounds
- Keep important content centered
- Readable at 480px width
- Clear visual focus

### File Size Optimization

**Why size matters in Slack:**
- Faster load times
- Better mobile experience
- Reduced data usage
- Improved engagement

**GIFDistributor optimization:**
```
Settings → Slack Integration → Auto-optimize
  - Target size: 3-5MB
  - Quality: High (minimal loss)
  - Format: Auto-select (GIF or MP4)
  - Mobile preview generation
```

## App Features

### Slash Commands

**Search your library:**
```
/gifdist search "celebration"
  → Shows matching GIFs
  → Click to post to channel
  → Preview before sharing (ephemeral message)
```

**Recent uploads:**
```
/gifdist recent
  → Last 10 uploads
  → Quick-share interface
  → Filter by tags
```

**Direct upload:**
```
/gifdist upload
  → Opens upload dialog
  → Add title/tags
  → Choose privacy (public/private)
  → Posts to channel on completion
```

### Interactive Messages

**Rich GIF cards:**
```
┌─────────────────────────────────┐
│ 🎬 Happy Celebration Dance      │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ [GIF preview]                   │
│                                 │
│ 👀 Views: 234  💬 Uses: 45      │
│ 🏷️ Tags: celebration, happy     │
│                                 │
│ [Share to Channel] [Save] [⋯]  │
└─────────────────────────────────┘
```

**Interactions:**
- Share: Post to current channel
- Save: Add to favorites
- More: View details, copy link, report

### Shortcuts

**Message shortcuts:**
- Right-click message → "Find similar GIF"
- Hover over GIF → "Save to GIFDistributor"

**Global shortcuts:**
- `/` menu → "Search GIFs"
- Compose box → GIF button (if enabled)

## Workspace Setup

### For Workspace Admins

**1. Install GIFDistributor App**
```
Admin Dashboard → Apps → Browse App Directory → GIFDistributor → Install
```

**2. Configure Permissions**
```
Settings:
  ✓ Allow in public channels
  ✓ Allow in private channels
  ✓ Allow in DMs
  ⚠ Review app permissions
```

**3. Set Policies**
```
Workspace Policies:
  - Who can install apps: Admins only / Everyone
  - File upload permissions: All members
  - External link unfurling: Enabled
  - App usage analytics: Enabled
```

### For Individual Users

**1. Connect Account**
```
/gifdist connect
  → Opens authentication flow
  → Authorize GIFDistributor access
  → Links Slack user to GIFDistributor account
```

**2. Personal Preferences**
```
/gifdist settings
  - Default privacy for uploads
  - Auto-share on upload
  - Notification preferences
  - Favorite collections
```

## Use Cases

### Team Communication

**Reactions and responses:**
- Quick acknowledgments ("thumbs up", "great job")
- Emotional reactions ("surprised", "laughing")
- Team inside jokes (custom GIFs)

**Engagement boosting:**
- More expressive than emoji
- Adds personality to messages
- Strengthens team culture

### Content Creators

**Showcasing work:**
```
Workflow:
1. Create GIF
2. Upload to GIFDistributor
3. Auto-post to #portfolio channel
4. Team provides feedback
5. Publish to public platforms
```

**Collaboration:**
- Share drafts for review
- Get quick feedback
- Iterate on designs
- Archive final versions

### Customer Support

**Pre-built responses:**
- Common questions answered with GIFs
- Visual instructions
- Friendly acknowledgments
- Escalation procedures

**Efficiency:**
```
Instead of typing:
"Thanks for contacting us! We're looking into this and will get back to you within 24 hours."

Share pre-made GIF:
/gifdist share support-acknowledgment-24h
```

## Tracking and Analytics

### Slack-Specific Metrics

**GIFDistributor dashboard shows:**
```
Slack Engagement:
  ├─ Shares: 123 (across 5 workspaces)
  ├─ Views: 1,890
  ├─ Reactions: 234 (👍 89, ❤️ 67, 😂 45, ⋯)
  ├─ Re-shares: 34 (forwarded to other channels)
  └─ Saved: 56 (added to favorites)
```

**Per-workspace analytics:**
- Which workspaces engage most
- Popular content types
- Peak usage times
- User adoption rates

### Engagement Insights

**What to track:**
1. **Share-to-view ratio** - How many people view after share
2. **Reaction rate** - Percentage of views that get reactions
3. **Re-share rate** - How often content is forwarded
4. **Time-to-first-view** - How quickly content gets attention

**Optimization:**
- Best posting times
- Most engaging content types
- Optimal GIF length
- Tag effectiveness

## Troubleshooting

### Link Not Unfurling

**Problem:** GIFDistributor links don't show preview

**Solutions:**
1. **Check unfurling settings:**
   - Slack Workspace → Preferences → Messages & Media
   - Enable "Show website previews"

2. **Verify app installation:**
   - GIFDistributor app must be installed
   - App needs `links:read` permission

3. **Domain verification:**
   - GIFDistributor domain must be verified
   - Check whitelist in Slack admin settings

**Manual unfurl:**
```
If automatic unfurling fails, use slash command:
/gifdist share [url]
```

### Slash Commands Not Working

**Problem:** `/gifdist` commands return error

**Checklist:**
- [ ] App is installed in workspace
- [ ] User has linked GIFDistributor account (`/gifdist connect`)
- [ ] App has required permissions
- [ ] Workspace allows slash commands

**Debug:**
```
/gifdist status     → Check connection
/gifdist help       → List available commands
```

### Slow Loading

**Problem:** GIFs load slowly in Slack

**Causes:**
- Large file size
- Network issues
- CDN problems
- Workspace region mismatch

**Fixes:**
- Use GIFDistributor's Slack optimization
- Reduce file size (target <3MB)
- Choose regional CDN closest to workspace
- Convert GIF to MP4 for better compression

### File Upload Issues

**Problem:** "Upload failed" error

**Solutions:**
1. **Check file size:**
   - Must be under workspace limit
   - Free: 5GB total, Pro/Business+: 10-20GB per member

2. **Verify permissions:**
   - User has file upload permission
   - Channel allows file uploads

3. **Format compatibility:**
   - Slack supports GIF, MP4, WebM
   - Use standard formats (avoid exotic codecs)

**Workaround:**
```
Instead of direct upload, share CDN link:
1. Upload to GIFDistributor
2. Copy CDN URL
3. Paste in Slack (auto-unfurls)
```

## Best Practices

### Content Strategy

**Know your workspace culture:**
- Professional vs. casual tone
- Frequency expectations
- Channel-specific norms

**Appropriate usage:**
- Don't spam channels
- Keep content relevant
- Respect channel topics
- Use threads for off-topic GIFs

### Organization

**Collections for different contexts:**
- Reactions (happy, sad, confused)
- Team-specific (inside jokes)
- Project-related (milestones, status)
- Support (help responses)

**Naming conventions:**
```
Good:
- "team-celebration-milestone"
- "support-acknowledged-24h"
- "reaction-thumbs-up-simple"

Bad:
- "gif1", "gif2", "gif3"
- "untitled-123"
```

### Collaboration

**Team libraries:**
- Shared GIF collections
- Team-curated content
- Consistent branding
- Easy access for all members

**Governance:**
- Who can upload
- Approval processes (if needed)
- Content guidelines
- Archive/deletion policies

## Advanced Features

### Custom Integration

**Build custom Slack apps using GIFDistributor API:**
- Custom commands
- Automated workflows
- Department-specific features
- White-label experience

**Example use case:**
```
Marketing team custom app:
- /campaign upload [gif]
- /campaign schedule [date] [channel]
- /campaign analytics
```

### Webhook Automation

**Trigger Slack actions from GIFDistributor:**
```
Event: New GIF uploaded
  → Post to #content-team
  → Notify @reviewer
  → Add to approval queue
```

**Trigger GIFDistributor from Slack:**
```
Event: Message with file in #gif-submissions
  → Upload to GIFDistributor
  → Tag automatically
  → Post confirmation
```

### Enterprise Features

**For Enterprise Grid:**
- Cross-workspace sharing
- Centralized GIF library
- Org-wide analytics
- Compliance controls

## External Upload Path

### Sharing from Outside Workspace

**Scenario:** User wants to share GIF but isn't workspace member

**Solution: External share link**
```
1. GIFDistributor generates public share link
2. External user visits link
3. Clicks "Share to Slack"
4. Authenticates with Slack
5. Chooses workspace/channel
6. GIF posted to Slack
```

**Privacy controls:**
- Restrict external shares
- Require approval
- Limit to specific workspaces
- Track external shares

## Resources

- **Slack API Documentation**: https://api.slack.com
- **GIFDistributor Slack App**: [App details](./slack-app-integration.md)
- **Slack App Directory**: https://slack.com/apps
- **Support**: [Main guide](./propagation-guide-overview.md)

## FAQ

**Q: Can I search GIFs across multiple workspaces?**
A: No, Slack GIFs are workspace-specific. Use GIFDistributor dashboard for cross-workspace management.

**Q: Are GIFs stored in Slack or externally?**
A: When shared via link, they're stored on GIFDistributor CDN. Direct uploads use Slack storage.

**Q: Can guests in my workspace see shared GIFs?**
A: Yes, if they have access to the channel where GIF is shared.

**Q: How do I remove a GIF from Slack?**
A: Delete the message containing it. For CDN-hosted GIFs, original remains on GIFDistributor.

**Q: Can I schedule GIF posts?**
A: Yes, use Slack Workflow Builder or GIFDistributor's scheduling feature.

**Q: Is there a limit to how many GIFs I can share?**
A: No limit on sharing. Storage limits apply to direct uploads.

---

**Last Updated:** 2025-10-04
