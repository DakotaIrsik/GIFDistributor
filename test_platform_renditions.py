"""
Tests for Platform Renditions Module - Issue #30
"""

import pytest
from platform_renditions import (
    Platform,
    RenditionSpec,
    PlatformRenditions,
    get_platform_constraints,
)


def test_platform_enum_values():
    """Test Platform enum has expected values"""
    assert Platform.DISCORD.value == "discord"
    assert Platform.SLACK.value == "slack"
    assert Platform.TEAMS.value == "teams"
    assert Platform.TWITTER.value == "twitter"
    assert Platform.WEB.value == "web"
    assert Platform.GENERIC.value == "generic"


def test_discord_spec():
    """Test Discord rendition specification"""
    spec = PlatformRenditions.get_discord_spec()

    assert spec.platform == Platform.DISCORD
    assert spec.max_width == 1280
    assert spec.max_height == 720
    assert spec.max_file_size_mb == 8
    assert spec.video_bitrate == "800k"
    assert spec.quality == "medium"
    assert "Discord" in spec.description


def test_slack_spec():
    """Test Slack rendition specification"""
    spec = PlatformRenditions.get_slack_spec()

    assert spec.platform == Platform.SLACK
    assert spec.max_width == 1920
    assert spec.max_height == 1080
    assert spec.video_bitrate == "2M"
    assert spec.quality == "high"


def test_teams_spec():
    """Test Microsoft Teams rendition specification"""
    spec = PlatformRenditions.get_teams_spec()

    assert spec.platform == Platform.TEAMS
    assert spec.max_width == 1920
    assert spec.max_height == 1080
    assert spec.max_file_size_mb == 250
    assert spec.video_bitrate == "2M"


def test_twitter_spec():
    """Test Twitter rendition specification"""
    spec = PlatformRenditions.get_twitter_spec()

    assert spec.platform == Platform.TWITTER
    assert spec.max_width == 1920
    assert spec.max_height == 1200
    assert spec.max_file_size_mb == 512
    assert spec.video_bitrate == "5M"


def test_web_1080p_spec():
    """Test Web 1080p specification"""
    spec = PlatformRenditions.get_web_1080p_spec()

    assert spec.platform == Platform.WEB
    assert spec.max_width == 1920
    assert spec.max_height == 1080
    assert spec.video_bitrate == "3M"
    assert spec.quality == "high"


def test_web_720p_spec():
    """Test Web 720p specification"""
    spec = PlatformRenditions.get_web_720p_spec()

    assert spec.platform == Platform.WEB
    assert spec.max_width == 1280
    assert spec.max_height == 720
    assert spec.video_bitrate == "1.5M"
    assert spec.quality == "medium"


def test_get_all_specs():
    """Test getting all platform specifications"""
    all_specs = PlatformRenditions.get_all_specs()

    assert len(all_specs) == 5
    assert Platform.DISCORD in all_specs
    assert Platform.SLACK in all_specs
    assert Platform.TEAMS in all_specs
    assert Platform.TWITTER in all_specs
    assert Platform.WEB in all_specs

    # Verify each spec is a RenditionSpec
    for platform, spec in all_specs.items():
        assert isinstance(spec, RenditionSpec)
        assert spec.platform == platform


def test_get_spec_for_platform():
    """Test getting spec for a specific platform"""
    discord_spec = PlatformRenditions.get_spec_for_platform(Platform.DISCORD)

    assert discord_spec is not None
    assert discord_spec.platform == Platform.DISCORD
    assert discord_spec.max_width == 1280


def test_get_spec_for_nonexistent_platform():
    """Test getting spec for platform not in defaults"""
    generic_spec = PlatformRenditions.get_spec_for_platform(Platform.GENERIC)

    assert generic_spec is None


def test_get_platform_constraints():
    """Test getting platform constraints as dictionary"""
    constraints = get_platform_constraints(Platform.DISCORD)

    assert constraints["max_width"] == 1280
    assert constraints["max_height"] == 720
    assert constraints["max_file_size_mb"] == 8
    assert constraints["video_bitrate"] == "800k"
    assert constraints["quality"] == "medium"


def test_get_platform_constraints_nonexistent():
    """Test getting constraints for nonexistent platform"""
    constraints = get_platform_constraints(Platform.GENERIC)

    assert constraints == {}


def test_rendition_spec_dataclass():
    """Test RenditionSpec dataclass creation"""
    spec = RenditionSpec(
        platform=Platform.GENERIC,
        max_width=1920,
        max_height=1080,
        max_file_size_mb=100,
        video_bitrate="2M",
        quality="high",
        description="Custom spec",
    )

    assert spec.platform == Platform.GENERIC
    assert spec.max_width == 1920
    assert spec.max_height == 1080
    assert spec.max_file_size_mb == 100
    assert spec.video_bitrate == "2M"
    assert spec.quality == "high"
    assert spec.description == "Custom spec"


def test_discord_file_size_constraint():
    """Test Discord has appropriate file size constraint for free tier"""
    spec = PlatformRenditions.get_discord_spec()

    # Discord free tier is 8MB
    assert spec.max_file_size_mb == 8
    # Should be lower resolution to fit in size constraint
    assert spec.max_width <= 1280


def test_teams_large_file_support():
    """Test Teams supports large files"""
    spec = PlatformRenditions.get_teams_spec()

    # Teams supports up to 250MB
    assert spec.max_file_size_mb == 250
    # Should support HD video
    assert spec.max_width >= 1920


def test_quality_levels():
    """Test different quality levels are used appropriately"""
    discord_spec = PlatformRenditions.get_discord_spec()
    web_720p_spec = PlatformRenditions.get_web_720p_spec()
    teams_spec = PlatformRenditions.get_teams_spec()

    # Discord should use medium quality for size constraints
    assert discord_spec.quality == "medium"

    # Web 720p should use medium
    assert web_720p_spec.quality == "medium"

    # Teams should use high quality
    assert teams_spec.quality == "high"


def test_bitrate_scaling():
    """Test bitrate scales with resolution/quality"""
    discord_spec = PlatformRenditions.get_discord_spec()
    twitter_spec = PlatformRenditions.get_twitter_spec()

    # Discord (720p, medium) should have lower bitrate than Twitter (1200p, high)
    discord_bitrate = int(
        discord_spec.video_bitrate.replace("k", "").replace("M", "000")
    )
    twitter_bitrate = int(
        twitter_spec.video_bitrate.replace("M", "000").replace("k", "")
    )

    assert discord_bitrate < twitter_bitrate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
