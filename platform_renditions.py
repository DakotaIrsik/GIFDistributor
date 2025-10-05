"""
Platform Renditions Module - Issue #30
Platform-specific media rendition specifications for Discord, Slack, Teams, etc.
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass


class Platform(str, Enum):
    """Target platforms with specific requirements"""

    DISCORD = "discord"
    SLACK = "slack"
    TEAMS = "teams"
    TWITTER = "twitter"
    WEB = "web"
    GENERIC = "generic"


@dataclass
class RenditionSpec:
    """Specification for a platform-specific rendition"""

    platform: Platform
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    max_file_size_mb: Optional[int] = None
    video_bitrate: str = "1M"
    quality: str = "high"  # low, medium, high
    description: str = ""


class PlatformRenditions:
    """
    Pre-configured rendition specs for different platforms
    Based on platform-specific requirements and limitations
    """

    @staticmethod
    def get_discord_spec() -> RenditionSpec:
        """
        Discord specifications:
        - Max 8MB for free users, 50MB for Nitro
        - Max 1280x720 recommended for embeds
        """
        return RenditionSpec(
            platform=Platform.DISCORD,
            max_width=1280,
            max_height=720,
            max_file_size_mb=8,
            video_bitrate="800k",
            quality="medium",
            description="Discord standard (free tier compatible)",
        )

    @staticmethod
    def get_slack_spec() -> RenditionSpec:
        """
        Slack specifications:
        - Videos play inline up to 1GB
        - Recommended max 1920x1080
        """
        return RenditionSpec(
            platform=Platform.SLACK,
            max_width=1920,
            max_height=1080,
            video_bitrate="2M",
            quality="high",
            description="Slack standard HD",
        )

    @staticmethod
    def get_teams_spec() -> RenditionSpec:
        """
        Microsoft Teams specifications:
        - Max 250MB per file
        - H.264 codec recommended
        """
        return RenditionSpec(
            platform=Platform.TEAMS,
            max_width=1920,
            max_height=1080,
            max_file_size_mb=250,
            video_bitrate="2M",
            quality="high",
            description="Microsoft Teams HD",
        )

    @staticmethod
    def get_twitter_spec() -> RenditionSpec:
        """
        Twitter specifications:
        - Max 512MB
        - Max 1920x1200 or 1200x1920
        """
        return RenditionSpec(
            platform=Platform.TWITTER,
            max_width=1920,
            max_height=1200,
            max_file_size_mb=512,
            video_bitrate="5M",
            quality="high",
            description="Twitter video standard",
        )

    @staticmethod
    def get_web_1080p_spec() -> RenditionSpec:
        """Web 1080p specification"""
        return RenditionSpec(
            platform=Platform.WEB,
            max_width=1920,
            max_height=1080,
            video_bitrate="3M",
            quality="high",
            description="Web 1080p HD",
        )

    @staticmethod
    def get_web_720p_spec() -> RenditionSpec:
        """Web 720p specification"""
        return RenditionSpec(
            platform=Platform.WEB,
            max_width=1280,
            max_height=720,
            video_bitrate="1.5M",
            quality="medium",
            description="Web 720p",
        )

    @staticmethod
    def get_all_specs() -> Dict[Platform, RenditionSpec]:
        """Get default specification for each platform"""
        return {
            Platform.DISCORD: PlatformRenditions.get_discord_spec(),
            Platform.SLACK: PlatformRenditions.get_slack_spec(),
            Platform.TEAMS: PlatformRenditions.get_teams_spec(),
            Platform.TWITTER: PlatformRenditions.get_twitter_spec(),
            Platform.WEB: PlatformRenditions.get_web_1080p_spec(),
        }

    @staticmethod
    def get_spec_for_platform(platform: Platform) -> Optional[RenditionSpec]:
        """Get specification for a specific platform"""
        return PlatformRenditions.get_all_specs().get(platform)


# Utility functions


def get_platform_constraints(platform: Platform) -> Dict:
    """
    Get platform constraints as a simple dictionary

    Returns:
        Dict with max_width, max_height, max_file_size_mb, etc.
    """
    spec = PlatformRenditions.get_spec_for_platform(platform)
    if not spec:
        return {}

    return {
        "max_width": spec.max_width,
        "max_height": spec.max_height,
        "max_file_size_mb": spec.max_file_size_mb,
        "video_bitrate": spec.video_bitrate,
        "quality": spec.quality,
        "description": spec.description,
    }


if __name__ == "__main__":
    print("Platform Renditions - Specifications")
    print("=" * 60)

    for platform, spec in PlatformRenditions.get_all_specs().items():
        print(f"\n{platform.value.upper()}:")
        print(f"  Description: {spec.description}")
        if spec.max_width:
            print(f"  Max Resolution: {spec.max_width}x{spec.max_height}")
        if spec.max_file_size_mb:
            print(f"  Max File Size: {spec.max_file_size_mb}MB")
        print(f"  Video Bitrate: {spec.video_bitrate}")
        print(f"  Quality: {spec.quality}")
