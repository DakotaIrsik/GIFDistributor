"""
Microsoft Teams Message Extension for GIF Distribution

Provides Teams integration with:
- Message extension (search + compose)
- Adaptive cards with playable MP4/GIF
- Link unfurling
- OAuth 2.0 authentication
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import time
import hashlib
import hmac


class MessageExtensionType(Enum):
    """Types of message extension commands"""
    SEARCH = "search"
    COMPOSE = "compose"
    ACTION = "action"


class CardType(Enum):
    """Adaptive card types"""
    PREVIEW = "preview"
    FULL = "full"
    HERO = "hero"


@dataclass
class TeamsAttachment:
    """Teams adaptive card attachment"""
    content_type: str
    content: Dict[str, Any]
    preview: Optional[Dict[str, Any]] = None


@dataclass
class TeamsMessageExtensionResult:
    """Result from message extension query"""
    attachment_layout: str = "list"  # "list" or "grid"
    attachments: List[TeamsAttachment] = field(default_factory=list)
    type: str = "result"


@dataclass
class GIFCard:
    """GIF card data for Teams"""
    asset_id: str
    title: str
    mp4_url: str
    gif_url: str
    thumbnail_url: str
    canonical_url: str
    short_url: str
    file_size: int
    width: int
    height: int
    duration_ms: int
    tags: List[str] = field(default_factory=list)
    description: str = ""


class AdaptiveCardBuilder:
    """Builder for Teams adaptive cards"""

    @staticmethod
    def create_gif_card(gif: GIFCard, card_type: CardType = CardType.FULL) -> Dict[str, Any]:
        """
        Create an adaptive card for a GIF

        Args:
            gif: GIF card data
            card_type: Type of card to create

        Returns:
            Adaptive card JSON
        """
        if card_type == CardType.PREVIEW:
            return AdaptiveCardBuilder._create_preview_card(gif)
        elif card_type == CardType.HERO:
            return AdaptiveCardBuilder._create_hero_card(gif)
        else:
            return AdaptiveCardBuilder._create_full_card(gif)

    @staticmethod
    def _create_preview_card(gif: GIFCard) -> Dict[str, Any]:
        """Create a compact preview card"""
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "Image",
                                    "url": gif.thumbnail_url,
                                    "size": "Small",
                                    "width": "60px"
                                }
                            ]
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": gif.title,
                                    "weight": "Bolder",
                                    "wrap": True
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"{gif.width}x{gif.height} • {gif.duration_ms/1000:.1f}s",
                                    "size": "Small",
                                    "color": "Accent",
                                    "spacing": "None"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def _create_hero_card(gif: GIFCard) -> Dict[str, Any]:
        """Create a hero card (compatible with older Teams clients)"""
        return {
            "contentType": "application/vnd.microsoft.card.hero",
            "content": {
                "title": gif.title,
                "subtitle": f"{gif.width}x{gif.height} • {gif.duration_ms/1000:.1f}s",
                "text": gif.description if gif.description else None,
                "images": [
                    {"url": gif.thumbnail_url}
                ],
                "buttons": [
                    {
                        "type": "openUrl",
                        "title": "View GIF",
                        "value": gif.canonical_url
                    },
                    {
                        "type": "openUrl",
                        "title": "Share",
                        "value": gif.short_url
                    }
                ]
            }
        }

    @staticmethod
    def _create_full_card(gif: GIFCard) -> Dict[str, Any]:
        """Create a full adaptive card with playable media"""
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": gif.title,
                    "weight": "Bolder",
                    "size": "Large",
                    "wrap": True
                },
                {
                    "type": "Media",
                    "poster": gif.thumbnail_url,
                    "sources": [
                        {
                            "mimeType": "video/mp4",
                            "url": gif.mp4_url
                        }
                    ],
                    "altText": gif.title
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Dimensions:",
                            "value": f"{gif.width}x{gif.height}"
                        },
                        {
                            "title": "Duration:",
                            "value": f"{gif.duration_ms/1000:.1f}s"
                        },
                        {
                            "title": "Size:",
                            "value": AdaptiveCardBuilder._format_file_size(gif.file_size)
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Original",
                    "url": gif.canonical_url
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "Copy Share Link",
                    "url": gif.short_url
                }
            ]
        }

        # Add tags if available
        if gif.tags:
            card["body"].append({
                "type": "TextBlock",
                "text": " ".join([f"`{tag}`" for tag in gif.tags[:5]]),
                "size": "Small",
                "color": "Accent",
                "wrap": True
            })

        # Add description if available
        if gif.description:
            card["body"].insert(1, {
                "type": "TextBlock",
                "text": gif.description,
                "wrap": True,
                "spacing": "Small"
            })

        return card

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"


class TeamsMessageExtension:
    """
    Microsoft Teams Message Extension

    Handles search queries, compose extensions, and adaptive card creation
    for GIF distribution in Teams.
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        bot_endpoint: str = "",
        enable_link_unfurling: bool = True
    ):
        """
        Initialize Teams message extension

        Args:
            app_id: Microsoft App ID
            app_secret: Microsoft App Secret
            bot_endpoint: Bot endpoint URL for callbacks
            enable_link_unfurling: Enable automatic link unfurling
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.bot_endpoint = bot_endpoint
        self.enable_link_unfurling = enable_link_unfurling

        # Storage for GIF data (in production, use database)
        self._gif_registry: Dict[str, GIFCard] = {}

        # Activity tracking
        self._search_queries: List[Dict[str, Any]] = []
        self._card_interactions: List[Dict[str, Any]] = []

    def register_gif(self, gif: GIFCard) -> bool:
        """
        Register a GIF for use in the message extension

        Args:
            gif: GIF card data to register

        Returns:
            True if registered successfully
        """
        if not gif.asset_id:
            return False

        self._gif_registry[gif.asset_id] = gif
        return True

    def handle_search_query(
        self,
        query: str,
        limit: int = 10,
        context: Optional[Dict[str, Any]] = None
    ) -> TeamsMessageExtensionResult:
        """
        Handle a search query from Teams message extension

        Args:
            query: Search query string
            limit: Maximum number of results
            context: Additional context (user, channel, etc.)

        Returns:
            Message extension result with cards
        """
        # Track the search query
        self._search_queries.append({
            "query": query,
            "timestamp": time.time(),
            "context": context or {}
        })

        # Search for matching GIFs
        matching_gifs = self._search_gifs(query, limit)

        # Create attachments
        attachments = []
        for gif in matching_gifs:
            # Create preview and full cards
            preview_card = AdaptiveCardBuilder.create_gif_card(gif, CardType.PREVIEW)
            full_card = AdaptiveCardBuilder.create_gif_card(gif, CardType.FULL)

            attachment = TeamsAttachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=full_card,
                preview={
                    "content": preview_card,
                    "contentType": "application/vnd.microsoft.card.adaptive"
                }
            )
            attachments.append(attachment)

        return TeamsMessageExtensionResult(
            attachment_layout="grid" if len(matching_gifs) > 1 else "list",
            attachments=attachments
        )

    def _search_gifs(self, query: str, limit: int) -> List[GIFCard]:
        """
        Search for GIFs matching query

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching GIF cards
        """
        query_lower = query.lower()
        results = []

        for gif in self._gif_registry.values():
            # Match on title, description, or tags
            if (query_lower in gif.title.lower() or
                query_lower in gif.description.lower() or
                any(query_lower in tag.lower() for tag in gif.tags)):
                results.append(gif)

                if len(results) >= limit:
                    break

        return results

    def get_gif_card(
        self,
        asset_id: str,
        card_type: CardType = CardType.FULL
    ) -> Optional[Dict[str, Any]]:
        """
        Get adaptive card for a specific GIF

        Args:
            asset_id: Asset ID
            card_type: Type of card to create

        Returns:
            Adaptive card JSON or None if not found
        """
        gif = self._gif_registry.get(asset_id)
        if not gif:
            return None

        return AdaptiveCardBuilder.create_gif_card(gif, card_type)

    def unfurl_link(self, url: str) -> Optional[TeamsAttachment]:
        """
        Create card for link unfurling

        Args:
            url: URL to unfurl

        Returns:
            Teams attachment or None if URL not recognized
        """
        if not self.enable_link_unfurling:
            return None

        # Extract asset ID from URL
        asset_id = self._extract_asset_id(url)
        if not asset_id:
            return None

        gif = self._gif_registry.get(asset_id)
        if not gif:
            return None

        # Create card for unfurling
        card = AdaptiveCardBuilder.create_gif_card(gif, CardType.FULL)

        return TeamsAttachment(
            content_type="application/vnd.microsoft.card.adaptive",
            content=card
        )

    def _extract_asset_id(self, url: str) -> Optional[str]:
        """
        Extract asset ID from URL

        Args:
            url: URL to parse

        Returns:
            Asset ID or None
        """
        # Simple extraction - in production, use proper URL parsing
        for asset_id in self._gif_registry.keys():
            if asset_id in url:
                return asset_id
        return None

    def track_card_interaction(
        self,
        asset_id: str,
        interaction_type: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track card interaction for analytics

        Args:
            asset_id: Asset ID
            interaction_type: Type of interaction (view, click, share)
            user_id: User who interacted
            metadata: Additional metadata
        """
        self._card_interactions.append({
            "asset_id": asset_id,
            "interaction_type": interaction_type,
            "user_id": user_id,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })

    def get_analytics(self) -> Dict[str, Any]:
        """
        Get analytics data for the message extension

        Returns:
            Analytics summary
        """
        return {
            "total_gifs": len(self._gif_registry),
            "total_searches": len(self._search_queries),
            "total_interactions": len(self._card_interactions),
            "popular_queries": self._get_popular_queries(),
            "popular_gifs": self._get_popular_gifs()
        }

    def _get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular search queries"""
        query_counts: Dict[str, int] = {}
        for search in self._search_queries:
            query = search["query"]
            query_counts[query] = query_counts.get(query, 0) + 1

        sorted_queries = sorted(
            query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [{"query": q, "count": c} for q, c in sorted_queries]

    def _get_popular_gifs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular GIFs by interaction count"""
        gif_counts: Dict[str, int] = {}
        for interaction in self._card_interactions:
            asset_id = interaction["asset_id"]
            gif_counts[asset_id] = gif_counts.get(asset_id, 0) + 1

        sorted_gifs = sorted(
            gif_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [{"asset_id": g, "interactions": c} for g, c in sorted_gifs]

    def verify_request_signature(
        self,
        payload: str,
        signature: str
    ) -> bool:
        """
        Verify Teams request signature for security

        Args:
            payload: Request payload
            signature: HMAC signature from Teams

        Returns:
            True if signature is valid
        """
        expected_signature = hmac.new(
            self.app_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def create_compose_extension_response(
        self,
        gif: GIFCard
    ) -> Dict[str, Any]:
        """
        Create response for compose extension

        Args:
            gif: GIF to include in response

        Returns:
            Compose extension response
        """
        card = AdaptiveCardBuilder.create_gif_card(gif, CardType.FULL)

        return {
            "composeExtension": {
                "type": "result",
                "attachmentLayout": "list",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": card
                    }
                ]
            }
        }

    def get_registered_gifs(self) -> List[GIFCard]:
        """
        Get all registered GIFs

        Returns:
            List of all registered GIF cards
        """
        return list(self._gif_registry.values())

    def clear_registry(self):
        """Clear all registered GIFs"""
        self._gif_registry.clear()

    def clear_analytics(self):
        """Clear analytics data"""
        self._search_queries.clear()
        self._card_interactions.clear()
