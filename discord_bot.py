"""
Discord Bot OAuth2 Integration

Issue #9: Discord bot: OAuth2 + send embed/attachment

This module provides OAuth2 authentication for Discord and
the ability to send embeds/attachments to Discord channels.
"""

import os
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlencode


class DiscordOAuth2:
    """
    Discord OAuth2 authentication handler
    """

    def __init__(self):
        self.client_id = os.getenv('DISCORD_CLIENT_ID')
        self.client_secret = os.getenv('DISCORD_CLIENT_SECRET')
        self.redirect_uri = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:3000/auth/discord/callback')

        self.oauth_url = 'https://discord.com/api/oauth2/authorize'
        self.token_url = 'https://discord.com/api/oauth2/token'
        self.api_base = 'https://discord.com/api/v10'

    def get_authorization_url(self, state: Optional[str] = None, scopes: Optional[list] = None) -> str:
        """
        Generate Discord OAuth2 authorization URL

        Args:
            state: CSRF protection state parameter
            scopes: List of OAuth2 scopes (default: ['identify', 'guilds'])

        Returns:
            Authorization URL for redirecting users
        """
        if scopes is None:
            scopes = ['identify', 'guilds', 'webhook.incoming']

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scopes)
        }

        if state:
            params['state'] = state

        return f"{self.oauth_url}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from OAuth2 callback

        Returns:
            Token response containing access_token, refresh_token, etc.
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(self.token_url, data=data, headers=headers)
        response.raise_for_status()

        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token

        Args:
            refresh_token: Refresh token from previous token exchange

        Returns:
            New token response
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(self.token_url, data=data, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get authenticated user information

        Args:
            access_token: User's access token

        Returns:
            User information from Discord API
        """
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(f'{self.api_base}/users/@me', headers=headers)
        response.raise_for_status()

        return response.json()

    def get_user_guilds(self, access_token: str) -> list:
        """
        Get list of guilds (servers) the user is in

        Args:
            access_token: User's access token

        Returns:
            List of guild objects
        """
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(f'{self.api_base}/users/@me/guilds', headers=headers)
        response.raise_for_status()

        return response.json()


class DiscordMessenger:
    """
    Discord message and embed sender
    """

    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Discord messenger

        Args:
            bot_token: Discord bot token (optional, can also use OAuth tokens)
        """
        self.bot_token = bot_token or os.getenv('DISCORD_BOT_TOKEN')
        self.api_base = 'https://discord.com/api/v10'

    def send_embed(
        self,
        channel_id: str,
        embed: Dict[str, Any],
        access_token: Optional[str] = None,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an embed to a Discord channel

        Args:
            channel_id: Discord channel ID
            embed: Embed object (Discord embed format)
            access_token: OAuth access token (if not using bot token)
            content: Optional message content

        Returns:
            Response from Discord API
        """
        # Determine which token to use
        token = access_token or self.bot_token
        auth_header = f'Bearer {token}' if access_token else f'Bot {self.bot_token}'

        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }

        payload = {
            'embeds': [embed]
        }

        if content:
            payload['content'] = content

        url = f'{self.api_base}/channels/{channel_id}/messages'
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

    def send_attachment(
        self,
        channel_id: str,
        file_url: str,
        filename: str,
        access_token: Optional[str] = None,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an attachment to a Discord channel

        Args:
            channel_id: Discord channel ID
            file_url: URL of the file to attach (GIF, image, etc.)
            filename: Name of the file
            access_token: OAuth access token (if not using bot token)
            content: Optional message content

        Returns:
            Response from Discord API
        """
        # Download the file
        file_response = requests.get(file_url)
        file_response.raise_for_status()

        # Determine which token to use
        token = access_token or self.bot_token
        auth_header = f'Bearer {token}' if access_token else f'Bot {self.bot_token}'

        headers = {
            'Authorization': auth_header
        }

        # Prepare multipart form data
        files = {
            'file': (filename, file_response.content)
        }

        data = {}
        if content:
            data['content'] = content

        url = f'{self.api_base}/channels/{channel_id}/messages'
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()

        return response.json()

    def create_embed(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
        color: Optional[int] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Discord embed object

        Args:
            title: Embed title
            description: Embed description
            url: URL for the title link
            color: Embed color (integer)
            image_url: URL for main image
            thumbnail_url: URL for thumbnail
            footer_text: Footer text
            author_name: Author name

        Returns:
            Discord embed object
        """
        embed: Dict[str, Any] = {}

        if title:
            embed['title'] = title
        if description:
            embed['description'] = description
        if url:
            embed['url'] = url
        if color:
            embed['color'] = color
        else:
            embed['color'] = 5814783  # Discord blurple default

        if image_url:
            embed['image'] = {'url': image_url}
        if thumbnail_url:
            embed['thumbnail'] = {'url': thumbnail_url}
        if footer_text:
            embed['footer'] = {'text': footer_text}
        if author_name:
            embed['author'] = {'name': author_name}

        return embed

    def send_gif_embed(
        self,
        channel_id: str,
        gif_url: str,
        title: str,
        description: Optional[str] = None,
        source_url: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a GIF as an embed to a Discord channel

        Args:
            channel_id: Discord channel ID
            gif_url: URL of the GIF
            title: Title for the embed
            description: Optional description
            source_url: Optional source URL for the GIF
            access_token: OAuth access token (if not using bot token)

        Returns:
            Response from Discord API
        """
        embed = self.create_embed(
            title=title,
            description=description,
            url=source_url,
            image_url=gif_url,
            footer_text='Powered by GIF Distributor'
        )

        return self.send_embed(channel_id, embed, access_token)


# Example usage
if __name__ == '__main__':
    # OAuth2 flow example
    oauth = DiscordOAuth2()

    # Step 1: Get authorization URL
    auth_url = oauth.get_authorization_url(state='random_state_123')
    print(f'Authorization URL: {auth_url}')

    # Step 2: After user authorizes, exchange code for token
    # code = 'authorization_code_from_callback'
    # token_data = oauth.exchange_code_for_token(code)
    # access_token = token_data['access_token']

    # Step 3: Get user info
    # user_info = oauth.get_user_info(access_token)
    # print(f'User: {user_info["username"]}')

    # Messaging example
    messenger = DiscordMessenger()

    # Create an embed for a GIF
    # messenger.send_gif_embed(
    #     channel_id='1234567890',
    #     gif_url='https://example.com/awesome.gif',
    #     title='Awesome GIF!',
    #     description='Check out this cool GIF'
    # )
