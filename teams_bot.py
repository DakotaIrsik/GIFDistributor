"""
Microsoft Teams Bot for GIF Distribution

Provides Teams bot integration with:
- OAuth 2.0 authentication
- Proactive messaging
- Message posting with hosted GIFs
- Adaptive card responses
- Conversation state management

Issue: #42
Slug: teams-bot
Priority: P1
Depends on: auth, sharelinks
"""

import json
import time
import hmac
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, timezone


class ActivityType(Enum):
    """Teams activity types"""

    MESSAGE = "message"
    CONVERSATION_UPDATE = "conversationUpdate"
    MESSAGE_REACTION = "messageReaction"
    INVOKE = "invoke"


class ConversationType(Enum):
    """Teams conversation types"""

    PERSONAL = "personal"
    GROUP_CHAT = "groupChat"
    CHANNEL = "channel"


@dataclass
class TeamsIdentity:
    """Teams user or bot identity"""

    id: str
    name: str
    aad_object_id: Optional[str] = None


@dataclass
class TeamsConversation:
    """Teams conversation context"""

    id: str
    conversation_type: ConversationType
    tenant_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class TeamsActivity:
    """Teams activity (message, event, etc.)"""

    type: ActivityType
    id: str
    timestamp: datetime
    from_identity: TeamsIdentity
    conversation: TeamsConversation
    text: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    value: Optional[Dict[str, Any]] = None


@dataclass
class BotMessage:
    """Message to send via bot"""

    text: str
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    conversation_id: Optional[str] = None
    reply_to_id: Optional[str] = None


class TeamsOAuthManager:
    """
    OAuth 2.0 authentication manager for Teams bot

    Handles bot authentication with Microsoft identity platform
    and user authentication flows.
    """

    def __init__(self, app_id: str, app_password: str, tenant_id: str = "common"):
        """
        Initialize OAuth manager

        Args:
            app_id: Microsoft App ID
            app_password: Microsoft App Password
            tenant_id: Azure AD tenant ID (default: common)
        """
        self.app_id = app_id
        self.app_password = app_password
        self.tenant_id = tenant_id

        # Token cache
        self._bot_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # User auth tokens
        self._user_tokens: Dict[str, Dict[str, Any]] = {}

    def get_bot_token(self) -> str:
        """
        Get bot access token (cached)

        In production, this would call Microsoft's token endpoint.

        Returns:
            Bot access token
        """
        # Check if cached token is still valid
        if (
            self._bot_token
            and self._token_expires_at
            and datetime.now(timezone.utc) < self._token_expires_at
        ):
            return self._bot_token

        # In production: POST to https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token
        # with grant_type=client_credentials, client_id=app_id, client_secret=app_password
        # scope=https://api.botframework.com/.default

        # Mock token for development
        self._bot_token = f"bot_token_{secrets.token_urlsafe(32)}"
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        return self._bot_token

    def get_user_auth_url(
        self, state: str, redirect_uri: str, scope: str = "User.Read"
    ) -> str:
        """
        Get OAuth URL for user authentication

        Args:
            state: State parameter for CSRF protection
            redirect_uri: OAuth redirect URI
            scope: OAuth scopes (default: User.Read)

        Returns:
            Authorization URL
        """
        base_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        )

        params = {
            "client_id": self.app_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "response_mode": "query",
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in auth request

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        # In production: POST to https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
        # with grant_type=authorization_code, code=code, redirect_uri=redirect_uri,
        # client_id=app_id, client_secret=app_password

        # Mock response
        user_id = secrets.token_urlsafe(16)
        token_data = {
            "access_token": f"user_token_{secrets.token_urlsafe(32)}",
            "refresh_token": f"refresh_{secrets.token_urlsafe(32)}",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "User.Read",
            "user_id": user_id,
        }

        # Cache user token
        self._user_tokens[user_id] = {
            **token_data,
            "expires_at": datetime.now(timezone.utc)
            + timedelta(seconds=token_data["expires_in"]),
        }

        return token_data

    def get_user_token(self, user_id: str) -> Optional[str]:
        """
        Get cached user token

        Args:
            user_id: User identifier

        Returns:
            Access token or None if not found/expired
        """
        token_data = self._user_tokens.get(user_id)
        if not token_data:
            return None

        # Check expiration
        if datetime.now(timezone.utc) >= token_data["expires_at"]:
            # Token expired - should refresh here
            del self._user_tokens[user_id]
            return None

        return token_data["access_token"]

    def revoke_user_token(self, user_id: str) -> bool:
        """
        Revoke user token (logout)

        Args:
            user_id: User identifier

        Returns:
            True if token was revoked
        """
        if user_id in self._user_tokens:
            del self._user_tokens[user_id]
            return True
        return False


class TeamsBot:
    """
    Microsoft Teams Bot

    Handles incoming activities, sends messages, and manages
    conversation state for GIF distribution.
    """

    def __init__(
        self,
        app_id: str,
        app_password: str,
        service_url: str = "https://smba.trafficmanager.net/amer/",
        oauth_manager: Optional[TeamsOAuthManager] = None,
    ):
        """
        Initialize Teams bot

        Args:
            app_id: Microsoft App ID
            app_password: Microsoft App Password
            service_url: Bot Framework service URL
            oauth_manager: Optional OAuth manager (created if not provided)
        """
        self.app_id = app_id
        self.app_password = app_password
        self.service_url = service_url.rstrip("/")

        # OAuth
        self.oauth = oauth_manager or TeamsOAuthManager(app_id, app_password)

        # Conversation state storage (in production, use database)
        self._conversations: Dict[str, Dict[str, Any]] = {}

        # Activity handlers
        self._message_handlers: List[callable] = []
        self._conversation_update_handlers: List[callable] = []

        # Analytics
        self._activity_log: List[Dict[str, Any]] = []

    def verify_request(self, auth_header: str, request_body: str) -> bool:
        """
        Verify incoming request from Bot Framework

        Args:
            auth_header: Authorization header
            request_body: Request body JSON

        Returns:
            True if request is valid
        """
        # In production, validate JWT token from auth_header
        # against Microsoft's public keys

        # For development, simple validation
        if not auth_header or not auth_header.startswith("Bearer "):
            return False

        return True

    def handle_activity(
        self, activity_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle incoming activity from Teams

        Args:
            activity_data: Activity JSON from Bot Framework

        Returns:
            Response to send back (or None)
        """
        # Parse activity
        activity = self._parse_activity(activity_data)

        # Log activity
        self._activity_log.append(
            {
                "activity_type": activity.type.value,
                "conversation_id": activity.conversation.id,
                "from": activity.from_identity.name,
                "timestamp": activity.timestamp.isoformat(),
            }
        )

        # Route to appropriate handler
        if activity.type == ActivityType.MESSAGE:
            return self._handle_message(activity)
        elif activity.type == ActivityType.CONVERSATION_UPDATE:
            return self._handle_conversation_update(activity)
        elif activity.type == ActivityType.INVOKE:
            return self._handle_invoke(activity)

        return None

    def _parse_activity(self, data: Dict[str, Any]) -> TeamsActivity:
        """Parse activity data into TeamsActivity object"""
        return TeamsActivity(
            type=ActivityType(data.get("type", "message")),
            id=data.get("id", ""),
            timestamp=datetime.fromisoformat(
                data.get(
                    "timestamp", datetime.now(timezone.utc).isoformat() + "Z"
                ).replace("Z", "+00:00")
            ),
            from_identity=TeamsIdentity(
                id=data.get("from", {}).get("id", ""),
                name=data.get("from", {}).get("name", ""),
                aad_object_id=data.get("from", {}).get("aadObjectId"),
            ),
            conversation=TeamsConversation(
                id=data.get("conversation", {}).get("id", ""),
                conversation_type=ConversationType(
                    data.get("conversation", {}).get("conversationType", "personal")
                ),
                tenant_id=data.get("conversation", {}).get("tenantId"),
                name=data.get("conversation", {}).get("name"),
            ),
            text=data.get("text"),
            attachments=data.get("attachments", []),
            value=data.get("value"),
        )

    def _handle_message(self, activity: TeamsActivity) -> Optional[Dict[str, Any]]:
        """Handle incoming message"""
        # Update conversation state
        self._update_conversation_state(activity)

        # Call registered message handlers
        for handler in self._message_handlers:
            response = handler(activity)
            if response:
                return response

        # Default response
        if activity.text and "help" in activity.text.lower():
            return self._create_help_response()

        return None

    def _handle_conversation_update(
        self, activity: TeamsActivity
    ) -> Optional[Dict[str, Any]]:
        """Handle conversation update (bot added/removed)"""
        # Call registered handlers
        for handler in self._conversation_update_handlers:
            response = handler(activity)
            if response:
                return response

        # Send welcome message when bot is added
        return self._create_welcome_response()

    def _handle_invoke(self, activity: TeamsActivity) -> Optional[Dict[str, Any]]:
        """Handle invoke activity (adaptive card actions)"""
        if activity.value:
            action = activity.value.get("action")

            if action == "auth":
                # Return OAuth card
                return self._create_oauth_card_response()

        return None

    def _update_conversation_state(self, activity: TeamsActivity):
        """Update conversation state"""
        conv_id = activity.conversation.id

        if conv_id not in self._conversations:
            self._conversations[conv_id] = {
                "id": conv_id,
                "type": activity.conversation.conversation_type.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "messages": [],
            }

        self._conversations[conv_id]["messages"].append(
            {
                "from": activity.from_identity.name,
                "text": activity.text,
                "timestamp": activity.timestamp.isoformat(),
            }
        )

    def send_message(
        self,
        conversation_id: str,
        text: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Send message to conversation

        Args:
            conversation_id: Teams conversation ID
            text: Message text
            attachments: Optional attachments (adaptive cards, etc.)

        Returns:
            True if sent successfully
        """
        # Get bot token
        token = self.oauth.get_bot_token()

        # Build message payload
        payload = {
            "type": "message",
            "from": {"id": f"28:{self.app_id}", "name": "GIF Distribution Bot"},
            "conversation": {"id": conversation_id},
            "text": text,
        }

        if attachments:
            payload["attachments"] = attachments

        # In production: POST to {service_url}/v3/conversations/{conversation_id}/activities
        # with Authorization: Bearer {token}

        # Log the message
        self._activity_log.append(
            {
                "type": "outgoing_message",
                "conversation_id": conversation_id,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return True

    def send_gif_card(
        self,
        conversation_id: str,
        gif_url: str,
        title: str,
        description: str = "",
        share_url: Optional[str] = None,
    ) -> bool:
        """
        Send adaptive card with GIF

        Args:
            conversation_id: Teams conversation ID
            gif_url: URL to GIF/MP4
            title: GIF title
            description: Optional description
            share_url: Optional share link

        Returns:
            True if sent successfully
        """
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "Bolder",
                    "size": "Large",
                },
                {"type": "Image", "url": gif_url, "size": "Stretch"},
            ],
        }

        if description:
            card["body"].insert(
                1, {"type": "TextBlock", "text": description, "wrap": True}
            )

        if share_url:
            card["actions"] = [
                {"type": "Action.OpenUrl", "title": "Share", "url": share_url}
            ]

        attachment = {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card,
        }

        return self.send_message(conversation_id, text="", attachments=[attachment])

    def _create_welcome_response(self) -> Dict[str, Any]:
        """Create welcome message response"""
        return {
            "type": "message",
            "text": "Welcome to GIF Distribution Bot! 🎉\n\n"
            "I can help you share GIFs across platforms.\n\n"
            'Type "help" to see what I can do.',
        }

    def _create_help_response(self) -> Dict[str, Any]:
        """Create help message response"""
        return {
            "type": "message",
            "text": "**GIF Distribution Bot Commands**\n\n"
            "• `help` - Show this help message\n"
            "• `login` - Authenticate with OAuth\n"
            "• `search [query]` - Search for GIFs\n"
            "• `share [gif_id]` - Share a GIF",
        }

    def _create_oauth_card_response(self) -> Dict[str, Any]:
        """Create OAuth sign-in card"""
        state = secrets.token_urlsafe(16)
        auth_url = self.oauth.get_user_auth_url(
            state=state, redirect_uri="https://yourapp.com/auth/callback"
        )

        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Sign in to continue",
                    "weight": "Bolder",
                    "size": "Medium",
                },
                {
                    "type": "TextBlock",
                    "text": "Click below to sign in with your Microsoft account",
                    "wrap": True,
                },
            ],
            "actions": [
                {"type": "Action.OpenUrl", "title": "Sign In", "url": auth_url}
            ],
        }

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                }
            ],
        }

    def on_message(self, handler: callable):
        """
        Register message handler

        Args:
            handler: Function that takes TeamsActivity and returns response dict
        """
        self._message_handlers.append(handler)

    def on_conversation_update(self, handler: callable):
        """
        Register conversation update handler

        Args:
            handler: Function that takes TeamsActivity and returns response dict
        """
        self._conversation_update_handlers.append(handler)

    def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation state

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation state or None
        """
        return self._conversations.get(conversation_id)

    def get_analytics(self) -> Dict[str, Any]:
        """
        Get bot analytics

        Returns:
            Analytics summary
        """
        total_activities = len(self._activity_log)
        total_conversations = len(self._conversations)

        # Count by type
        activity_types = {}
        for activity in self._activity_log:
            atype = activity.get("activity_type", activity.get("type", "unknown"))
            activity_types[atype] = activity_types.get(atype, 0) + 1

        return {
            "total_activities": total_activities,
            "total_conversations": total_conversations,
            "activity_types": activity_types,
            "active_users": len(
                set(a.get("from") for a in self._activity_log if a.get("from"))
            ),
        }


# Example usage
if __name__ == "__main__":
    # Initialize bot
    bot = TeamsBot(app_id="your-app-id", app_password="your-app-password")

    # Register custom message handler
    def custom_message_handler(activity: TeamsActivity):
        if activity.text and "gif" in activity.text.lower():
            return {"type": "message", "text": "Looking for GIFs? Try searching!"}
        return None

    bot.on_message(custom_message_handler)

    # Simulate incoming activity
    activity_data = {
        "type": "message",
        "id": "12345",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "from": {"id": "user123", "name": "Test User"},
        "conversation": {"id": "conv123", "conversationType": "personal"},
        "text": "hello",
    }

    response = bot.handle_activity(activity_data)
    print(f"Response: {response}")

    # Send GIF
    bot.send_gif_card(
        conversation_id="conv123",
        gif_url="https://example.com/cat.gif",
        title="Cute Cat",
        description="A very cute cat doing cat things",
        share_url="https://gifdist.io/s/abc123",
    )

    # Get analytics
    analytics = bot.get_analytics()
    print(f"Analytics: {analytics}")
