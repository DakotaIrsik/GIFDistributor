"""
Tests for Microsoft Teams Bot module

Issue: #42
"""

import pytest
from datetime import datetime, timedelta, timezone
from teams_bot import (
    TeamsBot,
    TeamsOAuthManager,
    TeamsActivity,
    TeamsIdentity,
    TeamsConversation,
    ActivityType,
    ConversationType,
)


class TestTeamsOAuthManager:
    """Test OAuth manager"""

    def test_initialization(self):
        """Test OAuth manager initialization"""
        oauth = TeamsOAuthManager(
            app_id="test-app-id", app_password="test-password", tenant_id="test-tenant"
        )

        assert oauth.app_id == "test-app-id"
        assert oauth.app_password == "test-password"
        assert oauth.tenant_id == "test-tenant"

    def test_get_bot_token(self):
        """Test bot token generation"""
        oauth = TeamsOAuthManager("app-id", "password")

        token1 = oauth.get_bot_token()
        assert token1.startswith("bot_token_")

        # Second call should return cached token
        token2 = oauth.get_bot_token()
        assert token1 == token2

    def test_get_user_auth_url(self):
        """Test user auth URL generation"""
        oauth = TeamsOAuthManager("app-id", "password", "common")

        url = oauth.get_user_auth_url(
            state="test-state", redirect_uri="https://example.com/callback"
        )

        assert "login.microsoftonline.com" in url
        assert "client_id=app-id" in url
        assert "state=test-state" in url
        assert "redirect_uri=https://example.com/callback" in url

    def test_exchange_code_for_token(self):
        """Test exchanging auth code for token"""
        oauth = TeamsOAuthManager("app-id", "password")

        token_data = oauth.exchange_code_for_token(
            code="auth-code", redirect_uri="https://example.com/callback"
        )

        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert "expires_in" in token_data
        assert token_data["access_token"].startswith("user_token_")

    def test_get_user_token(self):
        """Test getting cached user token"""
        oauth = TeamsOAuthManager("app-id", "password")

        # Exchange code first
        token_data = oauth.exchange_code_for_token("code", "https://example.com")
        user_id = token_data["user_id"]

        # Get cached token
        token = oauth.get_user_token(user_id)
        assert token == token_data["access_token"]

        # Non-existent user
        assert oauth.get_user_token("nonexistent") is None

    def test_revoke_user_token(self):
        """Test revoking user token"""
        oauth = TeamsOAuthManager("app-id", "password")

        token_data = oauth.exchange_code_for_token("code", "https://example.com")
        user_id = token_data["user_id"]

        # Revoke token
        assert oauth.revoke_user_token(user_id) is True
        assert oauth.get_user_token(user_id) is None

        # Revoke non-existent
        assert oauth.revoke_user_token("nonexistent") is False


class TestTeamsBot:
    """Test Teams bot"""

    def test_initialization(self):
        """Test bot initialization"""
        bot = TeamsBot(app_id="test-app", app_password="test-password")

        assert bot.app_id == "test-app"
        assert bot.app_password == "test-password"
        assert bot.oauth is not None

    def test_verify_request(self):
        """Test request verification"""
        bot = TeamsBot("app-id", "password")

        # Valid request
        assert bot.verify_request("Bearer token123", "{}") is True

        # Invalid request (no Bearer)
        assert bot.verify_request("token123", "{}") is False
        assert bot.verify_request("", "{}") is False

    def test_handle_message_activity(self):
        """Test handling message activity"""
        bot = TeamsBot("app-id", "password")

        activity_data = {
            "type": "message",
            "id": "msg123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            + "Z",
            "from": {"id": "user123", "name": "Test User"},
            "conversation": {"id": "conv123", "conversationType": "personal"},
            "text": "help",
        }

        response = bot.handle_activity(activity_data)

        assert response is not None
        assert "text" in response
        assert "Commands" in response["text"]

    def test_handle_conversation_update(self):
        """Test handling conversation update"""
        bot = TeamsBot("app-id", "password")

        activity_data = {
            "type": "conversationUpdate",
            "id": "update123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            + "Z",
            "from": {"id": "bot123", "name": "Bot"},
            "conversation": {"id": "conv123", "conversationType": "personal"},
        }

        response = bot.handle_activity(activity_data)

        assert response is not None
        assert "text" in response
        assert "Welcome" in response["text"]

    def test_send_message(self):
        """Test sending message"""
        bot = TeamsBot("app-id", "password")

        result = bot.send_message(conversation_id="conv123", text="Hello, World!")

        assert result is True

        # Check activity log
        analytics = bot.get_analytics()
        assert analytics["total_activities"] > 0

    def test_send_gif_card(self):
        """Test sending GIF card"""
        bot = TeamsBot("app-id", "password")

        result = bot.send_gif_card(
            conversation_id="conv123",
            gif_url="https://example.com/cat.gif",
            title="Cute Cat",
            description="A cat",
            share_url="https://gifdist.io/s/abc123",
        )

        assert result is True

    def test_custom_message_handler(self):
        """Test registering custom message handler"""
        bot = TeamsBot("app-id", "password")

        handled = []

        def custom_handler(activity: TeamsActivity):
            handled.append(activity.text)
            if activity.text and "test" in activity.text.lower():
                return {"type": "message", "text": "Custom response"}
            return None

        bot.on_message(custom_handler)

        activity_data = {
            "type": "message",
            "id": "msg123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            + "Z",
            "from": {"id": "user123", "name": "Test User"},
            "conversation": {"id": "conv123", "conversationType": "personal"},
            "text": "test message",
        }

        response = bot.handle_activity(activity_data)

        assert len(handled) == 1
        assert response is not None
        assert response["text"] == "Custom response"

    def test_conversation_state(self):
        """Test conversation state management"""
        bot = TeamsBot("app-id", "password")

        activity_data = {
            "type": "message",
            "id": "msg123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            + "Z",
            "from": {"id": "user123", "name": "Test User"},
            "conversation": {"id": "conv123", "conversationType": "personal"},
            "text": "hello",
        }

        bot.handle_activity(activity_data)

        # Get conversation state
        state = bot.get_conversation_state("conv123")

        assert state is not None
        assert state["id"] == "conv123"
        assert state["type"] == "personal"
        assert len(state["messages"]) == 1
        assert state["messages"][0]["text"] == "hello"

    def test_get_analytics(self):
        """Test analytics"""
        bot = TeamsBot("app-id", "password")

        # Send some messages
        bot.send_message("conv1", "Message 1")
        bot.send_message("conv2", "Message 2")

        # Handle some activities
        activity_data = {
            "type": "message",
            "id": "msg123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            + "Z",
            "from": {"id": "user1", "name": "User 1"},
            "conversation": {"id": "conv1", "conversationType": "personal"},
            "text": "hello",
        }
        bot.handle_activity(activity_data)

        analytics = bot.get_analytics()

        assert analytics["total_activities"] >= 3
        assert analytics["total_conversations"] >= 1
        assert "activity_types" in analytics
        assert analytics["active_users"] >= 1

    def test_oauth_card_response(self):
        """Test OAuth card creation"""
        bot = TeamsBot("app-id", "password")

        response = bot._create_oauth_card_response()

        assert "attachments" in response
        assert len(response["attachments"]) == 1

        card = response["attachments"][0]["content"]
        assert card["type"] == "AdaptiveCard"
        assert "actions" in card
        assert card["actions"][0]["type"] == "Action.OpenUrl"

    def test_help_response(self):
        """Test help response"""
        bot = TeamsBot("app-id", "password")

        response = bot._create_help_response()

        assert "text" in response
        assert "Commands" in response["text"]
        assert "help" in response["text"]

    def test_welcome_response(self):
        """Test welcome response"""
        bot = TeamsBot("app-id", "password")

        response = bot._create_welcome_response()

        assert "text" in response
        assert "Welcome" in response["text"]

    def test_conversation_update_handler(self):
        """Test conversation update handler"""
        bot = TeamsBot("app-id", "password")

        handled = []

        def update_handler(activity: TeamsActivity):
            handled.append(activity.type)
            return None

        bot.on_conversation_update(update_handler)

        activity_data = {
            "type": "conversationUpdate",
            "id": "update123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            + "Z",
            "from": {"id": "bot123", "name": "Bot"},
            "conversation": {"id": "conv123", "conversationType": "channel"},
        }

        bot.handle_activity(activity_data)

        assert len(handled) == 1
        assert handled[0] == ActivityType.CONVERSATION_UPDATE

    def test_multiple_conversations(self):
        """Test managing multiple conversations"""
        bot = TeamsBot("app-id", "password")

        # Create activities for different conversations
        for i in range(3):
            activity_data = {
                "type": "message",
                "id": f"msg{i}",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                + "Z",
                "from": {"id": f"user{i}", "name": f"User {i}"},
                "conversation": {"id": f"conv{i}", "conversationType": "personal"},
                "text": f"message {i}",
            }
            bot.handle_activity(activity_data)

        analytics = bot.get_analytics()
        assert analytics["total_conversations"] == 3

        # Each conversation should have state
        for i in range(3):
            state = bot.get_conversation_state(f"conv{i}")
            assert state is not None
            assert state["id"] == f"conv{i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
