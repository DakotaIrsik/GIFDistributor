"""
GIPHY Publisher Module for GIF Distributor
Provides channel management and programmatic upload integration with GIPHY API
Issue: #12
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import time


class GiphyContentRating(Enum):
    """Content rating levels for GIPHY uploads"""

    G = "g"  # General audiences, safe for all
    PG = "pg"  # Parental guidance suggested
    PG13 = "pg-13"  # Parents strongly cautioned
    R = "r"  # Restricted (not supported in SFW-only mode)


class GiphyChannelType(Enum):
    """GIPHY channel types"""

    BRAND = "brand"  # Brand/official channel
    ARTIST = "artist"  # Artist/creator channel
    COMMUNITY = "community"  # Community channel


@dataclass
class GiphyUploadMetadata:
    """Metadata for a GIPHY upload"""

    media_url: str
    title: str
    tags: List[str]
    source_url: Optional[str] = None
    content_rating: GiphyContentRating = GiphyContentRating.G
    channel_id: Optional[str] = None
    is_hidden: bool = False
    is_private: bool = False


@dataclass
class GiphyChannel:
    """GIPHY channel configuration"""

    channel_id: str
    display_name: str
    channel_type: GiphyChannelType
    slug: str
    description: Optional[str] = None
    banner_image_url: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_verified: bool = False


@dataclass
class GiphyUploadResult:
    """Result of a GIPHY upload operation"""

    success: bool
    giphy_id: Optional[str] = None
    giphy_url: Optional[str] = None
    embed_url: Optional[str] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None


class GiphyPublisher:
    """
    Handles publishing GIFs to GIPHY via their Upload API

    This module implements the GIPHY Upload flow:
    1. Authenticate with API key
    2. Optionally create/configure channels
    3. Upload media with metadata (title, tags, rating)
    4. Handle response and track upload status
    """

    def __init__(
        self,
        api_key: str,
        username: str,
        base_url: str = "https://upload.giphy.com/v1",
        sfw_only: bool = True,
    ):
        """
        Initialize GIPHY publisher

        Args:
            api_key: GIPHY API key (from developer dashboard)
            username: GIPHY username/account
            base_url: GIPHY API base URL
            sfw_only: If True, only allow G/PG ratings (default: True)
        """
        self.api_key = api_key
        self.username = username
        self.base_url = base_url.rstrip("/")
        self.sfw_only = sfw_only
        self.app_name = "GIFDistributor"
        self.channels: Dict[str, GiphyChannel] = {}

    def validate_metadata(
        self, metadata: GiphyUploadMetadata
    ) -> tuple[bool, Optional[str]]:
        """
        Validate upload metadata before submission

        Args:
            metadata: Upload metadata to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check media URL
        if not metadata.media_url or not metadata.media_url.startswith("http"):
            return False, "Invalid media URL"

        # Check title
        if not metadata.title or len(metadata.title.strip()) == 0:
            return False, "Title is required"

        if len(metadata.title) > 140:
            return False, "Title must be 140 characters or less"

        # Check tags
        if not metadata.tags or len(metadata.tags) == 0:
            return False, "At least one tag is required"

        if len(metadata.tags) > 25:
            return False, "Maximum 25 tags allowed"

        # Validate tag content
        for tag in metadata.tags:
            if not tag or len(tag.strip()) == 0:
                return False, "Empty tags are not allowed"
            if len(tag) > 50:
                return False, f"Tag '{tag}' exceeds 50 character limit"

        # Check content rating for SFW-only mode
        if self.sfw_only and metadata.content_rating not in [
            GiphyContentRating.G,
            GiphyContentRating.PG,
        ]:
            return False, "Only G or PG rated content is allowed in SFW-only mode"

        # Validate channel if specified
        if metadata.channel_id and metadata.channel_id not in self.channels:
            return False, f"Channel '{metadata.channel_id}' not found"

        return True, None

    def sanitize_tags(self, tags: List[str]) -> List[str]:
        """
        Sanitize and normalize tags for GIPHY

        Args:
            tags: List of tags to sanitize

        Returns:
            Sanitized list of tags
        """
        sanitized = []
        seen = set()

        for tag in tags:
            # Strip whitespace
            tag = tag.strip()

            # Skip empty tags
            if not tag:
                continue

            # Convert to lowercase for deduplication
            tag_lower = tag.lower()

            # Skip duplicates
            if tag_lower in seen:
                continue

            # GIPHY tags are typically lowercase with hyphens
            tag = tag_lower.replace(" ", "-")

            seen.add(tag)
            sanitized.append(tag)

        return sanitized

    def create_channel(self, channel: GiphyChannel) -> bool:
        """
        Create/register a GIPHY channel

        Args:
            channel: Channel configuration

        Returns:
            True if successful, False otherwise
        """
        # Validate channel data
        if not channel.channel_id or not channel.display_name:
            return False

        # Store channel configuration
        self.channels[channel.channel_id] = channel
        return True

    def get_channel(self, channel_id: str) -> Optional[GiphyChannel]:
        """
        Get channel by ID

        Args:
            channel_id: Channel identifier

        Returns:
            GiphyChannel if found, None otherwise
        """
        return self.channels.get(channel_id)

    def list_channels(self) -> List[GiphyChannel]:
        """
        List all configured channels

        Returns:
            List of GiphyChannel objects
        """
        return list(self.channels.values())

    def build_upload_payload(self, metadata: GiphyUploadMetadata) -> Dict:
        """
        Build the upload payload for GIPHY API

        Args:
            metadata: Upload metadata

        Returns:
            Dictionary containing the upload payload
        """
        payload = {
            "source_image_url": metadata.media_url,
            "title": metadata.title.strip(),
            "tags": ",".join(self.sanitize_tags(metadata.tags)),
            "rating": metadata.content_rating.value,
            "api_key": self.api_key,
            "username": self.username,
        }

        # Add optional fields
        if metadata.source_url:
            payload["source_post_url"] = metadata.source_url

        if metadata.channel_id:
            payload["channel_id"] = metadata.channel_id

        if metadata.is_hidden:
            payload["is_hidden"] = "true"

        if metadata.is_private:
            payload["is_private"] = "true"

        return payload

    def upload(self, metadata: GiphyUploadMetadata) -> GiphyUploadResult:
        """
        Upload a GIF to GIPHY

        Args:
            metadata: Upload metadata

        Returns:
            GiphyUploadResult with upload status
        """
        # Validate metadata
        is_valid, error_msg = self.validate_metadata(metadata)
        if not is_valid:
            return GiphyUploadResult(
                success=False, error_message=f"Validation failed: {error_msg}"
            )

        # Build payload
        payload = self.build_upload_payload(metadata)

        # In a real implementation, this would call the GIPHY API
        # For now, we'll simulate a successful upload

        # Generate a mock GIPHY ID
        giphy_id = self._generate_mock_id(metadata.media_url)
        giphy_url = f"https://giphy.com/gifs/{giphy_id}"
        embed_url = f"https://giphy.com/embed/{giphy_id}"

        return GiphyUploadResult(
            success=True,
            giphy_id=giphy_id,
            giphy_url=giphy_url,
            embed_url=embed_url,
            status_code=200,
        )

    def _generate_mock_id(self, media_url: str) -> str:
        """
        Generate a mock GIPHY ID for testing

        Args:
            media_url: URL to generate ID from

        Returns:
            Mock GIPHY ID
        """
        # Create a hash-based ID similar to GIPHY's format
        hash_input = f"{media_url}{time.time()}".encode("utf-8")
        hash_value = hashlib.sha256(hash_input).hexdigest()[:16]
        return hash_value

    def check_upload_status(self, giphy_id: str) -> Dict:
        """
        Check the status of an upload

        Args:
            giphy_id: GIPHY ID to check

        Returns:
            Dictionary with status information
        """
        # Mock implementation
        return {
            "giphy_id": giphy_id,
            "status": "published",
            "url": f"https://giphy.com/gifs/{giphy_id}",
            "views": 0,
            "favorites": 0,
            "import_datetime": time.time(),
        }

    def generate_giphy_search_url(self, tags: List[str], limit: int = 10) -> str:
        """
        Generate a GIPHY search URL for verification

        Args:
            tags: Tags to search for
            limit: Maximum results to return

        Returns:
            GIPHY search URL
        """
        search_query = " ".join(tags)
        return f"https://giphy.com/search/{search_query.replace(' ', '-')}"

    def format_tags_for_giphy(
        self, tags: List[str], include_platform_tags: bool = True
    ) -> List[str]:
        """
        Format tags specifically for GIPHY's tagging system

        Args:
            tags: Original tags
            include_platform_tags: Whether to add platform-specific tags

        Returns:
            Formatted tags list
        """
        formatted_tags = self.sanitize_tags(tags)

        if include_platform_tags:
            # Add platform identifier tag
            formatted_tags.append(f"via-{self.app_name.lower()}")

        return formatted_tags

    def estimate_tag_reach(self, tags: List[str]) -> Dict[str, int]:
        """
        Estimate the potential reach of given tags on GIPHY

        Args:
            tags: Tags to analyze

        Returns:
            Dictionary with estimated metrics
        """
        # Mock implementation - in reality would query GIPHY analytics
        total_searches = sum(hash(tag) % 15000 for tag in tags)

        return {
            "estimated_monthly_searches": total_searches,
            "competition_level": "high",
            "recommended_tags": ["reaction", "sticker", "animated"],
            "tag_count": len(tags),
        }

    def batch_upload(
        self, uploads: List[GiphyUploadMetadata]
    ) -> List[GiphyUploadResult]:
        """
        Upload multiple GIFs in batch

        Args:
            uploads: List of upload metadata

        Returns:
            List of upload results
        """
        results = []

        for metadata in uploads:
            result = self.upload(metadata)
            results.append(result)

        return results

    def get_user_stats(self) -> Dict:
        """
        Get statistics for the user account

        Returns:
            Dictionary with user statistics
        """
        # Mock implementation
        return {
            "username": self.username,
            "total_uploads": 0,
            "total_views": 0,
            "total_favorites": 0,
            "follower_count": 0,
            "channel_count": len(self.channels),
            "top_tags": [],
            "upload_limit_remaining": 5000,
        }

    def get_channel_stats(self, channel_id: str) -> Optional[Dict]:
        """
        Get statistics for a specific channel

        Args:
            channel_id: Channel identifier

        Returns:
            Dictionary with channel statistics, or None if channel not found
        """
        channel = self.get_channel(channel_id)
        if not channel:
            return None

        # Mock implementation
        return {
            "channel_id": channel_id,
            "display_name": channel.display_name,
            "total_gifs": 0,
            "total_views": 0,
            "total_favorites": 0,
            "follower_count": 0,
            "is_verified": channel.is_verified,
            "top_performing_gifs": [],
        }

    def update_gif_metadata(
        self,
        giphy_id: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Update metadata for an existing GIF

        Args:
            giphy_id: GIPHY ID to update
            title: New title (optional)
            tags: New tags (optional)

        Returns:
            True if successful, False otherwise
        """
        # Mock implementation - would call GIPHY update API
        if not giphy_id:
            return False

        # In real implementation, validate and send update request
        return True

    def delete_gif(self, giphy_id: str) -> bool:
        """
        Delete a GIF from GIPHY

        Args:
            giphy_id: GIPHY ID to delete

        Returns:
            True if successful, False otherwise
        """
        # Mock implementation - would call GIPHY delete API
        if not giphy_id:
            return False

        # In real implementation, send delete request
        return True

    def get_trending_tags(self, limit: int = 10) -> List[str]:
        """
        Get currently trending tags on GIPHY

        Args:
            limit: Maximum number of tags to return

        Returns:
            List of trending tags
        """
        # Mock implementation - would call GIPHY trending API
        return [
            "reaction",
            "funny",
            "love",
            "happy",
            "birthday",
            "excited",
            "thumbs-up",
            "dancing",
            "celebrate",
            "wow",
        ][:limit]

    def search_similar_gifs(self, giphy_id: str, limit: int = 5) -> List[Dict]:
        """
        Find similar GIFs to a given GIF

        Args:
            giphy_id: GIPHY ID to find similar GIFs for
            limit: Maximum results to return

        Returns:
            List of similar GIF metadata
        """
        # Mock implementation
        return [
            {
                "giphy_id": f"similar-{i}",
                "title": f"Similar GIF {i}",
                "url": f"https://giphy.com/gifs/similar-{i}",
            }
            for i in range(limit)
        ]
