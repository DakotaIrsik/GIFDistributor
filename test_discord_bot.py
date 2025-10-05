"""
Tests for Discord Bot OAuth2 Integration

Issue #9: Discord bot: OAuth2 + send embed/attachment
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import os
from discord_bot import DiscordOAuth2, DiscordMessenger


class TestDiscordOAuth2(unittest.TestCase):
    """Test Discord OAuth2 functionality"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ["DISCORD_CLIENT_ID"] = "test_client_id"
        os.environ["DISCORD_CLIENT_SECRET"] = "test_client_secret"
        os.environ["DISCORD_REDIRECT_URI"] = "http://localhost:3000/callback"
        self.oauth = DiscordOAuth2()

    def test_get_authorization_url(self):
        """Test OAuth2 authorization URL generation"""
        url = self.oauth.get_authorization_url(state="test_state")

        self.assertIn("client_id=test_client_id", url)
        self.assertIn("redirect_uri=http", url)
        self.assertIn("state=test_state", url)
        self.assertIn("response_type=code", url)

    def test_authorization_url_with_custom_scopes(self):
        """Test authorization URL with custom scopes"""
        url = self.oauth.get_authorization_url(scopes=["identify", "email"])

        self.assertIn("scope=identify+email", url)

    @patch("discord_bot.requests.post")
    def test_exchange_code_for_token(self, mock_post):
        """Test exchanging authorization code for token"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 604800,
            "refresh_token": "test_refresh_token",
            "scope": "identify guilds",
        }
        mock_post.return_value = mock_response

        result = self.oauth.exchange_code_for_token("test_code")

        self.assertEqual(result["access_token"], "test_access_token")
        self.assertEqual(result["refresh_token"], "test_refresh_token")

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["data"]["code"], "test_code")
        self.assertEqual(call_kwargs["data"]["grant_type"], "authorization_code")

    @patch("discord_bot.requests.post")
    def test_refresh_access_token(self, mock_post):
        """Test refreshing access token"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 604800,
            "refresh_token": "new_refresh_token",
            "scope": "identify guilds",
        }
        mock_post.return_value = mock_response

        result = self.oauth.refresh_access_token("old_refresh_token")

        self.assertEqual(result["access_token"], "new_access_token")

        # Verify the request
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(call_kwargs["data"]["refresh_token"], "old_refresh_token")

    @patch("discord_bot.requests.get")
    def test_get_user_info(self, mock_get):
        """Test getting user information"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "123456789",
            "username": "testuser",
            "discriminator": "1234",
            "avatar": "avatar_hash",
        }
        mock_get.return_value = mock_response

        result = self.oauth.get_user_info("test_access_token")

        self.assertEqual(result["username"], "testuser")
        self.assertEqual(result["id"], "123456789")

        # Verify authorization header
        call_kwargs = mock_get.call_args[1]
        self.assertEqual(
            call_kwargs["headers"]["Authorization"], "Bearer test_access_token"
        )

    @patch("discord_bot.requests.get")
    def test_get_user_guilds(self, mock_get):
        """Test getting user's guilds"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "111", "name": "Guild 1"},
            {"id": "222", "name": "Guild 2"},
        ]
        mock_get.return_value = mock_response

        result = self.oauth.get_user_guilds("test_access_token")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Guild 1")


class TestDiscordMessenger(unittest.TestCase):
    """Test Discord messaging functionality"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ["DISCORD_BOT_TOKEN"] = "test_bot_token"
        self.messenger = DiscordMessenger()

    def test_create_embed_basic(self):
        """Test creating a basic embed"""
        embed = self.messenger.create_embed(
            title="Test Title", description="Test Description"
        )

        self.assertEqual(embed["title"], "Test Title")
        self.assertEqual(embed["description"], "Test Description")
        self.assertEqual(embed["color"], 5814783)  # Discord blurple

    def test_create_embed_with_image(self):
        """Test creating embed with image"""
        embed = self.messenger.create_embed(
            title="Image Test",
            image_url="https://example.com/image.gif",
            thumbnail_url="https://example.com/thumb.png",
        )

        self.assertEqual(embed["image"]["url"], "https://example.com/image.gif")
        self.assertEqual(embed["thumbnail"]["url"], "https://example.com/thumb.png")

    def test_create_embed_with_footer_and_author(self):
        """Test creating embed with footer and author"""
        embed = self.messenger.create_embed(
            title="Test", footer_text="Footer Text", author_name="Author Name"
        )

        self.assertEqual(embed["footer"]["text"], "Footer Text")
        self.assertEqual(embed["author"]["name"], "Author Name")

    @patch("discord_bot.requests.post")
    def test_send_embed_with_bot_token(self, mock_post):
        """Test sending embed with bot token"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "message_id"}
        mock_post.return_value = mock_response

        embed = {"title": "Test", "description": "Test embed"}
        result = self.messenger.send_embed("channel_123", embed)

        self.assertEqual(result["id"], "message_id")

        # Verify bot token was used
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bot test_bot_token")

    @patch("discord_bot.requests.post")
    def test_send_embed_with_oauth_token(self, mock_post):
        """Test sending embed with OAuth access token"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "message_id"}
        mock_post.return_value = mock_response

        embed = {"title": "Test", "description": "Test embed"}
        result = self.messenger.send_embed(
            "channel_123", embed, access_token="oauth_token"
        )

        # Verify OAuth token was used instead of bot token
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer oauth_token")

    @patch("discord_bot.requests.post")
    def test_send_embed_with_content(self, mock_post):
        """Test sending embed with text content"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "message_id"}
        mock_post.return_value = mock_response

        embed = {"title": "Test"}
        self.messenger.send_embed("channel_123", embed, content="Check this out!")

        # Verify content was included
        call_kwargs = mock_post.call_args[1]
        self.assertIn("content", call_kwargs["json"])
        self.assertEqual(call_kwargs["json"]["content"], "Check this out!")

    @patch("discord_bot.requests.get")
    @patch("discord_bot.requests.post")
    def test_send_attachment(self, mock_post, mock_get):
        """Test sending file attachment"""
        # Mock file download
        mock_get_response = Mock()
        mock_get_response.content = b"fake_gif_data"
        mock_get.return_value = mock_get_response

        # Mock Discord API response
        mock_post_response = Mock()
        mock_post_response.json.return_value = {"id": "message_id"}
        mock_post.return_value = mock_post_response

        result = self.messenger.send_attachment(
            "channel_123", "https://example.com/gif.gif", "awesome.gif"
        )

        self.assertEqual(result["id"], "message_id")

        # Verify file was downloaded
        mock_get.assert_called_once_with("https://example.com/gif.gif")

        # Verify attachment was sent
        call_kwargs = mock_post.call_args[1]
        self.assertIn("file", call_kwargs["files"])

    @patch("discord_bot.requests.post")
    def test_send_gif_embed(self, mock_post):
        """Test sending GIF embed"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "message_id"}
        mock_post.return_value = mock_response

        result = self.messenger.send_gif_embed(
            channel_id="channel_123",
            gif_url="https://example.com/cool.gif",
            title="Cool GIF",
            description="This is a cool GIF",
            source_url="https://example.com/source",
        )

        self.assertEqual(result["id"], "message_id")

        # Verify embed structure
        call_kwargs = mock_post.call_args[1]
        embed = call_kwargs["json"]["embeds"][0]
        self.assertEqual(embed["title"], "Cool GIF")
        self.assertEqual(embed["description"], "This is a cool GIF")
        self.assertEqual(embed["image"]["url"], "https://example.com/cool.gif")
        self.assertEqual(embed["url"], "https://example.com/source")
        self.assertEqual(embed["footer"]["text"], "Powered by GIF Distributor")


class TestIntegration(unittest.TestCase):
    """Integration tests for Discord bot"""

    @patch("discord_bot.requests.post")
    @patch("discord_bot.requests.get")
    def test_full_oauth_flow(self, mock_get, mock_post):
        """Test complete OAuth2 flow"""
        os.environ["DISCORD_CLIENT_ID"] = "client_id"
        os.environ["DISCORD_CLIENT_SECRET"] = "client_secret"

        # Step 1: Get authorization URL
        oauth = DiscordOAuth2()
        auth_url = oauth.get_authorization_url(state="csrf_token")
        self.assertIn("client_id=client_id", auth_url)

        # Step 2: Mock token exchange
        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            "access_token": "user_access_token",
            "refresh_token": "user_refresh_token",
        }
        mock_post.return_value = mock_token_response

        tokens = oauth.exchange_code_for_token("auth_code")
        self.assertEqual(tokens["access_token"], "user_access_token")

        # Step 3: Mock user info
        mock_user_response = Mock()
        mock_user_response.json.return_value = {"id": "999", "username": "testuser"}
        mock_get.return_value = mock_user_response

        user = oauth.get_user_info(tokens["access_token"])
        self.assertEqual(user["username"], "testuser")

        # Step 4: Send a message with the user's token
        messenger = DiscordMessenger()
        mock_message_response = Mock()
        mock_message_response.json.return_value = {"id": "msg_id"}
        mock_post.return_value = mock_message_response

        result = messenger.send_gif_embed(
            channel_id="123",
            gif_url="https://gif.example.com/test.gif",
            title="Test GIF",
            access_token=tokens["access_token"],
        )

        self.assertEqual(result["id"], "msg_id")


if __name__ == "__main__":
    unittest.main()
