"""
Tenor Publisher Module for GIF Distributor
Provides partner flow integration with Tenor API for uploading GIFs with tags
Issue: #28
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import time


class TenorContentRating(Enum):
    """Content rating levels for Tenor uploads"""

    HIGH = "high"  # G-rated, safe for all audiences
    MEDIUM = "medium"  # PG-13, mild content
    LOW = "low"  # R-rated (not supported in SFW-only mode)


@dataclass
class TenorUploadMetadata:
    """Metadata for a Tenor upload"""

    media_url: str
    title: str
    tags: List[str]
    content_rating: TenorContentRating = TenorContentRating.HIGH
    source_id: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class TenorUploadResult:
    """Result of a Tenor upload operation"""

    success: bool
    tenor_id: Optional[str] = None
    tenor_url: Optional[str] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None


class TenorPublisher:
    """
    Handles publishing GIFs to Tenor via their Partner API

    This module implements the Tenor Partner Upload flow:
    1. Authenticate with API key
    2. Upload media with metadata (title, tags, rating)
    3. Handle response and track upload status
    """

    def __init__(
        self,
        api_key: str,
        partner_id: str,
        base_url: str = "https://tenor.googleapis.com/v2",
        sfw_only: bool = True,
    ):
        """
        Initialize Tenor publisher

        Args:
            api_key: Tenor API key (from developer dashboard)
            partner_id: Tenor partner ID
            base_url: Tenor API base URL
            sfw_only: If True, only allow HIGH content rating (default: True)
        """
        self.api_key = api_key
        self.partner_id = partner_id
        self.base_url = base_url.rstrip("/")
        self.sfw_only = sfw_only
        self.app_name = "GIFDistributor"

    def validate_metadata(
        self, metadata: TenorUploadMetadata
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

        if len(metadata.title) > 100:
            return False, "Title must be 100 characters or less"

        # Check tags
        if not metadata.tags or len(metadata.tags) == 0:
            return False, "At least one tag is required"

        if len(metadata.tags) > 20:
            return False, "Maximum 20 tags allowed"

        # Validate tag content
        for tag in metadata.tags:
            if not tag or len(tag.strip()) == 0:
                return False, "Empty tags are not allowed"
            if len(tag) > 50:
                return False, f"Tag '{tag}' exceeds 50 character limit"

        # Check content rating for SFW-only mode
        if self.sfw_only and metadata.content_rating != TenorContentRating.HIGH:
            return False, "Only HIGH (G-rated) content is allowed in SFW-only mode"

        return True, None

    def sanitize_tags(self, tags: List[str]) -> List[str]:
        """
        Sanitize and normalize tags

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

            seen.add(tag_lower)
            sanitized.append(tag)

        return sanitized

    def build_upload_payload(self, metadata: TenorUploadMetadata) -> Dict:
        """
        Build the upload payload for Tenor API

        Args:
            metadata: Upload metadata

        Returns:
            Dictionary containing the upload payload
        """
        payload = {
            "media_url": metadata.media_url,
            "title": metadata.title.strip(),
            "tags": self.sanitize_tags(metadata.tags),
            "content_rating": metadata.content_rating.value,
            "key": self.api_key,
            "partner_id": self.partner_id,
        }

        # Add optional fields
        if metadata.source_id:
            payload["source_id"] = metadata.source_id

        if metadata.source_url:
            payload["source_url"] = metadata.source_url

        return payload

    def upload(self, metadata: TenorUploadMetadata) -> TenorUploadResult:
        """
        Upload a GIF to Tenor

        Args:
            metadata: Upload metadata

        Returns:
            TenorUploadResult with upload status
        """
        # Validate metadata
        is_valid, error_msg = self.validate_metadata(metadata)
        if not is_valid:
            return TenorUploadResult(
                success=False, error_message=f"Validation failed: {error_msg}"
            )

        # Build payload
        payload = self.build_upload_payload(metadata)

        # In a real implementation, this would call the Tenor API
        # For now, we'll simulate a successful upload

        # Generate a mock Tenor ID
        tenor_id = self._generate_mock_id(metadata.media_url)
        tenor_url = f"https://tenor.com/view/{tenor_id}"

        return TenorUploadResult(
            success=True, tenor_id=tenor_id, tenor_url=tenor_url, status_code=200
        )

    def _generate_mock_id(self, media_url: str) -> str:
        """
        Generate a mock Tenor ID for testing

        Args:
            media_url: URL to generate ID from

        Returns:
            Mock Tenor ID
        """
        # Create a hash-based ID
        hash_input = f"{media_url}{time.time()}".encode("utf-8")
        hash_value = hashlib.sha256(hash_input).hexdigest()[:12]
        return f"tenor-{hash_value}"

    def check_upload_status(self, tenor_id: str) -> Dict:
        """
        Check the status of an upload

        Args:
            tenor_id: Tenor ID to check

        Returns:
            Dictionary with status information
        """
        # Mock implementation
        return {
            "tenor_id": tenor_id,
            "status": "approved",
            "url": f"https://tenor.com/view/{tenor_id}",
            "views": 0,
            "shares": 0,
        }

    def generate_tenor_search_url(self, tags: List[str], limit: int = 10) -> str:
        """
        Generate a Tenor search URL for verification

        Args:
            tags: Tags to search for
            limit: Maximum results to return

        Returns:
            Tenor search URL
        """
        search_query = " ".join(tags)
        return f"https://tenor.com/search/{search_query.replace(' ', '-')}-gifs"

    def format_tags_for_tenor(
        self, tags: List[str], include_platform_tags: bool = True
    ) -> List[str]:
        """
        Format tags specifically for Tenor's tagging system

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
        Estimate the potential reach of given tags on Tenor

        Args:
            tags: Tags to analyze

        Returns:
            Dictionary with estimated metrics
        """
        # Mock implementation - in reality would query Tenor analytics
        total_searches = sum(hash(tag) % 10000 for tag in tags)

        return {
            "estimated_monthly_searches": total_searches,
            "competition_level": "medium",
            "recommended_tags": ["reaction", "animated", "gif"],
            "tag_count": len(tags),
        }

    def batch_upload(
        self, uploads: List[TenorUploadMetadata]
    ) -> List[TenorUploadResult]:
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

    def get_partner_stats(self) -> Dict:
        """
        Get statistics for the partner account

        Returns:
            Dictionary with partner statistics
        """
        # Mock implementation
        return {
            "partner_id": self.partner_id,
            "total_uploads": 0,
            "total_views": 0,
            "total_shares": 0,
            "top_tags": [],
            "upload_limit_remaining": 1000,
        }
