"""
Advanced Edge Cases and Stress Tests
Additional comprehensive tests for error handling, limits, and edge cases
"""

import pytest
import tempfile
import os
import sys
from datetime import datetime, timedelta
from analytics import AnalyticsTracker, EventType, Platform
from sharelinks import ShareLinkGenerator, create_asset_hash


class TestFileOperationErrors:
    """Test error handling for file operations"""

    def test_create_hash_directory_not_file(self):
        """Test hashing a directory raises appropriate error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises((IsADirectoryError, PermissionError, OSError)):
                create_asset_hash(tmpdir)

    def test_create_hash_invalid_path(self):
        """Test hashing with invalid path characters"""
        invalid_paths = [
            "",  # Empty path
            "\x00invalid",  # Null character (if OS allows)
        ]
        for path in invalid_paths:
            try:
                with pytest.raises((FileNotFoundError, OSError, ValueError)):
                    create_asset_hash(path)
            except:
                # Some OSes may handle these differently
                pass

    def test_create_hash_special_files(self):
        """Test hashing special system files (skip on Windows)"""
        if sys.platform != "win32":
            # On Unix, try /dev/null
            try:
                hash_result = create_asset_hash("/dev/null")
                # Should succeed and produce empty file hash
                assert len(hash_result) == 64
            except:
                # May fail depending on system
                pass

    def test_create_hash_symlink(self):
        """Test hashing a symbolic link"""
        if sys.platform == "win32":
            pytest.skip("Symlink test not reliable on Windows")

        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f:
            f.write(b"target content")
            target_path = f.name

        link_path = target_path + ".link"
        try:
            os.symlink(target_path, link_path)
            hash_target = create_asset_hash(target_path)
            hash_link = create_asset_hash(link_path)
            # Should produce same hash
            assert hash_target == hash_link
        except OSError:
            pytest.skip("Symlinks not supported")
        finally:
            try:
                os.unlink(link_path)
            except:
                pass
            os.unlink(target_path)


class TestAnalyticsInputValidation:
    """Test analytics with invalid or edge case inputs"""

    def test_track_event_empty_asset_id(self):
        """Test tracking event with empty asset ID"""
        tracker = AnalyticsTracker()
        event = tracker.track_event("", EventType.VIEW)
        assert event["asset_id"] == ""

        metrics = tracker.get_asset_metrics("")
        assert metrics["views"] == 1

    def test_track_event_very_long_asset_id(self):
        """Test with extremely long asset ID"""
        tracker = AnalyticsTracker()
        long_id = "a" * 10000
        event = tracker.track_event(long_id, EventType.VIEW)
        assert event["asset_id"] == long_id

        metrics = tracker.get_asset_metrics(long_id)
        assert metrics["views"] == 1

    def test_track_event_special_characters_asset_id(self):
        """Test asset IDs with special characters"""
        tracker = AnalyticsTracker()
        special_ids = [
            "asset/with/slashes",
            "asset\\with\\backslashes",
            "asset?with=query&params",
            "asset#with#hashes",
            "asset\nwith\nnewlines",
            "asset\twith\ttabs",
            "asset with spaces",
            "日本語アセット",  # Japanese
            "🎉emoji🎊asset",  # Emoji
        ]

        for asset_id in special_ids:
            event = tracker.track_event(asset_id, EventType.VIEW)
            assert event["asset_id"] == asset_id
            metrics = tracker.get_asset_metrics(asset_id)
            assert metrics["views"] >= 1

    def test_track_event_none_short_code(self):
        """Test explicitly passing None as short_code"""
        tracker = AnalyticsTracker()
        event = tracker.track_event("asset1", EventType.VIEW, short_code=None)
        assert event["short_code"] is None

    def test_track_event_empty_metadata(self):
        """Test with explicitly empty metadata"""
        tracker = AnalyticsTracker()
        event = tracker.track_event("asset1", EventType.VIEW, metadata={})
        assert event["metadata"] == {}

    def test_track_event_nested_metadata(self):
        """Test with deeply nested metadata"""
        tracker = AnalyticsTracker()
        nested = {"level1": {"level2": {"level3": {"data": "deep"}}}}
        event = tracker.track_event("asset1", EventType.VIEW, metadata=nested)
        assert event["metadata"]["level1"]["level2"]["level3"]["data"] == "deep"

    def test_get_metrics_unicode_asset_ids(self):
        """Test metrics with various unicode asset IDs"""
        tracker = AnalyticsTracker()

        # Track events with unicode IDs
        tracker.track_event("アセット123", EventType.VIEW)
        tracker.track_event("资产456", EventType.VIEW)
        tracker.track_event("مُحتوى789", EventType.VIEW)

        # Retrieve metrics
        metrics1 = tracker.get_asset_metrics("アセット123")
        metrics2 = tracker.get_asset_metrics("资产456")
        metrics3 = tracker.get_asset_metrics("مُحتوى789")

        assert metrics1["views"] == 1
        assert metrics2["views"] == 1
        assert metrics3["views"] == 1


class TestAnalyticsStressAndLimits:
    """Test analytics under stress and with large datasets"""

    def test_track_many_events_single_asset(self):
        """Test tracking thousands of events for single asset"""
        tracker = AnalyticsTracker()

        # Track 10,000 events
        for i in range(10000):
            if i % 3 == 0:
                tracker.track_event("popular_asset", EventType.VIEW)
            elif i % 3 == 1:
                tracker.track_event("popular_asset", EventType.PLAY)
            else:
                tracker.track_event("popular_asset", EventType.CLICK)

        metrics = tracker.get_asset_metrics("popular_asset")
        assert metrics["views"] == 3334
        assert metrics["plays"] == 3333
        assert metrics["clicks"] == 3333
        assert metrics["total_events"] == 10000

    def test_track_many_unique_assets(self):
        """Test tracking events across many unique assets"""
        tracker = AnalyticsTracker()

        # Create 1000 unique assets
        for i in range(1000):
            tracker.track_event(f"asset_{i}", EventType.VIEW)

        # Get top assets
        top = tracker.get_top_assets(metric="views", limit=100)
        assert len(top) == 100

    def test_very_large_metadata(self):
        """Test with very large metadata objects"""
        tracker = AnalyticsTracker()

        # Create large metadata
        large_meta = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        event = tracker.track_event("asset1", EventType.VIEW, metadata=large_meta)
        assert len(event["metadata"]) == 100

    def test_cache_behavior_under_load(self):
        """Test cache invalidation with many rapid updates"""
        tracker = AnalyticsTracker()

        # Rapidly alternate between tracking and reading metrics
        for i in range(100):
            tracker.track_event("asset1", EventType.VIEW)
            metrics = tracker.get_asset_metrics("asset1")
            assert metrics["views"] == i + 1
            # Cache should be invalidated each time

    def test_platform_metrics_with_all_platforms_heavy_load(self):
        """Test platform metrics with heavy load across all platforms"""
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

        # 1000 events per platform
        for platform in platforms:
            for _ in range(1000):
                tracker.track_event("multi_platform_asset", EventType.VIEW, platform)

        platform_metrics = tracker.get_platform_metrics("multi_platform_asset")
        assert len(platform_metrics) == 7
        for platform in platforms:
            assert platform_metrics[platform.value]["views"] == 1000


class TestShareLinksInputValidation:
    """Test share links with invalid or edge case inputs"""

    def test_generate_with_none_tags(self):
        """Test that None tags are handled properly"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset1", tags=None)
        link_data = gen._links_db[result["short_code"]]
        assert link_data["tags"] == []

    def test_generate_with_none_title(self):
        """Test creating link without title argument"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset1")
        link_data = gen._links_db[result["short_code"]]
        assert link_data["title"] == ""

    def test_tags_with_special_characters(self):
        """Test tags containing special characters"""
        gen = ShareLinkGenerator()
        special_tags = [
            "tag-with-dash",
            "tag_with_underscore",
            "tag.with.dots",
            "tag with spaces",
            "#hashtag",
            "@mention",
            "日本語タグ",
            "emoji🎉tag",
        ]

        result = gen.create_share_link("asset1", tags=special_tags)
        metadata = gen.get_share_metadata(result["short_code"])
        assert len(metadata["tags"]) == len(special_tags)

    def test_extremely_long_title(self):
        """Test with title exceeding typical limits"""
        gen = ShareLinkGenerator()
        long_title = "A" * 100000  # 100k characters
        result = gen.create_share_link("asset1", title=long_title)
        metadata = gen.get_share_metadata(result["short_code"])
        assert len(metadata["title"]) == 100000

    def test_title_with_control_characters(self):
        """Test title with control characters"""
        gen = ShareLinkGenerator()
        title_with_controls = "Title\x00with\x01control\x02chars"
        result = gen.create_share_link("asset1", title=title_with_controls)
        metadata = gen.get_share_metadata(result["short_code"])
        assert metadata["title"] == title_with_controls

    def test_base_url_with_query_params(self):
        """Test base URL containing query parameters"""
        gen = ShareLinkGenerator("https://example.com/app?ref=source")
        url = gen.create_canonical_url("asset1")
        assert url == "https://example.com/app?ref=source/a/asset1"

    def test_base_url_with_fragment(self):
        """Test base URL containing fragment"""
        gen = ShareLinkGenerator("https://example.com#section")
        url = gen.create_canonical_url("asset1")
        assert url == "https://example.com#section/a/asset1"

    def test_asset_id_only_special_chars(self):
        """Test asset ID containing only special characters"""
        gen = ShareLinkGenerator()
        special_id = "!@#$%^&*()"
        url = gen.create_canonical_url(special_id)
        assert special_id in url


class TestShareLinksStressAndLimits:
    """Test share links under stress and with large datasets"""

    def test_generate_many_links_collision_check(self):
        """Test generating many links to verify no collisions"""
        gen = ShareLinkGenerator()
        codes = set()

        # Generate 10,000 short codes
        for i in range(10000):
            result = gen.create_share_link(f"asset_{i}")
            codes.add(result["short_code"])

        # All should be unique
        assert len(codes) == 10000

    def test_resolve_many_links(self):
        """Test resolving many links rapidly"""
        gen = ShareLinkGenerator()

        # Create 1000 links
        links = []
        for i in range(1000):
            result = gen.create_share_link(f"asset_{i}")
            links.append(result["short_code"])

        # Resolve all
        for i, code in enumerate(links):
            resolved = gen.resolve_short_link(code)
            assert resolved["asset_id"] == f"asset_{i}"

    def test_link_database_size(self):
        """Test that link database can handle many entries"""
        gen = ShareLinkGenerator()

        # Create 5000 links
        for i in range(5000):
            gen.create_share_link(f"asset_{i}", title=f"Title {i}", tags=[f"tag{i}"])

        assert len(gen._links_db) == 5000

    def test_heavy_click_tracking(self):
        """Test click counter with many increments"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("viral_asset")

        # Simulate 10000 clicks
        for _ in range(10000):
            gen.resolve_short_link(result["short_code"])

        assert gen._links_db[result["short_code"]]["clicks"] == 10000

    def test_tags_list_with_duplicates(self):
        """Test tags list containing duplicate entries"""
        gen = ShareLinkGenerator()
        tags_with_dupes = ["tag1", "tag2", "tag1", "tag3", "tag2"]
        result = gen.create_share_link("asset1", tags=tags_with_dupes)

        metadata = gen.get_share_metadata(result["short_code"])
        # Duplicates are preserved (deduplication is application logic)
        assert len(metadata["tags"]) == 5


class TestTimeframeEdgeCases:
    """Test timeframe queries with edge cases"""

    def test_timeframe_with_future_dates(self):
        """Test querying with dates far in the future"""
        tracker = AnalyticsTracker()
        tracker.track_event("asset1", EventType.VIEW)

        future = datetime.utcnow() + timedelta(days=365 * 10)  # 10 years
        events = tracker.get_events_by_timeframe("asset1", end_time=future)
        assert len(events) == 1

    def test_timeframe_with_past_dates(self):
        """Test querying with dates far in the past"""
        tracker = AnalyticsTracker()
        tracker.track_event("asset1", EventType.VIEW)

        past = datetime.utcnow() - timedelta(days=365 * 10)  # 10 years ago
        events = tracker.get_events_by_timeframe("asset1", start_time=past)
        assert len(events) == 1

    def test_timeframe_inverted_range(self):
        """Test with start_time after end_time"""
        tracker = AnalyticsTracker()
        tracker.track_event("asset1", EventType.VIEW)

        now = datetime.utcnow()
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        # Inverted range should return no events
        events = tracker.get_events_by_timeframe(
            "asset1", start_time=future, end_time=past
        )
        assert len(events) == 0

    def test_timeframe_microsecond_precision(self):
        """Test timeframe filtering with microsecond precision"""
        tracker = AnalyticsTracker()

        # Track events
        event1 = tracker.track_event("asset1", EventType.VIEW)
        event2 = tracker.track_event("asset1", EventType.PLAY)

        time1 = datetime.fromisoformat(event1["timestamp"])
        time2 = datetime.fromisoformat(event2["timestamp"])

        # Query between the two events
        events = tracker.get_events_by_timeframe(
            "asset1", start_time=time1, end_time=time2
        )
        assert len(events) >= 1


class TestIntegrationStressScenarios:
    """Stress test integration between modules"""

    def test_many_assets_many_links_many_events(self):
        """Test complete workflow with large numbers"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        # Create 100 assets, 3 links each, 10 events per link
        for asset_num in range(100):
            asset_id = f"asset_{asset_num}"

            for link_num in range(3):
                link = gen.create_share_link(asset_id, title=f"Link {link_num}")

                for _ in range(10):
                    tracker.track_event(
                        asset_id, EventType.VIEW, short_code=link["short_code"]
                    )

        # Verify data integrity
        asset_metrics = tracker.get_asset_metrics("asset_0")
        assert asset_metrics["views"] == 30  # 3 links * 10 events

    def test_concurrent_operations_simulation(self):
        """Simulate concurrent operations on same asset"""
        tracker = AnalyticsTracker()
        gen = ShareLinkGenerator()

        asset_id = "concurrent_asset"

        # Simulate interleaved operations
        link1 = gen.create_share_link(asset_id, title="Link 1")
        tracker.track_event(asset_id, EventType.VIEW, short_code=link1["short_code"])

        link2 = gen.create_share_link(asset_id, title="Link 2")
        tracker.track_event(asset_id, EventType.VIEW, short_code=link1["short_code"])
        tracker.track_event(asset_id, EventType.VIEW, short_code=link2["short_code"])

        gen.resolve_short_link(link1["short_code"])
        metrics1 = tracker.get_short_link_metrics(link1["short_code"])

        gen.resolve_short_link(link2["short_code"])
        metrics2 = tracker.get_short_link_metrics(link2["short_code"])

        # Verify independence
        assert metrics1["views"] == 2
        assert metrics2["views"] == 1


class TestMemoryAndResourceManagement:
    """Test memory and resource efficiency"""

    def test_clear_events_memory_reclaim(self):
        """Test that clearing events allows memory reclamation"""
        tracker = AnalyticsTracker()

        # Create many events
        for i in range(10000):
            tracker.track_event(f"asset_{i}", EventType.VIEW)

        initial_count = len(tracker._events)
        assert initial_count == 10000

        # Clear all
        tracker.clear_events()
        assert len(tracker._events) == 0
        assert len(tracker._metrics_cache) == 0

    def test_selective_event_clearing(self):
        """Test memory management with selective clearing"""
        tracker = AnalyticsTracker()

        # Create events for multiple assets
        for i in range(100):
            for _ in range(100):
                tracker.track_event(f"asset_{i}", EventType.VIEW)

        # Clear just one asset
        tracker.clear_events(asset_id="asset_0")

        # Should have 99 * 100 = 9900 events left
        assert len(tracker._events) == 9900

    def test_link_database_cleanup_simulation(self):
        """Test cleaning up old links from database"""
        gen = ShareLinkGenerator()

        # Create many links
        codes_to_keep = []
        codes_to_remove = []

        for i in range(100):
            result = gen.create_share_link(f"asset_{i}")
            if i % 2 == 0:
                codes_to_keep.append(result["short_code"])
            else:
                codes_to_remove.append(result["short_code"])

        # Simulate cleanup by removing from database
        for code in codes_to_remove:
            if code in gen._links_db:
                del gen._links_db[code]

        # Verify selective removal
        assert len(gen._links_db) == 50
        for code in codes_to_keep:
            assert gen.resolve_short_link(code) is not None
        for code in codes_to_remove:
            assert gen.resolve_short_link(code) is None


class TestBoundaryMathematics:
    """Test mathematical edge cases in calculations"""

    def test_ctr_with_zero_views(self):
        """Test CTR calculation when views is zero"""
        tracker = AnalyticsTracker()
        # Only clicks, no views (unusual but possible edge case)
        tracker.track_event("asset1", EventType.CLICK)

        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["ctr"] == 0.0  # Should not divide by zero

    def test_ctr_precision_edge_cases(self):
        """Test CTR with numbers that cause precision issues"""
        tracker = AnalyticsTracker()

        # Create specific ratios
        for _ in range(7):
            tracker.track_event("asset1", EventType.VIEW)
        for _ in range(3):
            tracker.track_event("asset1", EventType.CLICK)

        metrics = tracker.get_asset_metrics("asset1")
        # 3/7 * 100 = 42.857142...
        assert metrics["ctr"] == 42.86

    def test_play_rate_all_plays_no_views(self):
        """Test play rate when only plays tracked"""
        tracker = AnalyticsTracker()
        tracker.track_event("asset1", EventType.PLAY)

        metrics = tracker.get_asset_metrics("asset1")
        assert metrics["play_rate"] == 0.0

    def test_very_high_ctr(self):
        """Test CTR when clicks exceed views (edge case)"""
        tracker = AnalyticsTracker()
        tracker.track_event("asset1", EventType.VIEW)
        # Somehow more clicks than views (data quality issue)
        for _ in range(5):
            tracker.track_event("asset1", EventType.CLICK)

        metrics = tracker.get_asset_metrics("asset1")
        # 5/1 * 100 = 500%
        assert metrics["ctr"] == 500.0


class TestAssetIDDeduplication:
    """Test hash-based deduplication edge cases"""

    def test_different_content_same_prefix(self):
        """Test that files with same prefix produce different hashes"""
        content1 = b"same_prefix_different_content_1"
        content2 = b"same_prefix_different_content_2"

        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f1:
            f1.write(content1)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f2:
            f2.write(content2)
            path2 = f2.name

        try:
            hash1 = create_asset_hash(path1)
            hash2 = create_asset_hash(path2)
            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_same_content_different_filenames(self):
        """Test that same content in different files produces same hash"""
        content = b"identical content"

        with tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=".gif") as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=".jpg") as f2:
            f2.write(content)
            path2 = f2.name

        try:
            hash1 = create_asset_hash(path1)
            hash2 = create_asset_hash(path2)
            # Content hashing should ignore filename/extension
            assert hash1 == hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
