# Slack App Setup Guide

**Issue**: #26
**Status**: Implementation Complete
**Dependencies**: #3 (auth), #27 (storage-cdn)

## Overview

This guide covers setting up the GIF Distributor Slack app for OAuth integration and posting GIFs to Slack workspaces.

## Features

- **OAuth 2.0 Integration**: Secure workspace installation
- **Message Posting**: Post hosted GIFs to channels
- **File Upload**: Direct file upload as fallback
- **Channel Management**: List and select channels
- **Webhook Verification**: Secure request validation

## Prerequisites

1. Slack workspace with admin access
2. Storage/CDN for hosting GIF files (#27)
3. Auth system for user management (#3)

## Slack App Configuration

### 1. Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name: **GIF Distributor**
4. Select your development workspace

### 2. Configure OAuth & Permissions

Navigate to **OAuth & Permissions** and add these Bot Token Scopes:

- `chat:write` - Post messages to channels
- `files:write` - Upload files to Slack
- `links:write` - Unfurl links in messages
- `channels:read` - View public channels
- `groups:read` - View private channels
- `im:read` - View direct messages
- `mpim:read` - View group messages

### 3. Set Redirect URLs

Add these OAuth Redirect URLs:
- Development: `http://localhost:3001/api/slack/oauth/callback`
- Production: `https://your-domain.com/api/slack/oauth/callback`

### 4. Get Credentials

From **Basic Information**:
- Client ID: `SLACK_CLIENT_ID`
- Client Secret: `SLACK_CLIENT_SECRET`
- Signing Secret: `SLACK_SIGNING_SECRET`

## Environment Variables

Add to `.env`:

```env
# Slack App Credentials
SLACK_CLIENT_ID=your_client_id_here
SLACK_CLIENT_SECRET=your_client_secret_here
SLACK_SIGNING_SECRET=your_signing_secret_here
SLACK_REDIRECT_URI=http://localhost:3001/api/slack/oauth/callback
```

## API Endpoints

### OAuth Flow

#### 1. Installation URL
```
GET /api/slack/install
```

Redirects user to Slack's OAuth authorization page.

**Response**: Redirect to Slack OAuth

---

#### 2. OAuth Callback
```
GET /api/slack/oauth/callback?code={code}&state={state}
```

Handles OAuth redirect and exchanges code for access token.

**Response**:
```json
{
  "success": true,
  "team": "Your Workspace",
  "message": "Successfully installed GIF Distributor to your Slack workspace"
}
```

---

### Message Posting

#### Post Message with GIF
```
POST /api/slack/post-message
```

**Request Body**:
```json
{
  "team_id": "T123456",
  "channel_id": "C123456",
  "gif_url": "https://cdn.example.com/gifs/abc123.gif",
  "title": "Epic Reaction GIF",
  "tags": ["reaction", "happy", "celebration"]
}
```

**Response**:
```json
{
  "success": true,
  "message_ts": "1234567890.123456",
  "channel": "C123456"
}
```

---

#### Upload File
```
POST /api/slack/upload-file
```

**Request Body**:
```json
{
  "team_id": "T123456",
  "channel_id": "C123456",
  "file_url": "https://cdn.example.com/gifs/abc123.gif",
  "filename": "reaction.gif",
  "title": "Epic Reaction GIF",
  "comment": "Check this out!"
}
```

**Response**:
```json
{
  "success": true,
  "file": {
    "id": "F123456",
    "name": "reaction.gif",
    "permalink": "https://files.slack.com/..."
  }
}
```

---

### Workspace Management

#### Get Channels
```
GET /api/slack/channels/:team_id
```

**Response**:
```json
{
  "success": true,
  "channels": [
    {
      "id": "C123456",
      "name": "general",
      "is_member": true
    }
  ]
}
```

---

#### Health Check
```
GET /api/slack/health
```

**Response**:
```json
{
  "status": "ok",
  "service": "slack-integration",
  "configured": true,
  "workspaces": 3
}
```

## Usage Flow

### 1. Workspace Installation

```javascript
// User clicks "Add to Slack" button
window.location.href = 'https://your-api.com/api/slack/install';

// After authorization, user is redirected to callback
// Token is stored and workspace is ready
```

### 2. Post a GIF

```javascript
const response = await fetch('https://your-api.com/api/slack/post-message', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    team_id: 'T123456',
    channel_id: 'C123456',
    gif_url: 'https://cdn.example.com/gifs/celebration.gif',
    title: 'Celebration Time!',
    tags: ['party', 'celebration']
  })
});
```

### 3. Upload File (Fallback)

```javascript
const response = await fetch('https://your-api.com/api/slack/upload-file', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    team_id: 'T123456',
    channel_id: 'C123456',
    file_url: 'https://cdn.example.com/gifs/celebration.gif',
    filename: 'celebration.gif',
    title: 'Celebration Time!'
  })
});
```

## Architecture

### Token Storage

**Current**: In-memory Map (development only)

**Production**: Use database with encryption
```typescript
interface WorkspaceToken {
  access_token: string;     // Encrypted
  team_id: string;          // Primary key
  team_name: string;
  bot_user_id: string;
  scope: string;
  installed_at: Date;
  updated_at: Date;
}
```

### Security

1. **Request Verification**: All webhook requests verified with signing secret
2. **HTTPS Only**: Production must use HTTPS
3. **Token Encryption**: Store tokens encrypted at rest
4. **Scope Minimization**: Request only necessary permissions
5. **State Parameter**: CSRF protection in OAuth flow

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Workspace not authenticated` | Team ID not found | User needs to reinstall app |
| `OAuth authorization failed` | User denied access | Ask user to try again |
| `Failed to post message` | Invalid channel or permissions | Check channel ID and bot permissions |
| `not_in_channel` | Bot not in channel | Invite bot to channel first |

## Testing

### Manual Testing

1. Start API server:
```bash
cd api
npm run dev
```

2. Visit install URL:
```
http://localhost:3001/api/slack/install
```

3. Authorize workspace

4. Post test message:
```bash
curl -X POST http://localhost:3001/api/slack/post-message \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "T123456",
    "channel_id": "C123456",
    "gif_url": "https://example.com/test.gif",
    "title": "Test GIF"
  }'
```

### Integration Testing

See `tests/slack-app.test.ts` for automated tests.

## Production Deployment

### Checklist

- [ ] Set environment variables in production
- [ ] Update redirect URI in Slack app settings
- [ ] Implement database token storage
- [ ] Enable HTTPS
- [ ] Set up error monitoring
- [ ] Configure rate limiting
- [ ] Add analytics tracking
- [ ] Implement token refresh logic
- [ ] Set up webhook endpoints for events
- [ ] Add app uninstallation handler

### Database Migration

```sql
CREATE TABLE slack_workspaces (
  team_id VARCHAR(20) PRIMARY KEY,
  team_name VARCHAR(255) NOT NULL,
  access_token TEXT NOT NULL,  -- Encrypted
  bot_user_id VARCHAR(20) NOT NULL,
  scope TEXT NOT NULL,
  installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_team_name ON slack_workspaces(team_name);
```

## Related Issues

- [#26](https://github.com/your-repo/issues/26) - Slack app: OAuth + post message with hosted GIF (this issue)
- [#41](https://github.com/your-repo/issues/41) - Slack share: link unfurls
- [#3](https://github.com/your-repo/issues/3) - Auth system
- [#27](https://github.com/your-repo/issues/27) - Object storage + CDN

## Resources

- [Slack API Documentation](https://api.slack.com/)
- [OAuth 2.0 Guide](https://api.slack.com/authentication/oauth-v2)
- [Bot Token Scopes](https://api.slack.com/scopes)
- [Message Formatting](https://api.slack.com/reference/messaging/attachments)
