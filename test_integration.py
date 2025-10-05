"""
Integration Tests for Analytics + ShareLinks
Tests the interaction between analytics and share link modules
"""

import pytest
import tempfile
import os
from analytics import AnalyticsTracker, EventType, Platform
from sharelinks import ShareLinkGenerator, create_asset_hash


class TestAnalyticsShareLinksIntegration:
    """Test integration between analytics tracking and share links"""

    def test_track_share_link_usage(self):
        """Test tracking analytics for share links"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        # Create a share link
        link = gen.create_share_link("asset123", title="Test GIF")
        short_code = link["short_code"]

        # Track events with the short code
        tracker.track_event(
            "asset123", EventType.VIEW, Platform.SLACK, short_code=short_code
        )
        tracker.track_event(
            "asset123", EventType.PLAY, Platform.SLACK, short_code=short_code
        )
        tracker.track_event(
            "asset123", EventType.CLICK, Platform.SLACK, short_code=short_code
        )

        # Verify analytics
        metrics = tracker.get_short_link_metrics(short_code)
        assert metrics["views"] == 1
        assert metrics["plays"] == 1
        assert metrics["clicks"] == 1
        assert metrics["ctr"] == 100.0

        # Verify share link resolution
        resolved = gen.resolve_short_link(short_code)
        assert resolved["asset_id"] == "asset123"
        assert resolved["clicks"] == 1  # From share link tracking

    def test_multiple_share_links_analytics(self):
        """Test analytics for multiple share links of same asset"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        # Create multiple share links for same asset
        link1 = gen.create_share_link("asset999", title="Link 1")
        link2 = gen.create_share_link("asset999", title="Link 2")

        # Track events for different links
        tracker.track_event(
            "asset999", EventType.VIEW, Platform.SLACK, short_code=link1["short_code"]
        )
        tracker.track_event(
            "asset999", EventType.VIEW, Platform.DISCORD, short_code=link2["short_code"]
        )
        tracker.track_event(
            "asset999", EventType.CLICK, Platform.SLACK, short_code=link1["short_code"]
        )

        # Check overall asset metrics
        asset_metrics = tracker.get_asset_metrics("asset999")
        assert asset_metrics["views"] == 2
        assert asset_metrics["clicks"] == 1

        # Check individual link metrics
        link1_metrics = tracker.get_short_link_metrics(link1["short_code"])
        link2_metrics = tracker.get_short_link_metrics(link2["short_code"])

        assert link1_metrics["views"] == 1
        assert link1_metrics["clicks"] == 1
        assert link2_metrics["views"] == 1
        assert link2_metrics["clicks"] == 0

    def test_platform_tracking_with_share_links(self):
        """Test platform-specific analytics with share links"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        link = gen.create_share_link("asset777")
        short_code = link["short_code"]

        # Track events from different platforms
        for _ in range(5):
            tracker.track_event(
                "asset777", EventType.VIEW, Platform.SLACK, short_code=short_code
            )
        for _ in range(3):
            tracker.track_event(
                "asset777", EventType.VIEW, Platform.DISCORD, short_code=short_code
            )
        tracker.track_event(
            "asset777", EventType.CLICK, Platform.SLACK, short_code=short_code
        )

        # Check platform breakdown
        platform_metrics = tracker.get_platform_metrics("asset777")
        assert platform_metrics["slack"]["views"] == 5
        assert platform_metrics["slack"]["clicks"] == 1
        assert platform_metrics["discord"]["views"] == 3

    def test_canonical_url_analytics_tracking(self):
        """Test tracking analytics for canonical URLs (no short code)"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        canonical_url = gen.create_canonical_url("asset555")

        # Track events without short code (direct canonical URL access)
        tracker.track_event("asset555", EventType.VIEW, Platform.WEB)
        tracker.track_event("asset555", EventType.VIEW, Platform.WEB)

        metrics = tracker.get_asset_metrics("asset555")
        assert metrics["views"] == 2


class TestHashBasedWorkflow:
    """Test complete workflow using hash-based asset IDs"""

    def test_hash_to_analytics_workflow(self):
        """Test workflow from file hash to analytics tracking"""
        # Create test file
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f:
            f.write(b"GIF content here")
            temp_path = f.name

        try:
            # Step 1: Hash the file
            content_hash = create_asset_hash(temp_path)

            # Step 2: Generate deterministic asset ID
            gen = ShareLinkGenerator()
            asset_id = gen.generate_hash_based_id(content_hash)

            # Step 3: Create share link
            link = gen.create_share_link(asset_id, title="Hashed GIF")

            # Step 4: Track analytics
            tracker = AnalyticsTracker()
            tracker.track_event(asset_id, EventType.VIEW, short_code=link["short_code"])
            tracker.track_event(asset_id, EventType.PLAY, short_code=link["short_code"])

            # Verify everything is connected
            link_metrics = tracker.get_short_link_metrics(link["short_code"])
            assert link_metrics["asset_id"] == asset_id
            assert link_metrics["views"] == 1
            assert link_metrics["plays"] == 1

            resolved = gen.resolve_short_link(link["short_code"])
            assert resolved["asset_id"] == asset_id
            assert resolved["canonical_url"] == gen.create_canonical_url(asset_id)
        finally:
            os.unlink(temp_path)

    def test_deduplication_with_analytics(self):
        """Test that duplicate content uses same asset ID in analytics"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()
        content = b"Duplicate test content"

        # Upload "same" content twice
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f2:
            f2.write(content)
            path2 = f2.name

        try:
            # Both files should produce same asset ID
            hash1 = create_asset_hash(path1)
            hash2 = create_asset_hash(path2)
            asset_id1 = gen.generate_hash_based_id(hash1)
            asset_id2 = gen.generate_hash_based_id(hash2)

            assert asset_id1 == asset_id2

            # Track events for "different uploads" of same content
            tracker.track_event(asset_id1, EventType.VIEW)
            tracker.track_event(asset_id2, EventType.VIEW)

            # Should aggregate to same asset
            metrics = tracker.get_asset_metrics(asset_id1)
            assert metrics["views"] == 2
        finally:
            os.unlink(path1)
            os.unlink(path2)


class TestCrossModuleMetadata:
    """Test metadata consistency across modules"""

    def test_metadata_consistency(self):
        """Test that metadata is consistent between modules"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        # Create share link with metadata
        link = gen.create_share_link(
            "asset444", title="Epic GIF", tags=["funny", "viral"]
        )

        # Get share link metadata
        share_metadata = gen.get_share_metadata(link["short_code"])

        # Track event with metadata
        event_metadata = {
            "referrer": "https://example.com",
            "user_agent": "Mozilla/5.0",
        }
        tracker.track_event(
            "asset444",
            EventType.VIEW,
            short_code=link["short_code"],
            metadata=event_metadata,
        )

        # Verify both maintain their own metadata
        assert share_metadata["title"] == "Epic GIF"
        assert share_metadata["tags"] == ["funny", "viral"]

        events = tracker.get_events_by_timeframe("asset444")
        assert events[0]["metadata"]["referrer"] == "https://example.com"

    def test_share_link_with_custom_base_url(self):
        """Test analytics work with custom base URLs"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator("https://custom-domain.com")

        link = gen.create_share_link("asset888")

        # Verify custom URLs
        assert "custom-domain.com" in link["short_url"]
        assert "custom-domain.com" in link["canonical_url"]

        # Track analytics
        tracker.track_event("asset888", EventType.VIEW, short_code=link["short_code"])

        metrics = tracker.get_short_link_metrics(link["short_code"])
        assert metrics["asset_id"] == "asset888"


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""

    def test_viral_content_scenario(self):
        """Test scenario where content goes viral across platforms"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        # Create share links for different platforms
        slack_link = gen.create_share_link("viral_gif", title="Viral on Slack")
        discord_link = gen.create_share_link("viral_gif", title="Viral on Discord")

        # Simulate viral spread on Slack
        for _ in range(100):
            tracker.track_event(
                "viral_gif",
                EventType.VIEW,
                Platform.SLACK,
                short_code=slack_link["short_code"],
            )
        for _ in range(80):
            tracker.track_event(
                "viral_gif",
                EventType.PLAY,
                Platform.SLACK,
                short_code=slack_link["short_code"],
            )
        for _ in range(20):
            tracker.track_event(
                "viral_gif",
                EventType.CLICK,
                Platform.SLACK,
                short_code=slack_link["short_code"],
            )

        # Simulate spread on Discord
        for _ in range(50):
            tracker.track_event(
                "viral_gif",
                EventType.VIEW,
                Platform.DISCORD,
                short_code=discord_link["short_code"],
            )
        for _ in range(30):
            tracker.track_event(
                "viral_gif",
                EventType.PLAY,
                Platform.DISCORD,
                short_code=discord_link["short_code"],
            )

        # Check overall metrics
        asset_metrics = tracker.get_asset_metrics("viral_gif")
        assert asset_metrics["views"] == 150
        assert asset_metrics["plays"] == 110
        assert asset_metrics["clicks"] == 20

        # Check platform breakdown
        platform_metrics = tracker.get_platform_metrics("viral_gif")
        assert platform_metrics["slack"]["views"] == 100
        assert platform_metrics["discord"]["views"] == 50

        # Check individual link performance
        slack_metrics = tracker.get_short_link_metrics(slack_link["short_code"])
        discord_metrics = tracker.get_short_link_metrics(discord_link["short_code"])

        assert slack_metrics["ctr"] == 20.0
        assert discord_metrics["ctr"] == 0.0

    def test_ab_testing_scenario(self):
        """Test A/B testing different share link titles"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        # Create two variants
        variant_a = gen.create_share_link("asset_ab", title="Click me!")
        variant_b = gen.create_share_link("asset_ab", title="Amazing GIF Inside")

        # Simulate traffic
        for _ in range(100):
            tracker.track_event(
                "asset_ab", EventType.VIEW, short_code=variant_a["short_code"]
            )
        for _ in range(10):
            tracker.track_event(
                "asset_ab", EventType.CLICK, short_code=variant_a["short_code"]
            )

        for _ in range(100):
            tracker.track_event(
                "asset_ab", EventType.VIEW, short_code=variant_b["short_code"]
            )
        for _ in range(25):
            tracker.track_event(
                "asset_ab", EventType.CLICK, short_code=variant_b["short_code"]
            )

        # Compare performance
        a_metrics = tracker.get_short_link_metrics(variant_a["short_code"])
        b_metrics = tracker.get_short_link_metrics(variant_b["short_code"])

        assert a_metrics["ctr"] == 10.0
        assert b_metrics["ctr"] == 25.0  # Variant B performs better

    def test_campaign_tracking(self):
        """Test tracking a marketing campaign across platforms"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        campaign_asset = "campaign_2025"

        # Create platform-specific links
        twitter_link = gen.create_share_link(
            campaign_asset, tags=["campaign", "twitter"]
        )
        facebook_link = gen.create_share_link(
            campaign_asset, tags=["campaign", "facebook"]
        )
        email_link = gen.create_share_link(campaign_asset, tags=["campaign", "email"])

        # Track campaign performance
        tracker.track_event(
            campaign_asset,
            EventType.VIEW,
            Platform.TWITTER,
            short_code=twitter_link["short_code"],
        )
        tracker.track_event(
            campaign_asset,
            EventType.CLICK,
            Platform.TWITTER,
            short_code=twitter_link["short_code"],
        )

        tracker.track_event(
            campaign_asset,
            EventType.VIEW,
            Platform.FACEBOOK,
            short_code=facebook_link["short_code"],
        )

        tracker.track_event(
            campaign_asset,
            EventType.VIEW,
            Platform.WEB,
            short_code=email_link["short_code"],
        )
        tracker.track_event(
            campaign_asset,
            EventType.PLAY,
            Platform.WEB,
            short_code=email_link["short_code"],
        )

        # Analyze campaign
        campaign_metrics = tracker.get_asset_metrics(campaign_asset)
        assert campaign_metrics["views"] == 3
        assert campaign_metrics["plays"] == 1
        assert campaign_metrics["clicks"] == 1

        # Check which channel performed best
        twitter_metrics = tracker.get_short_link_metrics(twitter_link["short_code"])
        assert twitter_metrics["ctr"] == 100.0  # Best performing


class TestErrorHandlingIntegration:
    """Test error handling across both modules"""

    def test_analytics_for_nonexistent_link(self):
        """Test tracking analytics for a short code that doesn't exist in share links"""
        tracker = AnalyticsTracker()

        # Track with non-existent short code (analytics should still work)
        tracker.track_event("asset123", EventType.VIEW, short_code="nonexistent")

        metrics = tracker.get_short_link_metrics("nonexistent")
        assert metrics["views"] == 1

    def test_resolve_link_without_analytics(self):
        """Test resolving share link that has no analytics data"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        link = gen.create_share_link("unused_asset")

        # Resolve without any analytics
        resolved = gen.resolve_short_link(link["short_code"])
        assert resolved["asset_id"] == "unused_asset"

        # Analytics should show zero
        metrics = tracker.get_short_link_metrics(link["short_code"])
        assert metrics["views"] == 0

    def test_mixed_tracking_with_and_without_short_codes(self):
        """Test mixing direct and share link traffic"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        link = gen.create_share_link("mixed_asset")

        # Some events with short code
        tracker.track_event(
            "mixed_asset", EventType.VIEW, short_code=link["short_code"]
        )
        tracker.track_event(
            "mixed_asset", EventType.PLAY, short_code=link["short_code"]
        )

        # Some events without (direct canonical URL access)
        tracker.track_event("mixed_asset", EventType.VIEW)
        tracker.track_event("mixed_asset", EventType.PLAY)

        # Overall metrics should include both
        asset_metrics = tracker.get_asset_metrics("mixed_asset")
        assert asset_metrics["views"] == 2
        assert asset_metrics["plays"] == 2

        # Short link metrics only count events with short code
        link_metrics = tracker.get_short_link_metrics(link["short_code"])
        assert link_metrics["views"] == 1
        assert link_metrics["plays"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
