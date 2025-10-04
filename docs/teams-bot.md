# Microsoft Teams Bot Integration

This document describes the Microsoft Teams Bot integration for GIF distribution.

## Overview

The Teams bot provides:
- **OAuth 2.0 Authentication**: Secure user authentication via Microsoft identity platform
- **Message Handling**: Process incoming messages and send responses
- **Adaptive Cards**: Rich GIF cards with playable media
- **Conversation State**: Track and manage conversation context
- **Proactive Messaging**: Send messages to users/channels
- **Analytics**: Track bot usage and engagement

## Architecture

### Components

1. **TeamsOAuthManager**: Handles OAuth 2.0 flows for both bot and user authentication
2. **TeamsBot**: Main bot class that processes activities and sends messages
3. **Activity Handlers**: Extensible handlers for different activity types

### Authentication Flow

#### Bot Authentication
1. Bot requests access token from Microsoft identity platform
2. Token is cached and refreshed automatically
3. Token is used for all Bot Framework API calls

#### User Authentication
1. User clicks "Sign In" in adaptive card
2. Redirected to Microsoft OAuth consent page
3. After consent, receives authorization code
4. Code is exchanged for access token
5. Token is cached for subsequent API calls

## Setup

### Prerequisites

1. **Azure Bot Registration**:
   - Register bot in Azure portal
   - Get App ID and App Password
   - Configure messaging endpoint

2. **Teams App Manifest**:
   ```json
   {
     "bots": [
       {
         "botId": "YOUR_APP_ID",
         "scopes": ["personal", "team", "groupchat"],
         "supportsFiles": true,
         "isNotificationOnly": false
       }
     ],
     "permissions": ["identity", "messageTeamMembers"]
   }
   ```

### Configuration

```python
from teams_bot import TeamsBot

bot = TeamsBot(
    app_id="YOUR_APP_ID",
    app_password="YOUR_APP_PASSWORD",
    service_url="https://smba.trafficmanager.net/amer/"
)
```

## Usage

### Handling Messages

```python
from teams_bot import TeamsBot, TeamsActivity

bot = TeamsBot(app_id="...", app_password="...")

# Register custom handler
def handle_gif_search(activity: TeamsActivity):
    if activity.text and 'search' in activity.text.lower():
        # Perform search and return results
        return {
            'type': 'message',
            'text': 'Found 10 GIFs matching your query!'
        }
    return None

bot.on_message(handle_gif_search)
```

### Sending GIF Cards

```python
# Send adaptive card with GIF
bot.send_gif_card(
    conversation_id="19:meeting_abc123",
    gif_url="https://cdn.example.com/cat.gif",
    title="Funny Cat GIF",
    description="A cat doing funny things",
    share_url="https://gifdist.io/s/abc123"
)
```

### OAuth Integration

```python
from teams_bot import TeamsOAuthManager

oauth = TeamsOAuthManager(
    app_id="YOUR_APP_ID",
    app_password="YOUR_APP_PASSWORD"
)

# Get auth URL for user
auth_url = oauth.get_user_auth_url(
    state="random_csrf_token",
    redirect_uri="https://yourapp.com/auth/callback"
)

# After user authenticates, exchange code for token
token_data = oauth.exchange_code_for_token(
    code=request.args.get('code'),
    redirect_uri="https://yourapp.com/auth/callback"
)

# Use token for API calls
access_token = token_data['access_token']
```

### Processing Incoming Activities

```python
# In your web endpoint
@app.post("/api/messages")
def handle_teams_message(request):
    # Verify request
    auth_header = request.headers.get('Authorization')
    if not bot.verify_request(auth_header, request.body):
        return {"error": "Unauthorized"}, 401

    # Handle activity
    activity_data = request.json()
    response = bot.handle_activity(activity_data)

    return response or {}, 200
```

## Activity Types

### Message
User sends a message to the bot
```python
{
    'type': 'message',
    'text': 'search cats',
    'from': {'id': 'user123', 'name': 'John Doe'},
    'conversation': {'id': 'conv123', 'conversationType': 'personal'}
}
```

### Conversation Update
Bot is added/removed from conversation
```python
{
    'type': 'conversationUpdate',
    'membersAdded': [{'id': 'bot123'}],
    'conversation': {'id': 'conv123'}
}
```

### Invoke
Adaptive card action is triggered
```python
{
    'type': 'invoke',
    'name': 'adaptiveCard/action',
    'value': {'action': 'share', 'gifId': 'abc123'}
}
```

## Adaptive Card Examples

### Basic GIF Card

```python
card = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.5",
    "body": [
        {
            "type": "TextBlock",
            "text": "Funny Cat",
            "weight": "Bolder",
            "size": "Large"
        },
        {
            "type": "Image",
            "url": "https://cdn.example.com/cat.gif"
        }
    ],
    "actions": [
        {
            "type": "Action.OpenUrl",
            "title": "Share",
            "url": "https://gifdist.io/s/abc123"
        }
    ]
}
```

### OAuth Sign-In Card

Automatically generated by `bot._create_oauth_card_response()`

## Conversation State

Track conversation context:

```python
# Get conversation state
state = bot.get_conversation_state("conv123")

# State includes:
# - Conversation ID
# - Conversation type (personal/groupChat/channel)
# - Message history
# - Created timestamp
```

## Analytics

```python
analytics = bot.get_analytics()

# Returns:
{
    'total_activities': 150,
    'total_conversations': 25,
    'activity_types': {
        'message': 100,
        'conversationUpdate': 20,
        'outgoing_message': 30
    },
    'active_users': 15
}
```

## Security

### Request Verification

All incoming requests are verified:
1. Check Authorization header for Bearer token
2. Validate JWT signature against Microsoft public keys
3. Verify token claims (audience, issuer, expiration)

### Token Management

- Bot tokens are cached and refreshed automatically
- User tokens expire after 1 hour by default
- Refresh tokens can be used to get new access tokens
- All tokens are stored securely (use production-grade secret management)

## Best Practices

1. **Error Handling**: Always wrap bot operations in try/catch
2. **Rate Limiting**: Respect Teams API rate limits (avoid spam)
3. **Proactive Messages**: Only send when user has opted in
4. **Privacy**: Don't log sensitive user information
5. **State Management**: Use proper database for production (not in-memory)
6. **Token Storage**: Use Azure Key Vault or similar for secrets

## Integration with Other Modules

### With Auth Module
```python
from auth import AuthManager
from teams_bot import TeamsBot

auth = AuthManager()
bot = TeamsBot(app_id="...", app_password="...")

# Link Teams user to app user
def link_user(teams_user_id, app_user_id):
    # Store mapping in database
    pass
```

### With Share Links
```python
from sharelinks import ShareLinkGenerator
from teams_bot import TeamsBot

link_gen = ShareLinkGenerator()
bot = TeamsBot(app_id="...", app_password="...")

# Create share link and send via bot
link = link_gen.create_share_link(asset_id="gif123", title="Cat GIF")
bot.send_gif_card(
    conversation_id="conv123",
    gif_url="https://cdn.example.com/cat.gif",
    title="Cat GIF",
    share_url=link['short_url']
)
```

## Troubleshooting

### Bot not receiving messages
- Check messaging endpoint in Azure portal
- Verify endpoint is publicly accessible (HTTPS required)
- Check bot is added to the conversation

### Authentication failures
- Verify App ID and Password are correct
- Check Azure AD app registration
- Ensure proper scopes are configured

### Cards not rendering
- Validate card JSON against Adaptive Cards schema
- Check Teams client version supports card features
- Test card in Adaptive Cards Designer

## References

- [Bot Framework Documentation](https://docs.microsoft.com/en-us/azure/bot-service/)
- [Teams Bot API](https://docs.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/)
- [Adaptive Cards](https://adaptivecards.io/)
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)

## Issue Reference

- **Issue**: #42
- **Slug**: teams-bot
- **Priority**: P1
- **Dependencies**: auth (#3), sharelinks (#40)
