# Discord Propagation Guide

## Overview

Discord GIF sharing works differently from GIPHY/Tenor - content is **immediately available** but **limited to specific servers** unless integrated with Tenor's Discord partnership.

## Propagation Timeline

```
Upload → Discord Bot/Extension → Server Channel → Immediate Display
  ↓              ↓                      ↓                ↓
Instant    Auto-post/Share         Embed renders    VISIBLE
```

**Expected time to visibility:** Immediate (no review process)

## Distribution Models

### 1. Direct Sharing (Immediate)

**Server-specific distribution:**
- Upload via GIFDistributor
- Share link to Discord channel
- Discord auto-embeds the GIF
- Visible to all channel members

**Benefits:**
- Instant visibility
- No review/approval needed
- Full control over distribution
- Works in any server

### 2. Bot Integration (Automated)

**Automated posting via Discord bot:**
- GIFDistributor bot posts to configured channels
- Scheduled or instant posting
- Multi-server distribution
- Webhook-based delivery

**Setup:**
```
1. Invite GIFDistributor bot to server
2. Configure posting channels
3. Set posting permissions
4. Enable auto-posting in GIFDistributor dashboard
```

### 3. Discord-Tenor Integration

**Searchable GIFs via Tenor:**
- Upload to Tenor via GIFDistributor
- Content becomes searchable in Discord's GIF picker
- Users across all Discord servers can find it
- Propagation follows [Tenor timeline](./propagation-guide-tenor.md)

**Access:**
- Click GIF button in Discord message box
- Search by tags
- Your content appears if indexed by Tenor

## Sharing Methods

### Method 1: Direct Link Sharing

**Share GIFDistributor-hosted GIF:**
```
User uploads → GIFDistributor generates CDN link → Share in Discord
Example: https://cdn.gifdistributor.example/abc123.gif
```

**Discord auto-embed:**
- Recognizes media URLs
- Displays inline preview
- Supports GIF, MP4, WebM
- Click to view full size

**Best practices:**
- Use CDN URLs (fast loading)
- Keep file size under 8MB (Discord limit)
- Optimize for mobile viewing

### Method 2: Bot Commands

**Using GIFDistributor bot:**
```
/gif search [query]     → Search your uploaded GIFs
/gif recent            → Show recent uploads
/gif post [id]         → Post specific GIF
/gif random [tag]      → Random GIF by tag
```

**Permissions required:**
- Bot must be invited to server
- "Embed Links" permission
- "Send Messages" permission
- "Use External Emojis" (if using custom reactions)

### Method 3: Webhook Auto-Posting

**Automated distribution:**
```yaml
Configuration:
  - Trigger: On upload completion
  - Target: Specific Discord channels
  - Format: Auto-embed with metadata
  - Schedule: Immediate or scheduled
```

**Use cases:**
- Content creator showcasing new work
- Community sharing curated GIFs
- Automated announcements
- Cross-server distribution

## Server Setup

### For Server Administrators

**1. Invite GIFDistributor Bot**
```
Dashboard → Discord Integration → Generate Invite Link → Authorize
```

**2. Configure Channels**
```
/gifdist setup
  ├─ Select posting channel
  ├─ Set permissions
  ├─ Configure auto-posting rules
  └─ Test configuration
```

**3. Set Posting Rules**
- Who can trigger bot posts
- Which channels allow auto-posting
- Content filtering (tags, ratings)
- Rate limiting (to avoid spam)

### For Content Creators

**1. Link Discord Account**
```
GIFDistributor Dashboard → Integrations → Discord → Authorize
```

**2. Configure Auto-Posting**
```
Settings:
  ✓ Auto-post to my server
  ✓ Post on upload completion
  ✓ Include metadata (title, tags)
  ✓ Notify subscribers
```

**3. Manage Distribution**
- Select target servers/channels
- Set posting frequency
- Schedule posts
- Track engagement

## Content Optimization for Discord

### Technical Requirements

**File specifications:**
- **Maximum size:** 8MB (free users), 50MB (Nitro)
- **Formats:** GIF, MP4, WebM
- **Resolution:** Any (1280x720 recommended)
- **Duration:** Any (2-5 seconds optimal for GIFs)

**Optimization tips:**
- MP4 has better compression than GIF
- Use WebM for even smaller file sizes
- Discord auto-converts large GIFs to MP4

### Visual Design

**Discord dark mode:**
- Most users use dark mode
- Test GIFs on dark background
- Avoid transparent edges (look broken)
- Use good contrast

**Mobile viewing:**
- 40%+ Discord users on mobile
- Keep important elements centered
- Readable at small sizes
- Quick load times

### Embed Behavior

**Discord embed features:**
- Auto-plays in feed (muted)
- Click to expand
- Right-click to save
- Supports captions/descriptions

**Metadata in embeds:**
```
Embed includes:
  - Thumbnail preview
  - Title (if provided)
  - Description
  - File size indicator
  - Source link
```

## Bot Features

### Search Functionality

**Find uploaded content:**
```
/gif search "celebration"
  → Returns matching GIFs
  → Click to post to channel
  → Preview before posting
```

**Advanced search:**
```
/gif search tag:happy type:reaction recent:7d
  → Filter by tags
  → Filter by content type
  → Time range filtering
```

### Collections

**Organize GIFs:**
- Create collections by theme
- Share entire collections
- Quick access to favorites
- Public or private collections

### Analytics

**Track Discord engagement:**
- Views per server
- Most popular GIFs
- Peak posting times
- User engagement rates

## Propagation Tracking

### Real-Time Status

**GIFDistributor dashboard shows:**
```
Discord Distribution:
  ├─ Posted to: 5 servers, 12 channels
  ├─ Total views: 1,234
  ├─ Reactions: 89
  └─ Shares: 23 (re-posted to other channels)
```

### Engagement Metrics

**Per-server analytics:**
- Which servers engage most
- Peak activity times
- Popular content types
- User feedback (reactions)

## Troubleshooting

### GIF Not Embedding

**Problem:** Link doesn't auto-embed

**Solutions:**
1. **Check URL format:** Must be direct media link (.gif, .mp4)
2. **File size:** Must be under Discord limits (8MB/50MB)
3. **Permissions:** Channel must allow embeds
4. **HTTPS required:** Ensure CDN uses HTTPS

**Test:**
```
Working: https://cdn.example.com/abc.gif
Not working: https://example.com/view?id=abc
```

### Bot Not Responding

**Problem:** Bot commands don't work

**Checklist:**
- [ ] Bot is online (check status)
- [ ] Bot has proper permissions
- [ ] Commands used in allowed channels
- [ ] Bot isn't rate-limited

**Reset:**
```
/gifdist reset     → Reconnect bot
/gifdist status    → Check configuration
```

### File Size Issues

**Problem:** "File too large" error

**Solutions:**
1. **Compress GIF:** Use GIFDistributor's optimizer
2. **Convert to MP4:** Better compression
3. **Reduce dimensions:** Lower resolution
4. **Shorten duration:** Trim unnecessary frames
5. **Get Nitro:** 50MB limit instead of 8MB

**GIFDistributor auto-optimization:**
```
Settings → Discord Integration → Auto-optimize for Discord
  - Targets 7.5MB for free users
  - Targets 45MB for Nitro
  - MP4 conversion enabled
  - Quality preservation mode
```

### Slow Loading

**Problem:** GIF loads slowly in Discord

**Causes:**
- Large file size
- Slow CDN response
- Server/network issues
- Discord CDN caching

**Improvements:**
- Use GIFDistributor CDN (optimized for Discord)
- Enable compression
- Reduce file size
- Wait for Discord to cache (faster on repeat views)

## Best Practices

### Content Strategy

**Know your audience:**
- Different servers have different cultures
- Tailor content to community interests
- Respect server rules and tone

**Posting frequency:**
- Don't spam channels
- Space out posts (avoid rate limits)
- Consider time zones (when members are active)
- Use scheduled posting for consistency

### Community Building

**Engage with community:**
- Respond to reactions/feedback
- Take requests for new GIFs
- Create server-specific content
- Host GIF contests or events

**Collections for communities:**
- Create "server meme" collections
- Inside jokes or running gags
- Event-specific GIFs (birthdays, anniversaries)
- Role-specific reactions (admin, moderator, etc.)

### Cross-Server Distribution

**Multi-server strategy:**
- Customize posts per server culture
- Don't blast identical content everywhere
- Track which servers engage most
- Focus efforts on active communities

## Advanced Integration

### Custom Bot (Enterprise)

Build custom integration using GIFDistributor API:
- Custom commands
- Server-specific features
- Advanced analytics
- White-label experience

**Documentation:** See [API docs](../api/discord-integration.md)

### Slash Commands (Coming Soon)

Native Discord slash commands:
```
/gifdist upload    → Upload directly from Discord
/gifdist search    → Search your library
/gifdist share     → Share with other servers
```

### Activity Integration

Discord Rich Presence:
- "Creating GIFs"
- "Uploading to Discord"
- Link to your profile/collection

## Tenor-Discord Integration

### Searchable GIFs

**How it works:**
1. Upload to Tenor via GIFDistributor
2. Tenor indexes your content
3. Discord GIF picker searches Tenor
4. Your GIFs appear in search results

**Timeline:**
- Upload → Tenor (see [Tenor guide](./propagation-guide-tenor.md))
- Tenor → Discord GIF picker: Usually same-day
- Searchability across all Discord servers

**Optimization for Discord search:**
- Use Discord-relevant tags (reactions, memes)
- Mobile-optimized (most Discord users on mobile)
- Common search queries ("yes", "no", "lol", etc.)

### Benefits

**Server-specific vs. Global:**
| Method | Visibility | Speed | Control |
|--------|-----------|-------|---------|
| Direct share | Your servers only | Instant | Full |
| Tenor integration | All Discord users | Hours | Limited |

**Best strategy:** Use both methods
- Direct share for immediate community engagement
- Tenor integration for discoverability

## Resources

- **Discord Developer Portal**: https://discord.com/developers
- **GIFDistributor Bot Docs**: [Bot documentation](./discord-bot.md)
- **Discord API Docs**: https://discord.com/developers/docs
- **Support**: [Main guide](./propagation-guide-overview.md)

## FAQ

**Q: Do I need Discord Nitro to share GIFs?**
A: No, but Nitro increases file size limit from 8MB to 50MB.

**Q: Can I monetize GIFs on Discord?**
A: Only through server-specific arrangements. No built-in monetization.

**Q: Will my GIFs be searchable across all Discord servers?**
A: Only if indexed by Tenor. Direct shares are server-specific.

**Q: Can I track who views my GIFs?**
A: Only aggregate analytics. No individual user tracking.

**Q: How do I remove a GIF from Discord?**
A: Delete the message containing it. For Tenor-indexed content, see [Tenor guide](./propagation-guide-tenor.md).

---

**Last Updated:** 2025-10-04
