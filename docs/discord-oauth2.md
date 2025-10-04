# Discord Bot OAuth2 Integration

**Issue #9: Discord bot: OAuth2 + send embed/attachment**

## Overview

This module provides Discord OAuth2 authentication and messaging capabilities for the GIF Distributor platform. It enables users to authenticate with Discord and allows the platform to send GIFs as embeds or attachments to Discord channels.

## Features

✅ **OAuth2 Authentication**
- Complete OAuth2 flow implementation
- Authorization URL generation
- Token exchange and refresh
- User information retrieval
- Guild (server) access

✅ **Message & Embed Sending**
- Send rich embeds with GIFs
- Send file attachments
- Support for both bot tokens and OAuth access tokens
- Customizable embed styling

## Architecture

### Components

1. **DiscordOAuth2** - Handles OAuth2 authentication flow
2. **DiscordMessenger** - Manages message and embed sending

### Dependencies

- auth (#3) - Provides base authentication infrastructure
- shortlinks (#48) - Used for shortened GIF URLs in messages
- transcode (#30) - Ensures GIFs are in Discord-compatible formats

## Configuration

### Environment Variables

```bash
# Discord Application Credentials
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
DISCORD_REDIRECT_URI=http://localhost:3000/auth/discord/callback

# Discord Bot Token (optional, for bot-based messaging)
DISCORD_BOT_TOKEN=your_bot_token
```

### Setting Up Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Navigate to **OAuth2** section:
   - Add redirect URI: `http://localhost:3000/auth/discord/callback`
   - Note your Client ID and Client Secret
4. (Optional) For bot functionality:
   - Go to **Bot** section
   - Create a bot and copy the token
   - Enable required intents: Guilds, Guild Messages

## OAuth2 Flow

### Step 1: Authorization

Generate an authorization URL and redirect the user:

```python
from discord_bot import DiscordOAuth2

oauth = DiscordOAuth2()

# Generate authorization URL with CSRF protection
auth_url = oauth.get_authorization_url(
    state='random_csrf_token_123',
    scopes=['identify', 'guilds', 'webhook.incoming']
)

# Redirect user to auth_url
```

### Step 2: Token Exchange

After user authorizes, exchange the code for tokens:

```python
# Receive code from callback
code = request.args.get('code')
state = request.args.get('state')

# Verify state matches CSRF token
if state != 'random_csrf_token_123':
    raise ValueError('Invalid state parameter')

# Exchange code for tokens
token_data = oauth.exchange_code_for_token(code)

# Store tokens securely
access_token = token_data['access_token']
refresh_token = token_data['refresh_token']
expires_in = token_data['expires_in']
```

### Step 3: User Information

Retrieve user information:

```python
# Get user details
user_info = oauth.get_user_info(access_token)

print(f"User ID: {user_info['id']}")
print(f"Username: {user_info['username']}")
print(f"Avatar: {user_info['avatar']}")

# Get user's guilds (servers)
guilds = oauth.get_user_guilds(access_token)
for guild in guilds:
    print(f"Guild: {guild['name']} (ID: {guild['id']})")
```

### Step 4: Token Refresh

Refresh expired access tokens:

```python
# When access token expires
new_token_data = oauth.refresh_access_token(refresh_token)
new_access_token = new_token_data['access_token']
new_refresh_token = new_token_data['refresh_token']
```

## Sending Messages

### Send GIF Embed

```python
from discord_bot import DiscordMessenger

messenger = DiscordMessenger()

# Send GIF as embed using OAuth token
messenger.send_gif_embed(
    channel_id='1234567890',
    gif_url='https://cdn.example.com/awesome.gif',
    title='Awesome GIF!',
    description='Check out this amazing GIF',
    source_url='https://example.com/source',
    access_token=user_access_token
)

# Or use bot token (set via DISCORD_BOT_TOKEN env var)
messenger.send_gif_embed(
    channel_id='1234567890',
    gif_url='https://cdn.example.com/awesome.gif',
    title='Bot-posted GIF',
    description='Posted using bot token'
)
```

### Create Custom Embed

```python
# Create a custom embed
embed = messenger.create_embed(
    title='Custom Embed',
    description='This is a custom embed with a GIF',
    url='https://example.com',
    color=0x00FF00,  # Green
    image_url='https://cdn.example.com/image.gif',
    thumbnail_url='https://cdn.example.com/thumb.png',
    footer_text='GIF Distributor',
    author_name='GIF Bot'
)

# Send the embed
messenger.send_embed(
    channel_id='1234567890',
    embed=embed,
    content='Look at this!',
    access_token=user_access_token
)
```

### Send File Attachment

```python
# Send GIF as file attachment
messenger.send_attachment(
    channel_id='1234567890',
    file_url='https://example.com/large.gif',
    filename='large.gif',
    content='Here is a large GIF file',
    access_token=user_access_token
)
```

## API Reference

### DiscordOAuth2

#### `get_authorization_url(state=None, scopes=None)`

Generate OAuth2 authorization URL.

**Parameters:**
- `state` (str, optional): CSRF protection token
- `scopes` (list, optional): OAuth2 scopes (default: `['identify', 'guilds', 'webhook.incoming']`)

**Returns:** Authorization URL string

#### `exchange_code_for_token(code)`

Exchange authorization code for access token.

**Parameters:**
- `code` (str): Authorization code from callback

**Returns:** Dictionary with `access_token`, `refresh_token`, `expires_in`, etc.

#### `refresh_access_token(refresh_token)`

Refresh an expired access token.

**Parameters:**
- `refresh_token` (str): Refresh token

**Returns:** Dictionary with new tokens

#### `get_user_info(access_token)`

Get authenticated user information.

**Parameters:**
- `access_token` (str): User's access token

**Returns:** User object with `id`, `username`, `discriminator`, `avatar`, etc.

#### `get_user_guilds(access_token)`

Get list of user's guilds.

**Parameters:**
- `access_token` (str): User's access token

**Returns:** List of guild objects

### DiscordMessenger

#### `create_embed(...)`

Create a Discord embed object.

**Parameters:**
- `title` (str, optional): Embed title
- `description` (str, optional): Embed description
- `url` (str, optional): Title URL
- `color` (int, optional): Embed color (default: 5814783 - Discord blurple)
- `image_url` (str, optional): Main image URL
- `thumbnail_url` (str, optional): Thumbnail URL
- `footer_text` (str, optional): Footer text
- `author_name` (str, optional): Author name

**Returns:** Embed dictionary

#### `send_embed(channel_id, embed, access_token=None, content=None)`

Send an embed to a channel.

**Parameters:**
- `channel_id` (str): Discord channel ID
- `embed` (dict): Embed object
- `access_token` (str, optional): OAuth token (uses bot token if not provided)
- `content` (str, optional): Message content

**Returns:** Discord message object

#### `send_attachment(channel_id, file_url, filename, access_token=None, content=None)`

Send a file attachment.

**Parameters:**
- `channel_id` (str): Discord channel ID
- `file_url` (str): URL of file to send
- `filename` (str): Filename
- `access_token` (str, optional): OAuth token
- `content` (str, optional): Message content

**Returns:** Discord message object

#### `send_gif_embed(channel_id, gif_url, title, description=None, source_url=None, access_token=None)`

Send a GIF as an embed.

**Parameters:**
- `channel_id` (str): Discord channel ID
- `gif_url` (str): GIF URL
- `title` (str): Embed title
- `description` (str, optional): Description
- `source_url` (str, optional): Source URL
- `access_token` (str, optional): OAuth token

**Returns:** Discord message object

## Security Considerations

### Token Storage
- **Never store tokens in plaintext**
- Use encrypted database or secure key-value store
- Implement token rotation
- Set appropriate expiration times

### CSRF Protection
- Always use `state` parameter in OAuth flow
- Verify state on callback
- Use cryptographically secure random values

### Rate Limiting
- Respect Discord's rate limits
- Implement exponential backoff
- Cache responses where appropriate

### Permissions
- Request minimal scopes necessary
- Validate channel access before posting
- Handle permission errors gracefully

### Bot Token Security
- Store bot token in environment variables only
- Never commit tokens to version control
- Rotate tokens if compromised
- Use bot tokens only on server-side

## Error Handling

```python
from discord_bot import DiscordOAuth2, DiscordMessenger
import requests

try:
    oauth = DiscordOAuth2()
    token_data = oauth.exchange_code_for_token(code)
except requests.HTTPError as e:
    if e.response.status_code == 400:
        print("Invalid authorization code")
    elif e.response.status_code == 401:
        print("Invalid client credentials")
    else:
        print(f"Token exchange failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

try:
    messenger = DiscordMessenger()
    messenger.send_gif_embed(...)
except requests.HTTPError as e:
    if e.response.status_code == 403:
        print("Missing permissions for channel")
    elif e.response.status_code == 404:
        print("Channel not found")
    elif e.response.status_code == 429:
        print("Rate limited")
    else:
        print(f"Send failed: {e}")
```

## Testing

Run the test suite:

```bash
python -m pytest test_discord_bot.py -v
```

Run specific test:

```bash
python -m pytest test_discord_bot.py::TestDiscordOAuth2::test_get_authorization_url -v
```

## Integration with GIF Distributor

### User Flow

1. User clicks "Connect Discord" on GIF Distributor
2. User is redirected to Discord OAuth2 authorization
3. User authorizes the application
4. GIF Distributor receives callback with code
5. Code is exchanged for access token
6. User can now post GIFs to their Discord channels

### Publishing Workflow

```python
# When user publishes a GIF
def publish_to_discord(gif_id, user_id, channel_id):
    # Get GIF details
    gif = get_gif_from_database(gif_id)

    # Get user's Discord access token
    access_token = get_user_discord_token(user_id)

    # Refresh token if expired
    if is_token_expired(access_token):
        access_token = refresh_user_token(user_id)

    # Send GIF to Discord
    messenger = DiscordMessenger()
    result = messenger.send_gif_embed(
        channel_id=channel_id,
        gif_url=gif['cdn_url'],
        title=gif['title'],
        description=gif['description'],
        source_url=gif['short_url'],
        access_token=access_token
    )

    return result
```

## Future Enhancements

- [ ] Slash commands support
- [ ] Interactive components (buttons, selects)
- [ ] Scheduled posting
- [ ] Multi-channel broadcasting
- [ ] GIF search via Discord bot
- [ ] Reaction-based curation
- [ ] Guild-specific settings
- [ ] Analytics and tracking

## Related Documentation

- [Discord API Documentation](https://discord.com/developers/docs)
- [Discord OAuth2 Guide](https://discord.com/developers/docs/topics/oauth2)
- [Auth Module](../auth.py) (Issue #3)
- [Shortlinks Module](../sharelinks.py) (Issue #48)
- [Transcode Module](../transcode.py) (Issue #30)
