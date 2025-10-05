"""
Tests for Analytics Module
Issue: #33
"""

import pytest
from analytics import AnalyticsTracker, EventType, Platform
from datetime import datetime, timedelta, timezone


class TestAnalyticsTracker:
    """Test cases for AnalyticsTracker class"""

    def test_initialization(self):
        """Test that tracker initializes correctly"""
        tracker = AnalyticsTracker()
        assert tracker._events == []
        assert tracker._metrics_cache == {}

    def test_track_view_event(self):
        """Test tracking a view event"""
        tracker = AnalyticsTracker()
        event = tracker.track_event("asset1", EventType.VIEW)

        assert event["asset_id"] == "asset1"
        assert event["event_type"] == "view"
        assert event["platform"] == "web"
        assert "timestamp" in event

    def test_track_play_event(self):
        """Test tracking a play event"""
        tracker = AnalyticsTracker()
        event = tracker.track_event("asset2", EventType.PLAY, Platform.SLACK)

        assert event["asset_id"] == "asset2"
        assert event["event_type"] == "play"
        assert event["platform"] == "slack"

    def test_track_click_event(self):
        """Test tracking a click event"""
        tracker = AnalyticsTracker()
        event = tracker.track_event("asset3", EventType.CLICK, Platform.DISCORD)

        assert event["asset_id"] == "asset3"
        assert event["event_type"] == "click"
        assert event["platform"] == "discord"

    def test_track_event_with_short_code(self):
        """Test tracking event with short code"""
        tracker = AnalyticsTracker()
        event = tracker.track_event("asset4", EventType.VIEW, short_code="abc123")

        assert event["short_code"] == "abc123"

    def test_track_event_with_metadata(self):
        """Test tracking event with additional metadata"""
        tracker = AnalyticsTracker()
        metadata = {"user_agent": "Mozilla/5.0", "referrer": "https://example.com"}
        event = tracker.track_event("asset5", EventType.VIEW, metadata=metadata)

        assert event["metadata"]["user_agent"] == "Mozilla/5.0"
        assert event["metadata"]["referrer"] == "https://example.com"


class TestAssetMetrics:
    """Test cases for asset metrics aggregation"""

    def test_get_asset_metrics_no_events(self):
        """Test getting metrics for asset with no events"""
        tracker = AnalyticsTracker()
        metrics = tracker.get_asset_metrics("nonexistent")

        assert metrics["asset_id"] == "nonexistent"
        assert metrics["views"] == 0
        assert metrics["plays"] == 0
        assert metrics["clicks"] == 0
        assert metrics["ctr"] == 0.0

    def test_get_asset_metrics_single_view(self):
        """Test metrics with single view"""
        tracker = AnalyticsTracker()
        tracker.track_event("asset1", EventType.VIEW)

        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["views"] == 1
        assert metrics["plays"] == 0
        assert metrics["clicks"] == 0
        assert metrics["ctr"] == 0.0

    def test_get_asset_metrics_ctr_calculation(self):
        """Test CTR calculation"""
        tracker = AnalyticsTracker()

        # 10 views, 2 clicks = 20% CTR
        for _ in range(10):
            tracker.track_event("asset1", EventType.VIEW)
        for _ in range(2):
            tracker.track_event("asset1", EventType.CLICK)

        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["views"] == 10
        assert metrics["clicks"] == 2
        assert metrics["ctr"] == 20.0

    def test_get_asset_metrics_play_rate(self):
        """Test play rate calculation"""
        tracker = AnalyticsTracker()

        # 100 views, 75 plays = 75% play rate
        for _ in range(100):
            tracker.track_event("asset1", EventType.VIEW)
        for _ in range(75):
            tracker.track_event("asset1", EventType.PLAY)

        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["views"] == 100
        assert metrics["plays"] == 75
        assert metrics["play_rate"] == 75.0

    def test_get_asset_metrics_mixed_events(self):
        """Test metrics with mixed event types"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.PLAY)
        tracker.track_event("asset1", EventType.PLAY)
        tracker.track_event("asset1", EventType.CLICK)

        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["views"] == 3
        assert metrics["plays"] == 2
        assert metrics["clicks"] == 1
        assert metrics["ctr"] == 33.33
        assert metrics["play_rate"] == 66.67

    def test_metrics_cache_invalidation(self):
        """Test that cache is invalidated when new events are tracked"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        metrics1 = tracker.get_asset_metrics("asset1")
        assert metrics1["views"] == 1

        # Add another event
        tracker.track_event("asset1", EventType.VIEW)
        metrics2 = tracker.get_asset_metrics("asset1")
        assert metrics2["views"] == 2


class TestPlatformMetrics:
    """Test cases for platform-specific metrics"""

    def test_get_platform_metrics_single_platform(self):
        """Test platform metrics with events from one platform"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW, Platform.SLACK)
        tracker.track_event("asset1", EventType.PLAY, Platform.SLACK)
        tracker.track_event("asset1", EventType.CLICK, Platform.SLACK)

        platform_metrics = tracker.get_platform_metrics("asset1")

        assert "slack" in platform_metrics
        assert platform_metrics["slack"]["views"] == 1
        assert platform_metrics["slack"]["plays"] == 1
        assert platform_metrics["slack"]["clicks"] == 1
        assert platform_metrics["slack"]["ctr"] == 100.0

    def test_get_platform_metrics_multiple_platforms(self):
        """Test platform metrics across multiple platforms"""
        tracker = AnalyticsTracker()

        # Slack: 10 views, 2 clicks
        for _ in range(10):
            tracker.track_event("asset1", EventType.VIEW, Platform.SLACK)
        for _ in range(2):
            tracker.track_event("asset1", EventType.CLICK, Platform.SLACK)

        # Discord: 5 views, 1 click
        for _ in range(5):
            tracker.track_event("asset1", EventType.VIEW, Platform.DISCORD)
        tracker.track_event("asset1", EventType.CLICK, Platform.DISCORD)

        platform_metrics = tracker.get_platform_metrics("asset1")

        assert platform_metrics["slack"]["views"] == 10
        assert platform_metrics["slack"]["clicks"] == 2
        assert platform_metrics["slack"]["ctr"] == 20.0

        assert platform_metrics["discord"]["views"] == 5
        assert platform_metrics["discord"]["clicks"] == 1
        assert platform_metrics["discord"]["ctr"] == 20.0

    def test_get_platform_metrics_no_events(self):
        """Test platform metrics with no events"""
        tracker = AnalyticsTracker()
        platform_metrics = tracker.get_platform_metrics("nonexistent")

        assert platform_metrics == {}


class TestShortLinkMetrics:
    """Test cases for short link metrics"""

    def test_get_short_link_metrics_no_events(self):
        """Test short link metrics with no events"""
        tracker = AnalyticsTracker()
        metrics = tracker.get_short_link_metrics("unknown")

        assert metrics["short_code"] == "unknown"
        assert metrics["views"] == 0
        assert metrics["clicks"] == 0

    def test_get_short_link_metrics_with_events(self):
        """Test short link metrics with tracked events"""
        tracker = AnalyticsTracker()

        # Track events with short code
        for _ in range(5):
            tracker.track_event("asset1", EventType.VIEW, short_code="abc123")
        for _ in range(3):
            tracker.track_event("asset1", EventType.PLAY, short_code="abc123")
        tracker.track_event("asset1", EventType.CLICK, short_code="abc123")

        metrics = tracker.get_short_link_metrics("abc123")

        assert metrics["short_code"] == "abc123"
        assert metrics["asset_id"] == "asset1"
        assert metrics["views"] == 5
        assert metrics["plays"] == 3
        assert metrics["clicks"] == 1
        assert metrics["ctr"] == 20.0
        assert metrics["play_rate"] == 60.0

    def test_get_short_link_metrics_multiple_links(self):
        """Test metrics are separate for different short links"""
        tracker = AnalyticsTracker()

        # Link 1
        tracker.track_event("asset1", EventType.VIEW, short_code="link1")
        tracker.track_event("asset1", EventType.CLICK, short_code="link1")

        # Link 2
        tracker.track_event("asset1", EventType.VIEW, short_code="link2")
        tracker.track_event("asset1", EventType.VIEW, short_code="link2")

        metrics1 = tracker.get_short_link_metrics("link1")
        metrics2 = tracker.get_short_link_metrics("link2")

        assert metrics1["views"] == 1
        assert metrics1["clicks"] == 1
        assert metrics2["views"] == 2
        assert metrics2["clicks"] == 0


class TestTopAssets:
    """Test cases for top assets ranking"""

    def test_get_top_assets_by_views(self):
        """Test getting top assets by views"""
        tracker = AnalyticsTracker()

        # Asset 1: 10 views
        for _ in range(10):
            tracker.track_event("asset1", EventType.VIEW)

        # Asset 2: 5 views
        for _ in range(5):
            tracker.track_event("asset2", EventType.VIEW)

        # Asset 3: 15 views
        for _ in range(15):
            tracker.track_event("asset3", EventType.VIEW)

        top_assets = tracker.get_top_assets(metric="views", limit=10)

        assert len(top_assets) == 3
        assert top_assets[0]["asset_id"] == "asset3"
        assert top_assets[0]["views"] == 15
        assert top_assets[1]["asset_id"] == "asset1"
        assert top_assets[2]["asset_id"] == "asset2"

    def test_get_top_assets_by_ctr(self):
        """Test getting top assets by CTR"""
        tracker = AnalyticsTracker()

        # Asset 1: 10 views, 5 clicks = 50% CTR
        for _ in range(10):
            tracker.track_event("asset1", EventType.VIEW)
        for _ in range(5):
            tracker.track_event("asset1", EventType.CLICK)

        # Asset 2: 10 views, 1 click = 10% CTR
        for _ in range(10):
            tracker.track_event("asset2", EventType.VIEW)
        tracker.track_event("asset2", EventType.CLICK)

        top_assets = tracker.get_top_assets(metric="ctr", limit=10)

        assert top_assets[0]["asset_id"] == "asset1"
        assert top_assets[0]["ctr"] == 50.0
        assert top_assets[1]["asset_id"] == "asset2"
        assert top_assets[1]["ctr"] == 10.0

    def test_get_top_assets_limit(self):
        """Test that limit parameter works"""
        tracker = AnalyticsTracker()

        # Create 10 assets
        for i in range(10):
            tracker.track_event(f"asset{i}", EventType.VIEW)

        top_assets = tracker.get_top_assets(metric="views", limit=3)
        assert len(top_assets) == 3


class TestTimeframeQueries:
    """Test cases for timeframe-based queries"""

    def test_get_events_by_timeframe_no_filter(self):
        """Test getting all events without timeframe filter"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.PLAY)

        events = tracker.get_events_by_timeframe("asset1")
        assert len(events) == 2

    def test_get_events_by_timeframe_start_time(self):
        """Test filtering events by start time"""
        tracker = AnalyticsTracker()

        # Track events
        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.PLAY)

        # Get events from now onwards (should include all)
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        events = tracker.get_events_by_timeframe("asset1", start_time=past)
        assert len(events) == 2

    def test_get_events_by_timeframe_end_time(self):
        """Test filtering events by end time"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)

        # Get events until now (should include all)
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        events = tracker.get_events_by_timeframe("asset1", end_time=future)
        assert len(events) == 1


class TestUtilityFunctions:
    """Test utility functions"""

    def test_clear_events_all(self):
        """Test clearing all events"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset2", EventType.VIEW)

        assert len(tracker._events) == 2

        tracker.clear_events()
        assert len(tracker._events) == 0

    def test_clear_events_specific_asset(self):
        """Test clearing events for specific asset"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset2", EventType.VIEW)
        tracker.track_event("asset1", EventType.PLAY)

        tracker.clear_events(asset_id="asset1")

        assert len(tracker._events) == 1
        assert tracker._events[0]["asset_id"] == "asset2"

    def test_clear_events_invalidates_cache(self):
        """Test that clearing events invalidates cache"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["views"] == 1

        tracker.clear_events(asset_id="asset1")
        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["views"] == 0


class TestIntegration:
    """Integration tests combining multiple features"""

    def test_full_analytics_workflow(self):
        """Test complete analytics workflow"""
        tracker = AnalyticsTracker()

        # Simulate user interactions across platforms
        tracker.track_event(
            "asset1", EventType.VIEW, Platform.SLACK, short_code="link1"
        )
        tracker.track_event(
            "asset1", EventType.PLAY, Platform.SLACK, short_code="link1"
        )
        tracker.track_event(
            "asset1", EventType.VIEW, Platform.DISCORD, short_code="link2"
        )
        tracker.track_event("asset1", EventType.VIEW, Platform.WEB)
        tracker.track_event(
            "asset1", EventType.CLICK, Platform.SLACK, short_code="link1"
        )

        # Check overall metrics
        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["views"] == 3
        assert metrics["plays"] == 1
        assert metrics["clicks"] == 1

        # Check platform breakdown
        platform_metrics = tracker.get_platform_metrics("asset1")
        assert platform_metrics["slack"]["views"] == 1
        assert platform_metrics["slack"]["plays"] == 1
        assert platform_metrics["slack"]["clicks"] == 1
        assert platform_metrics["discord"]["views"] == 1
        assert platform_metrics["web"]["views"] == 1

        # Check short link metrics
        link1_metrics = tracker.get_short_link_metrics("link1")
        assert link1_metrics["views"] == 1
        assert link1_metrics["plays"] == 1
        assert link1_metrics["clicks"] == 1


class TestEnumEdgeCases:
    """Test edge cases for EventType and Platform enums"""

    def test_event_type_enum_values(self):
        """Test all EventType enum values are accessible"""
        assert EventType.VIEW.value == "view"
        assert EventType.PLAY.value == "play"
        assert EventType.CLICK.value == "click"

    def test_platform_enum_values(self):
        """Test all Platform enum values"""
        assert Platform.WEB.value == "web"
        assert Platform.SLACK.value == "slack"
        assert Platform.DISCORD.value == "discord"
        assert Platform.TEAMS.value == "teams"
        assert Platform.TWITTER.value == "twitter"
        assert Platform.FACEBOOK.value == "facebook"
        assert Platform.OTHER.value == "other"

    def test_event_with_all_platforms(self):
        """Test tracking events across all platform types"""
        tracker = AnalyticsTracker()
        platforms = [
            Platform.WEB,
            Platform.SLACK,
            Platform.DISCORD,
            Platform.TEAMS,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.OTHER,
        ]

        for platform in platforms:
            tracker.track_event("asset1", EventType.VIEW, platform)

        platform_metrics = tracker.get_platform_metrics("asset1")
        assert len(platform_metrics) == 7


class TestMetricsEdgeCases:
    """Test edge cases in metrics calculation"""

    def test_total_events_field(self):
        """Test that total_events field is correctly calculated"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.PLAY)
        tracker.track_event("asset1", EventType.CLICK)
        tracker.track_event("asset1", EventType.CLICK)

        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["total_events"] == 5

    def test_rounding_precision(self):
        """Test CTR and play rate rounding to 2 decimal places"""
        tracker = AnalyticsTracker()

        # Create scenario with non-round percentages
        for _ in range(3):
            tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.CLICK)

        metrics = tracker.get_asset_metrics("asset1")
        # 1/3 * 100 = 33.333...
        assert metrics["ctr"] == 33.33
        assert isinstance(metrics["ctr"], float)

    def test_cache_hit_performance(self):
        """Test that cached metrics are returned correctly"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)

        # First call - cache miss
        metrics1 = tracker.get_asset_metrics("asset1")
        # Second call - cache hit
        metrics2 = tracker.get_asset_metrics("asset1")

        assert metrics1 == metrics2
        assert "asset1" in tracker._metrics_cache

    def test_multiple_assets_independent_cache(self):
        """Test that cache is maintained independently per asset"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset2", EventType.VIEW)
        tracker.track_event("asset2", EventType.VIEW)

        metrics1 = tracker.get_asset_metrics("asset1")
        metrics2 = tracker.get_asset_metrics("asset2")

        assert metrics1["views"] == 1
        assert metrics2["views"] == 2
        assert len(tracker._metrics_cache) == 2


class TestTimeframeBoundaries:
    """Test timeframe boundary conditions"""

    def test_exact_start_time_boundary(self):
        """Test events exactly at start time are included"""
        tracker = AnalyticsTracker()

        # Track event and capture its exact timestamp
        event = tracker.track_event("asset1", EventType.VIEW)
        event_time = datetime.fromisoformat(event["timestamp"])

        # Query with exact event time as start
        events = tracker.get_events_by_timeframe("asset1", start_time=event_time)
        assert len(events) == 1

    def test_exact_end_time_boundary(self):
        """Test events exactly at end time are included"""
        tracker = AnalyticsTracker()

        event = tracker.track_event("asset1", EventType.VIEW)
        event_time = datetime.fromisoformat(event["timestamp"])

        # Query with exact event time as end
        events = tracker.get_events_by_timeframe("asset1", end_time=event_time)
        assert len(events) == 1

    def test_timeframe_with_both_boundaries(self):
        """Test filtering with both start and end time"""
        tracker = AnalyticsTracker()

        # Track multiple events
        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset1", EventType.PLAY)
        tracker.track_event("asset1", EventType.CLICK)

        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        events = tracker.get_events_by_timeframe(
            "asset1", start_time=past, end_time=future
        )
        assert len(events) == 3

    def test_zero_results_timeframe(self):
        """Test timeframe that excludes all events"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)

        # Query for events in the future
        future_start = datetime.now(timezone.utc) + timedelta(days=1)
        future_end = datetime.now(timezone.utc) + timedelta(days=2)

        events = tracker.get_events_by_timeframe(
            "asset1", start_time=future_start, end_time=future_end
        )
        assert len(events) == 0


class TestTopAssetsEdgeCases:
    """Test edge cases for top assets functionality"""

    def test_get_top_assets_empty_tracker(self):
        """Test getting top assets when no events exist"""
        tracker = AnalyticsTracker()
        top_assets = tracker.get_top_assets(metric="views", limit=10)
        assert top_assets == []

    def test_get_top_assets_invalid_metric(self):
        """Test sorting by non-existent metric defaults to 0"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset2", EventType.VIEW)

        # Non-existent metric should not crash
        top_assets = tracker.get_top_assets(metric="nonexistent", limit=10)
        assert len(top_assets) == 2

    def test_get_top_assets_by_plays(self):
        """Test getting top assets by play count"""
        tracker = AnalyticsTracker()

        # Asset 1: 5 plays
        for _ in range(5):
            tracker.track_event("asset1", EventType.PLAY)

        # Asset 2: 10 plays
        for _ in range(10):
            tracker.track_event("asset2", EventType.PLAY)

        top_assets = tracker.get_top_assets(metric="plays", limit=10)
        assert top_assets[0]["asset_id"] == "asset2"
        assert top_assets[0]["plays"] == 10

    def test_get_top_assets_tie_breaking(self):
        """Test behavior when multiple assets have same metric value"""
        tracker = AnalyticsTracker()

        # Both assets have same views
        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset2", EventType.VIEW)

        top_assets = tracker.get_top_assets(metric="views", limit=10)
        assert len(top_assets) == 2
        # Both should have 1 view
        assert all(asset["views"] == 1 for asset in top_assets)


class TestCacheBehavior:
    """Test cache invalidation and behavior"""

    def test_cache_cleared_on_all_events_clear(self):
        """Test that entire cache is cleared when all events are cleared"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset2", EventType.VIEW)

        # Populate cache
        tracker.get_asset_metrics("asset1")
        tracker.get_asset_metrics("asset2")

        assert len(tracker._metrics_cache) == 2

        # Clear all events
        tracker.clear_events()

        assert len(tracker._metrics_cache) == 0

    def test_cache_partial_invalidation(self):
        """Test cache only invalidated for specific asset when clearing"""
        tracker = AnalyticsTracker()

        tracker.track_event("asset1", EventType.VIEW)
        tracker.track_event("asset2", EventType.VIEW)

        # Populate cache
        tracker.get_asset_metrics("asset1")
        tracker.get_asset_metrics("asset2")

        # Clear only asset1
        tracker.clear_events(asset_id="asset1")

        # asset1 should be removed from cache
        assert "asset1" not in tracker._metrics_cache
        # asset2 should still be cached
        assert "asset2" in tracker._metrics_cache


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
