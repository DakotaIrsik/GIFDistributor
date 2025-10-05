# Discord Bot Integration (Optional)

**Issue #46: Discord bot (optional): curated channel posting**

## Overview

The Discord bot integration enables posting curated GIFs to Discord channels. This feature is **completely optional** and can be enabled by providing a Discord bot token.

## Features

- ✅ Post curated GIFs to Discord channels using bot
- ✅ Alternative webhook-based posting (no bot required)
- ✅ Rich embeds with titles, descriptions, and images
- ✅ Graceful degradation when disabled
- ✅ Status endpoint to check bot availability

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# Optional: Discord Bot Token
DISCORD_BOT_TOKEN=your-discord-bot-token-here
```

### Setting up a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token and add it to your `.env` file
5. Enable required intents:
   - `Guilds`
   - `Guild Messages`
6. Invite the bot to your server using OAuth2 URL generator:
   - Scopes: `bot`
   - Permissions: `Send Messages`, `Embed Links`

## API Endpoints

### POST /api/discord/post

Post a GIF to a Discord channel using the bot.

**Request:**
```json
{
  "channelId": "1234567890123456789",
  "title": "Awesome GIF!",
  "description": "Check out this amazing GIF",
  "imageUrl": "https://example.com/gif.gif",
  "sourceUrl": "https://example.com/source",
  "footer": "Powered by GIF Distributor"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Posted to Discord channel"
}
```

### POST /api/discord/webhook

Post a GIF using a Discord webhook (no bot required).

**Request:**
```json
{
  "webhookUrl": "https://discord.com/api/webhooks/...",
  "username": "GIF Bot",
  "embeds": [{
    "title": "New GIF",
    "image": { "url": "https://example.com/gif.gif" },
    "color": 5814783
  }]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Posted via Discord webhook"
}
```

### GET /api/discord/status

Check if the Discord bot is active.

**Response:**
```json
{
  "active": true,
  "message": "Discord bot is active"
}
```

## Usage Examples

### Using the Bot

```typescript
const response = await fetch('http://localhost:3001/api/discord/post', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    channelId: '1234567890123456789',
    title: 'Trending GIF',
    imageUrl: 'https://cdn.example.com/trending.gif',
    description: 'This GIF is trending today!',
  }),
});
```

### Using Webhooks (No Bot Required)

```typescript
const response = await fetch('http://localhost:3001/api/discord/webhook', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    webhookUrl: 'https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN',
    embeds: [{
      title: 'New Curated GIF',
      description: 'Check out this curated content',
      image: { url: 'https://cdn.example.com/gif.gif' },
      color: 5814783, // Discord blurple
    }],
  }),
});
```

## Architecture

The Discord integration consists of:

1. **Service Layer** (`services/discordBot.ts`)
   - Manages Discord.js client lifecycle
   - Handles posting to channels
   - Supports webhook-based posting

2. **API Routes** (`routes/discord.ts`)
   - REST endpoints for Discord operations
   - Validation and error handling
   - Status checks

3. **Graceful Degradation**
   - Works without bot token (webhook mode only)
   - Clear error messages when disabled
   - No impact on core functionality

## Security Considerations

- Bot token should be kept secret (use environment variables)
- Validate channel IDs before posting
- Implement rate limiting for production use
- Use webhook URLs securely (they include auth tokens)

## Future Enhancements

- Slash commands for Discord users
- Channel curation settings per server
- Automated posting schedules
- User reactions and feedback tracking
- Integration with GIF approval workflow
