"""
Cross-module integration tests
Tests interactions between Analytics, ShareLinks, and CDN modules
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from analytics import AnalyticsTracker, EventType, Platform
from sharelinks import ShareLinkGenerator, create_asset_hash
from cdn import CDNHelper, CachePolicy, SignedURL


class TestAnalyticsWithShareLinks:
    """Test analytics tracking with share links"""

    def test_track_share_link_clicks_and_views(self):
        """Test complete workflow: create link, track views and clicks"""
        gen = ShareLinkGenerator()
        tracker = AnalyticsTracker()

        # Create share link
        link = gen.create_share_link("asset123", title="Test Asset")

        # Track various events through the link
        tracker.track_event(
            "asset123", EventType.VIEW, Platform.SLACK, short_code=link["short_code"]
        )
        tracker.track_event(
            "asset123", EventType.PLAY, Platform.SLACK, short_code=link["short_code"]
        )
        tracker.track_event(
            "asset123", EventType.CLICK, Platform.SLACK, short_code=link["short_code"]
        )

        # Verify analytics
        metrics = tracker.get_short_link_metrics(link["short_code"])
        assert metrics["views"] == 1
        assert metrics["plays"] == 1
        assert metrics["clicks"] == 1
        assert metrics["ctr"] == 100.0

        # Verify share link tracking
        resolved = gen.resolve_short_link(link["short_code"])
        assert resolved["clicks"] == 1

    def test_multiple_links_same_asset_analytics(self):
        """Test analytics across multiple share links for same asset"""
        gen = ShareLinkGenerator()
        tracker = AnalyticsTracker()

        asset_id = "popular_asset"

        # Create 3 different share links
        link1 = gen.create_share_link(asset_id, title="Link 1")
        link2 = gen.create_share_link(asset_id, title="Link 2")
        link3 = gen.create_share_link(asset_id, title="Link 3")

        # Track events through different links
        # Link 1: 10 views, 5 clicks
        for _ in range(10):
            tracker.track_event(
                asset_id, EventType.VIEW, short_code=link1["short_code"]
            )
        for _ in range(5):
            tracker.track_event(
                asset_id, EventType.CLICK, short_code=link1["short_code"]
            )

        # Link 2: 20 views, 10 clicks
        for _ in range(20):
            tracker.track_event(
                asset_id, EventType.VIEW, short_code=link2["short_code"]
            )
        for _ in range(10):
            tracker.track_event(
                asset_id, EventType.CLICK, short_code=link2["short_code"]
            )

        # Link 3: 5 views, 1 click
        for _ in range(5):
            tracker.track_event(
                asset_id, EventType.VIEW, short_code=link3["short_code"]
            )
        tracker.track_event(asset_id, EventType.CLICK, short_code=link3["short_code"])

        # Verify individual link metrics
        metrics1 = tracker.get_short_link_metrics(link1["short_code"])
        metrics2 = tracker.get_short_link_metrics(link2["short_code"])
        metrics3 = tracker.get_short_link_metrics(link3["short_code"])

        assert metrics1["ctr"] == 50.0
        assert metrics2["ctr"] == 50.0
        assert metrics3["ctr"] == 20.0

        # Verify aggregate asset metrics
        asset_metrics = tracker.get_asset_metrics(asset_id)
        assert asset_metrics["views"] == 35
        assert asset_metrics["clicks"] == 16

    def test_platform_breakdown_with_share_links(self):
        """Test platform analytics with share links"""
        gen = ShareLinkGenerator()
        tracker = AnalyticsTracker()

        asset_id = "multi_platform_asset"
        link = gen.create_share_link(asset_id)

        # Share on different platforms
        tracker.track_event(
            asset_id, EventType.VIEW, Platform.SLACK, short_code=link["short_code"]
        )
        tracker.track_event(
            asset_id, EventType.VIEW, Platform.DISCORD, short_code=link["short_code"]
        )
        tracker.track_event(
            asset_id, EventType.VIEW, Platform.TWITTER, short_code=link["short_code"]
        )
        tracker.track_event(
            asset_id, EventType.CLICK, Platform.SLACK, short_code=link["short_code"]
        )

        # Check platform breakdown
        platform_metrics = tracker.get_platform_metrics(asset_id)
        assert len(platform_metrics) == 3
        assert platform_metrics["slack"]["views"] == 1
        assert platform_metrics["slack"]["clicks"] == 1


class TestCDNWithShareLinks:
    """Test CDN functionality with share links"""

    def test_signed_url_for_share_link(self):
        """Test creating signed URLs for assets with share links"""
        gen = ShareLinkGenerator()
        cdn = CDNHelper(secret_key="test-secret")

        # Create share link
        link = gen.create_share_link("asset_cdn_123")

        # Create signed CDN URL for the canonical URL
        signed_url = cdn.create_signed_asset_url(link["canonical_url"])

        # Validate it
        is_valid, error = cdn.validate_asset_url(signed_url)
        assert is_valid is True
        assert error is None

    def test_cdn_headers_for_shared_asset(self):
        """Test getting CDN headers for a shared asset"""
        gen = ShareLinkGenerator()
        cdn = CDNHelper()

        # Create share link for a GIF
        link = gen.create_share_link("gif_asset_456")

        # Get CDN headers for serving this asset
        headers, range_spec, status = cdn.get_asset_headers(
            content_type="image/gif",
            content_length=2048576,  # ~2MB
            is_immutable=False,
            cache_duration=CachePolicy.LONG_CACHE,
        )

        assert status == 200
        assert "Cache-Control" in headers
        assert headers["Content-Type"] == "image/gif"

    def test_range_request_with_share_link_analytics(self):
        """Test range requests tracked in analytics"""
        gen = ShareLinkGenerator()
        cdn = CDNHelper()
        tracker = AnalyticsTracker()

        asset_id = "video_asset"
        link = gen.create_share_link(asset_id, title="Video Asset")

        # Simulate progressive video loading with range requests
        content_length = 10485760  # 10MB
        chunk_size = 1048576  # 1MB

        for i in range(3):
            start = i * chunk_size
            end = start + chunk_size - 1

            # Get CDN headers for range
            headers, range_spec, status = cdn.get_asset_headers(
                content_type="video/mp4",
                content_length=content_length,
                range_header=f"bytes={start}-{end}",
            )

            assert status == 206

            # Track as a view or play event
            if i == 0:
                tracker.track_event(
                    asset_id, EventType.VIEW, short_code=link["short_code"]
                )
            tracker.track_event(asset_id, EventType.PLAY, short_code=link["short_code"])

        # Verify analytics
        metrics = tracker.get_short_link_metrics(link["short_code"])
        assert metrics["views"] == 1
        assert metrics["plays"] == 3


class TestFullWorkflowIntegration:
    """Test complete end-to-end workflows"""

    def test_complete_asset_lifecycle(self):
        """Test complete lifecycle: upload -> hash -> link -> CDN -> analytics"""
        # Step 1: Create and hash asset file
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f:
            f.write(b"GIF89a" + b"\x00" * 1000)  # Mock GIF data
            temp_path = f.name

        try:
            # Step 2: Hash the file
            content_hash = create_asset_hash(temp_path)
            assert len(content_hash) == 64

            # Step 3: Generate asset ID from hash
            gen = ShareLinkGenerator()
            asset_id = gen.generate_hash_based_id(content_hash)
            assert len(asset_id) == 16

            # Step 4: Create share link
            link = gen.create_share_link(asset_id, title="My GIF", tags=["test"])
            assert link["canonical_url"] == f"https://gifdist.io/a/{asset_id}"

            # Step 5: Create signed CDN URL
            cdn = CDNHelper(secret_key="production-secret")
            signed_url = cdn.create_signed_asset_url(
                link["canonical_url"], expiration_seconds=3600
            )

            # Step 6: Validate signed URL
            is_valid, error = cdn.validate_asset_url(signed_url)
            assert is_valid is True

            # Step 7: Get CDN headers for delivery
            headers, _, status = cdn.get_asset_headers(
                content_type="image/gif",
                content_length=1006,
                is_immutable=True,
                cache_duration=CachePolicy.IMMUTABLE_CACHE,
            )
            assert "immutable" in headers["Cache-Control"]

            # Step 8: Track analytics events
            tracker = AnalyticsTracker()
            tracker.track_event(
                asset_id, EventType.VIEW, Platform.SLACK, short_code=link["short_code"]
            )
            tracker.track_event(
                asset_id, EventType.PLAY, Platform.SLACK, short_code=link["short_code"]
            )
            tracker.track_event(
                asset_id, EventType.CLICK, Platform.SLACK, short_code=link["short_code"]
            )

            # Step 9: Verify complete analytics
            metrics = tracker.get_asset_metrics(asset_id)
            assert metrics["views"] == 1
            assert metrics["plays"] == 1
            assert metrics["clicks"] == 1
            assert metrics["ctr"] == 100.0

            link_metrics = tracker.get_short_link_metrics(link["short_code"])
            assert link_metrics["asset_id"] == asset_id

            # Step 10: Verify share link resolution
            resolved = gen.resolve_short_link(link["short_code"])
            assert resolved["asset_id"] == asset_id
            assert resolved["title"] == "My GIF"

        finally:
            os.unlink(temp_path)

    def test_viral_content_scenario(self):
        """Test scenario of viral content shared across platforms"""
        # Setup
        gen = ShareLinkGenerator()
        tracker = AnalyticsTracker()
        cdn = CDNHelper(secret_key="viral-key")

        # Upload viral GIF
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f:
            f.write(b"GIF89a" + b"\xff" * 5000)
            temp_path = f.name

        try:
            content_hash = create_asset_hash(temp_path)
            asset_id = gen.generate_hash_based_id(content_hash)

            # Create multiple share links for different platforms
            slack_link = gen.create_share_link(asset_id, title="Check this out!")
            twitter_link = gen.create_share_link(asset_id, title="Going viral!")
            discord_link = gen.create_share_link(asset_id, title="Epic GIF")

            # Create signed CDN URLs
            slack_cdn = cdn.create_signed_asset_url(slack_link["canonical_url"])
            twitter_cdn = cdn.create_signed_asset_url(twitter_link["canonical_url"])
            discord_cdn = cdn.create_signed_asset_url(discord_link["canonical_url"])

            # Simulate viral spread
            platforms_events = [
                (Platform.SLACK, slack_link["short_code"], 1000),
                (Platform.TWITTER, twitter_link["short_code"], 5000),
                (Platform.DISCORD, discord_link["short_code"], 2000),
            ]

            for platform, short_code, view_count in platforms_events:
                for _ in range(view_count):
                    tracker.track_event(
                        asset_id, EventType.VIEW, platform, short_code=short_code
                    )
                # 10% click through rate
                for _ in range(view_count // 10):
                    tracker.track_event(
                        asset_id, EventType.CLICK, platform, short_code=short_code
                    )

            # Analyze viral performance
            asset_metrics = tracker.get_asset_metrics(asset_id)
            assert asset_metrics["views"] == 8000
            assert asset_metrics["clicks"] == 800
            assert asset_metrics["ctr"] == 10.0

            platform_metrics = tracker.get_platform_metrics(asset_id)
            assert platform_metrics["twitter"]["views"] == 5000
            assert platform_metrics["slack"]["views"] == 1000
            assert platform_metrics["discord"]["views"] == 2000

            # Get top performing link
            twitter_metrics = tracker.get_short_link_metrics(twitter_link["short_code"])
            assert twitter_metrics["views"] == 5000

        finally:
            os.unlink(temp_path)

    def test_content_deduplication_workflow(self):
        """Test deduplication of identical content"""
        gen = ShareLinkGenerator()

        # Create two identical files
        content = b"GIF89a" + b"\xab" * 2000

        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f2:
            f2.write(content)
            path2 = f2.name

        try:
            # Hash both files
            hash1 = create_asset_hash(path1)
            hash2 = create_asset_hash(path2)

            # Hashes should be identical
            assert hash1 == hash2

            # Generate asset IDs
            id1 = gen.generate_hash_based_id(hash1)
            id2 = gen.generate_hash_based_id(hash2)

            # IDs should be identical (deduplication)
            assert id1 == id2

            # Creating share links will use same asset ID
            link1 = gen.create_share_link(id1, title="First upload")
            link2 = gen.create_share_link(id2, title="Duplicate upload")

            # Different short codes
            assert link1["short_code"] != link2["short_code"]

            # But same canonical URL (same asset)
            assert link1["canonical_url"] == link2["canonical_url"]

        finally:
            os.unlink(path1)
            os.unlink(path2)


class TestConcurrentAccessPatterns:
    """Test patterns simulating concurrent access"""

    def test_simultaneous_analytics_and_link_resolution(self):
        """Test tracking analytics while resolving links"""
        gen = ShareLinkGenerator()
        tracker = AnalyticsTracker()

        asset_id = "concurrent_asset"
        link = gen.create_share_link(asset_id)

        # Simulate interleaved operations
        for i in range(100):
            # Track event
            tracker.track_event(asset_id, EventType.VIEW, short_code=link["short_code"])

            # Resolve link (increments click counter)
            resolved = gen.resolve_short_link(link["short_code"])
            assert resolved is not None

            # Get metrics
            metrics = tracker.get_short_link_metrics(link["short_code"])
            assert metrics["views"] == i + 1

        # Final verification
        assert gen._links_db[link["short_code"]]["clicks"] == 100
        final_metrics = tracker.get_asset_metrics(asset_id)
        assert final_metrics["views"] == 100

    def test_multiple_cdn_requests_same_asset(self):
        """Test multiple simultaneous CDN requests for same asset"""
        cdn = CDNHelper()
        gen = ShareLinkGenerator()

        asset_id = "popular_video"
        link = gen.create_share_link(asset_id)
        content_length = 20971520  # 20MB

        # Simulate multiple clients requesting different ranges
        ranges = [
            "bytes=0-1048575",  # Client 1: first MB
            "bytes=1048576-2097151",  # Client 2: second MB
            "bytes=0-1048575",  # Client 3: first MB again
            "bytes=10485760-11534335",  # Client 4: chunk from middle
        ]

        results = []
        for range_header in ranges:
            headers, range_spec, status = cdn.get_asset_headers(
                content_type="video/mp4",
                content_length=content_length,
                range_header=range_header,
                cache_duration=CachePolicy.LONG_CACHE,
            )
            results.append((status, range_spec))

        # All should succeed
        assert all(status == 206 for status, _ in results)
        assert results[0][1] == results[2][1]  # Same range for clients 1 and 3


class TestErrorHandlingAcrossModules:
    """Test error handling in cross-module scenarios"""

    def test_analytics_with_nonexistent_short_code(self):
        """Test analytics for short code that doesn't exist"""
        tracker = AnalyticsTracker()

        # Track event with non-existent short code (analytics doesn't validate codes)
        event = tracker.track_event("asset1", EventType.VIEW, short_code="nonexistent")
        assert event["short_code"] == "nonexistent"

        # Get metrics for the short code we just created
        metrics = tracker.get_short_link_metrics("nonexistent")
        # Analytics tracks events regardless of whether the link exists in ShareLinkGenerator
        assert metrics["views"] == 1
        assert metrics["asset_id"] == "asset1"

    def test_cdn_signed_url_with_invalid_share_link_url(self):
        """Test CDN signing with malformed share link URL"""
        cdn = CDNHelper(secret_key="test")

        # Try to sign a malformed URL
        url = cdn.create_signed_asset_url("not-a-valid-url")
        # Should still create a signed URL (validation is CDN's job)
        assert "signature=" in url

    def test_hash_collision_handling(self):
        """Test handling of hash prefix collisions (very rare)"""
        gen = ShareLinkGenerator()

        # Generate IDs from similar hashes
        hash1 = "abcdef1234567890" + "0" * 48
        hash2 = "abcdef1234567890" + "1" * 48

        id1 = gen.generate_hash_based_id(hash1)
        id2 = gen.generate_hash_based_id(hash2)

        # First 16 chars are same, so IDs collide
        assert id1 == id2

        # Creating links should still work (different short codes)
        link1 = gen.create_share_link(id1, title="First")
        link2 = gen.create_share_link(id2, title="Second")

        assert link1["short_code"] != link2["short_code"]
        assert link1["canonical_url"] == link2["canonical_url"]


class TestPerformanceIntegration:
    """Test performance characteristics of integrated workflows"""

    def test_bulk_asset_processing(self):
        """Test processing many assets through complete pipeline"""
        gen = ShareLinkGenerator()
        tracker = AnalyticsTracker()
        cdn = CDNHelper(secret_key="bulk-test")

        # Process 100 assets
        for i in range(100):
            asset_id = f"asset_{i}"

            # Create share link
            link = gen.create_share_link(asset_id, title=f"Asset {i}")

            # Create signed URL
            signed = cdn.create_signed_asset_url(link["canonical_url"])

            # Track some events
            tracker.track_event(asset_id, EventType.VIEW, short_code=link["short_code"])

            if i % 10 == 0:
                tracker.track_event(
                    asset_id, EventType.CLICK, short_code=link["short_code"]
                )

        # Verify all processed
        assert len(gen._links_db) == 100
        assert len(tracker._events) == 110  # 100 views + 10 clicks

        top_assets = tracker.get_top_assets(metric="clicks", limit=10)
        assert len(top_assets) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
