"""
Slack Share Module for GIF Distributor
Provides link unfurling and external upload path for Slack
Issue: #41
"""
from typing import Dict, Optional, List
from dataclasses import dataclass
import json


@dataclass
class SlackUnfurlBlock:
    """Represents a Slack unfurl block for rich link previews"""
    title: str
    title_link: str
    image_url: str
    text: Optional[str] = None
    footer: Optional[str] = None
    footer_icon: Optional[str] = None
    ts: Optional[int] = None


class SlackShareHandler:
    """Handles Slack link unfurling and share functionality"""

    def __init__(self, base_url: str = "https://gifdist.io"):
        self.base_url = base_url.rstrip('/')
        self.app_name = "GIFDistributor"

    def generate_unfurl_response(
        self,
        asset_id: str,
        asset_url: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        file_type: str = "gif"
    ) -> Dict:
        """
        Generate Slack unfurl response for a shared link

        Args:
            asset_id: Unique identifier for the asset
            asset_url: Direct URL to the asset (CDN URL)
            title: Optional title for the asset
            tags: Optional list of tags
            file_type: Type of media file (gif, mp4, webp)

        Returns:
            Dictionary containing Slack unfurl payload
        """
        canonical_url = f"{self.base_url}/a/{asset_id}"

        # Build title
        display_title = title or f"GIF {asset_id}"

        # Build description from tags
        description = ""
        if tags:
            description = f"Tags: {', '.join(tags)}"

        # Construct unfurl attachment
        unfurl_data = {
            "title": display_title,
            "title_link": canonical_url,
            "image_url": asset_url,
            "text": description,
            "footer": self.app_name,
            "color": "#FF6B35"  # Brand color
        }

        return {
            "unfurls": {
                canonical_url: unfurl_data
            }
        }

    def create_message_attachment(
        self,
        asset_url: str,
        title: Optional[str] = None,
        canonical_url: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Create a Slack message attachment for posting GIFs

        Args:
            asset_url: Direct URL to the asset
            title: Optional title
            canonical_url: Optional canonical URL
            tags: Optional list of tags

        Returns:
            Slack message attachment dictionary
        """
        attachment = {
            "fallback": title or "GIF from GIFDistributor",
            "image_url": asset_url,
            "color": "#FF6B35"
        }

        if title:
            attachment["title"] = title

        if canonical_url:
            attachment["title_link"] = canonical_url

        if tags:
            attachment["footer"] = f"Tags: {', '.join(tags)}"

        return attachment

    def build_share_message(
        self,
        asset_url: str,
        title: Optional[str] = None,
        canonical_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_text: bool = True
    ) -> Dict:
        """
        Build a complete Slack share message

        Args:
            asset_url: Direct URL to the asset
            title: Optional title
            canonical_url: Optional canonical URL
            tags: Optional list of tags
            include_text: Whether to include text in the message

        Returns:
            Complete Slack message payload
        """
        message = {
            "attachments": [
                self.create_message_attachment(
                    asset_url=asset_url,
                    title=title,
                    canonical_url=canonical_url,
                    tags=tags
                )
            ]
        }

        if include_text and canonical_url:
            message["text"] = canonical_url

        return message

    def create_opengraph_metadata(
        self,
        asset_id: str,
        asset_url: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        file_type: str = "gif"
    ) -> Dict[str, str]:
        """
        Generate Open Graph metadata for link unfurling

        Args:
            asset_id: Unique identifier for the asset
            asset_url: Direct URL to the asset
            title: Optional title
            tags: Optional list of tags
            file_type: Type of media file

        Returns:
            Dictionary of Open Graph meta tags
        """
        canonical_url = f"{self.base_url}/a/{asset_id}"
        display_title = title or f"GIF {asset_id}"
        description = f"Shared via {self.app_name}"

        if tags:
            description += f" • {', '.join(tags)}"

        # Determine media type
        media_type = "image/gif"
        if file_type == "mp4":
            media_type = "video/mp4"
        elif file_type == "webp":
            media_type = "image/webp"

        return {
            "og:type": "website",
            "og:url": canonical_url,
            "og:title": display_title,
            "og:description": description,
            "og:image": asset_url,
            "og:image:type": media_type,
            "og:site_name": self.app_name,
            # Twitter Card metadata for better unfurling
            "twitter:card": "summary_large_image",
            "twitter:title": display_title,
            "twitter:description": description,
            "twitter:image": asset_url
        }

    def handle_external_upload(
        self,
        file_data: bytes,
        filename: str,
        channel_id: str,
        title: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict:
        """
        Handle external upload path for Slack when link unfurling isn't available

        This method would integrate with Slack's files.upload API

        Args:
            file_data: Binary file data
            filename: Name of the file
            channel_id: Slack channel ID
            title: Optional title for the upload
            comment: Optional comment to add with the upload

        Returns:
            Upload response metadata
        """
        # This would call Slack's files.upload API
        # For now, return a mock response structure

        upload_payload = {
            "file": file_data,
            "filename": filename,
            "channels": channel_id,
            "initial_comment": comment or "",
            "title": title or filename
        }

        # Mock response
        return {
            "ok": True,
            "file": {
                "id": "F123456789",
                "name": filename,
                "filename": filename,
                "title": title or filename,
                "mimetype": "image/gif",
                "permalink": f"{self.base_url}/external/{filename}",
                "channels": [channel_id]
            }
        }

    def validate_unfurl_event(self, event_data: Dict) -> bool:
        """
        Validate a Slack link_shared event for unfurling

        Args:
            event_data: Event data from Slack

        Returns:
            True if event is valid for unfurling
        """
        required_fields = ["type", "channel", "message_ts", "links"]

        if not all(field in event_data for field in required_fields):
            return False

        if event_data.get("type") != "link_shared":
            return False

        if not isinstance(event_data.get("links"), list):
            return False

        return True

    def extract_asset_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract asset ID from a canonical URL

        Args:
            url: URL to parse

        Returns:
            Asset ID or None if not found
        """
        # Handle canonical URLs like https://gifdist.io/a/{asset_id}
        if "/a/" in url:
            parts = url.split("/a/")
            if len(parts) == 2:
                # Get asset_id and strip any query params
                asset_id = parts[1].split("?")[0].split("#")[0]
                return asset_id

        # Handle short URLs like https://gifdist.io/s/{short_code}
        if "/s/" in url:
            parts = url.split("/s/")
            if len(parts) == 2:
                short_code = parts[1].split("?")[0].split("#")[0]
                # This would need to resolve via ShareLinkGenerator
                return short_code

        return None
