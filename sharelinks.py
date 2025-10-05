"""
Share Links Module for GIF Distributor
Provides canonical asset URLs and short link generation
Issue: #40
"""

import hashlib
import string
import secrets
from typing import Optional, Dict
from datetime import datetime, timezone


class ShareLinkGenerator:
    """Generates and manages share links for assets"""

    ALPHABET = string.ascii_letters + string.digits
    SHORT_LINK_LENGTH = 8

    def __init__(self, base_url: str = "https://gifdist.io"):
        self.base_url = base_url.rstrip("/")
        self._links_db: Dict[str, Dict] = {}

    def generate_short_code(self) -> str:
        """Generate a unique short code for URLs"""
        return "".join(
            secrets.choice(self.ALPHABET) for _ in range(self.SHORT_LINK_LENGTH)
        )

    def create_canonical_url(self, asset_id: str, asset_type: str = "gif") -> str:
        """
        Create a canonical URL for an asset
        Format: {base_url}/a/{asset_id}
        """
        return f"{self.base_url}/a/{asset_id}"

    def create_share_link(
        self, asset_id: str, title: str = "", tags: list = None
    ) -> Dict[str, str]:
        """
        Create a shareable short link for an asset

        Args:
            asset_id: Unique identifier for the asset
            title: Optional title for the asset
            tags: Optional list of tags

        Returns:
            Dictionary with short_url, canonical_url, and short_code
        """
        short_code = self.generate_short_code()
        canonical_url = self.create_canonical_url(asset_id)
        short_url = f"{self.base_url}/s/{short_code}"

        # Store in database (mock implementation)
        self._links_db[short_code] = {
            "asset_id": asset_id,
            "canonical_url": canonical_url,
            "title": title,
            "tags": list(tags) if tags else [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "clicks": 0,
        }

        return {
            "short_url": short_url,
            "canonical_url": canonical_url,
            "short_code": short_code,
        }

    def resolve_short_link(self, short_code: str) -> Optional[Dict]:
        """
        Resolve a short code to its asset information

        Args:
            short_code: The short code to resolve

        Returns:
            Asset information dictionary or None if not found
        """
        link_data = self._links_db.get(short_code)
        if link_data:
            # Increment click counter
            link_data["clicks"] += 1
        return link_data

    def generate_hash_based_id(self, content_hash: str) -> str:
        """
        Generate a deterministic asset ID based on content hash
        Useful for deduplication

        Args:
            content_hash: Hash of the asset content

        Returns:
            Asset ID derived from hash
        """
        # Use first 16 characters of hash for asset ID
        return content_hash[:16]

    def get_share_metadata(self, short_code: str) -> Optional[Dict]:
        """
        Get metadata for a share link (for Open Graph tags, etc.)

        Args:
            short_code: The short code to get metadata for

        Returns:
            Metadata dictionary or None if not found
        """
        link_data = self._links_db.get(short_code)
        if not link_data:
            return None

        return {
            "title": link_data.get("title") or "GIF from GIFDistributor",
            "canonical_url": link_data["canonical_url"],
            "tags": link_data.get("tags", []),
            "asset_id": link_data["asset_id"],
        }


def create_asset_hash(file_path: str) -> str:
    """
    Create a SHA-256 hash of an asset file

    Args:
        file_path: Path to the asset file

    Returns:
        Hex digest of the file hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
