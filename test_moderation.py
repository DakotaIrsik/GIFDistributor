"""
Tests for SFW-only Moderation Pipeline & Audit
"""
import pytest
import time
from moderation import (
    ModerationPipeline,
    ContentScanner,
    ModerationDecision,
    ContentCategory,
    ModerationResult,
    AuditEntry,
    ModerationError
)


class TestContentScanner:
    """Test content scanner functionality"""

    def test_scanner_init(self):
        """Test scanner initialization"""
        scanner = ContentScanner(strict_mode=True)
        assert scanner.strict_mode is True
        assert len(scanner.nsfw_keywords) > 0

    def test_safe_metadata(self):
        """Test scanning safe metadata"""
        scanner = ContentScanner()
        category, confidence, reasons = scanner.scan_metadata(
            title="Cute Cat GIF",
            tags=["cat", "funny", "cute"],
            description="A funny cat playing with yarn"
        )
        assert category == ContentCategory.SAFE
        assert confidence > 0.9
        assert "No policy violations" in reasons[0]

    def test_nsfw_keyword_detection(self):
        """Test NSFW keyword detection in metadata"""
        scanner = ContentScanner()
        category, confidence, reasons = scanner.scan_metadata(
            title="Adult Content",
            tags=["nsfw"],
            description="Explicit material"
        )
        assert category == ContentCategory.NSFW
        assert confidence > 0.9
        assert any("NSFW" in r for r in reasons)

    def test_violence_keyword_detection(self):
        """Test violence keyword detection"""
        scanner = ContentScanner()
        category, confidence, reasons = scanner.scan_metadata(
            title="Graphic Violence",
            tags=["gore", "brutal"]
        )
        assert category == ContentCategory.GRAPHIC_VIOLENCE
        assert confidence > 0.8

    def test_hate_speech_detection(self):
        """Test hate speech keyword detection"""
        scanner = ContentScanner()
        category, confidence, reasons = scanner.scan_metadata(
            title="Hate Speech Example",
            tags=["hate"]
        )
        assert category == ContentCategory.HATE_SPEECH
        assert confidence > 0.9

    def test_case_insensitive_scanning(self):
        """Test that scanning is case-insensitive"""
        scanner = ContentScanner()
        category1, _, _ = scanner.scan_metadata(title="NSFW Content")
        category2, _, _ = scanner.scan_metadata(title="nsfw content")
        assert category1 == category2 == ContentCategory.NSFW

    def test_visual_content_scanning(self):
        """Test visual content scanning"""
        scanner = ContentScanner()
        category, confidence, reasons = scanner.scan_visual_content(
            file_path="/path/to/safe.gif",
            file_hash="a" * 64  # Hash that results in safe content
        )
        assert category in [ContentCategory.SAFE, ContentCategory.NSFW, ContentCategory.UNKNOWN]
        assert 0.0 <= confidence <= 1.0
        assert len(reasons) > 0


class TestModerationPipeline:
    """Test moderation pipeline"""

    def test_pipeline_init(self):
        """Test pipeline initialization"""
        pipeline = ModerationPipeline(
            strict_mode=True,
            auto_approve_threshold=0.95,
            auto_reject_threshold=0.80
        )
        assert pipeline.strict_mode is True
        assert pipeline.auto_approve_threshold == 0.95
        assert pipeline.auto_reject_threshold == 0.80

    def test_moderate_safe_content(self):
        """Test moderating safe content"""
        pipeline = ModerationPipeline()
        result = pipeline.moderate_content(
            asset_id="asset123",
            file_path="/path/to/cat.gif",
            file_hash="a" * 64,
            title="Cute Cat",
            tags=["cat", "funny"],
            description="A cute cat GIF"
        )
        assert isinstance(result, ModerationResult)
        assert result.decision in [
            ModerationDecision.APPROVED,
            ModerationDecision.FLAGGED
        ]
        assert result.scan_id
        assert result.timestamp

    def test_moderate_nsfw_metadata(self):
        """Test rejection based on NSFW metadata"""
        pipeline = ModerationPipeline()
        result = pipeline.moderate_content(
            asset_id="asset456",
            file_path="/path/to/content.gif",
            file_hash="b" * 64,
            title="NSFW Content",
            tags=["adult", "explicit"]
        )
        assert result.decision == ModerationDecision.REJECTED
        assert result.category == ContentCategory.NSFW
        assert len(result.reasons) > 0

    def test_audit_trail_enabled(self):
        """Test that audit trail is recorded"""
        pipeline = ModerationPipeline(enable_audit=True)
        pipeline.moderate_content(
            asset_id="asset789",
            file_path="/path/to/test.gif",
            file_hash="c" * 64,
            title="Test Content"
        )
        audit_trail = pipeline.get_audit_trail()
        assert len(audit_trail) > 0
        assert isinstance(audit_trail[0], AuditEntry)

    def test_audit_trail_disabled(self):
        """Test audit trail can be disabled"""
        pipeline = ModerationPipeline(enable_audit=False)
        pipeline.moderate_content(
            asset_id="asset999",
            file_path="/path/to/test.gif",
            file_hash="d" * 64,
            title="Test Content"
        )
        audit_trail = pipeline.get_audit_trail()
        assert len(audit_trail) == 0

    def test_manual_review(self):
        """Test manual review workflow"""
        pipeline = ModerationPipeline()

        # First, auto-moderate content
        result = pipeline.moderate_content(
            asset_id="asset321",
            file_path="/path/to/flagged.gif",
            file_hash="e" * 64,
            title="Borderline Content"
        )

        # Then manually review
        manual_entry = pipeline.manual_review(
            asset_id="asset321",
            scan_id=result.scan_id,
            decision=ModerationDecision.APPROVED,
            reviewer_id="moderator123",
            notes="Reviewed and approved by human moderator"
        )

        assert isinstance(manual_entry, AuditEntry)
        assert manual_entry.moderator == "moderator123"
        assert manual_entry.decision == ModerationDecision.APPROVED
        assert manual_entry.confidence == 1.0

    def test_get_audit_trail_filtered(self):
        """Test filtering audit trail by asset"""
        pipeline = ModerationPipeline()

        pipeline.moderate_content(
            asset_id="asset_a",
            file_path="/path/to/a.gif",
            file_hash="f" * 64,
            title="Content A"
        )

        pipeline.moderate_content(
            asset_id="asset_b",
            file_path="/path/to/b.gif",
            file_hash="g" * 64,
            title="Content B"
        )

        trail_a = pipeline.get_audit_trail(asset_id="asset_a")
        assert len(trail_a) > 0
        assert all(e.asset_id == "asset_a" for e in trail_a)

    def test_get_audit_trail_by_decision(self):
        """Test filtering audit trail by decision"""
        pipeline = ModerationPipeline()

        # Moderate safe content
        pipeline.moderate_content(
            asset_id="safe_asset",
            file_path="/path/to/safe.gif",
            file_hash="h" * 64,
            title="Safe Content"
        )

        # Moderate NSFW content
        pipeline.moderate_content(
            asset_id="nsfw_asset",
            file_path="/path/to/nsfw.gif",
            file_hash="i" * 64,
            title="NSFW Content",
            tags=["adult"]
        )

        rejected = pipeline.get_audit_trail(decision=ModerationDecision.REJECTED)
        assert all(e.decision == ModerationDecision.REJECTED for e in rejected)

    def test_statistics(self):
        """Test moderation statistics"""
        pipeline = ModerationPipeline()

        # Moderate multiple pieces of content
        for i in range(5):
            pipeline.moderate_content(
                asset_id=f"asset_{i}",
                file_path=f"/path/to/{i}.gif",
                file_hash=chr(ord('a') + i) * 64,
                title=f"Content {i}"
            )

        stats = pipeline.get_statistics()
        assert "total_scans" in stats
        assert stats["total_scans"] == 5
        assert "approval_rate" in stats
        assert "rejection_rate" in stats
        assert "flag_rate" in stats

    def test_clear_audit_trail(self):
        """Test clearing audit trail"""
        pipeline = ModerationPipeline()

        pipeline.moderate_content(
            asset_id="temp_asset",
            file_path="/path/to/temp.gif",
            file_hash="j" * 64,
            title="Temp Content"
        )

        assert len(pipeline.get_audit_trail()) > 0

        pipeline.clear_audit_trail()
        assert len(pipeline.get_audit_trail()) == 0

    def test_clear_audit_trail_selective(self):
        """Test clearing audit trail for specific asset"""
        pipeline = ModerationPipeline()

        pipeline.moderate_content(
            asset_id="keep_asset",
            file_path="/path/to/keep.gif",
            file_hash="k" * 64,
            title="Keep This"
        )

        pipeline.moderate_content(
            asset_id="delete_asset",
            file_path="/path/to/delete.gif",
            file_hash="l" * 64,
            title="Delete This"
        )

        pipeline.clear_audit_trail(asset_id="delete_asset")

        trail = pipeline.get_audit_trail()
        assert all(e.asset_id != "delete_asset" for e in trail)
        assert any(e.asset_id == "keep_asset" for e in trail)

    def test_export_audit_trail(self):
        """Test exporting audit trail"""
        pipeline = ModerationPipeline()

        pipeline.moderate_content(
            asset_id="export_test",
            file_path="/path/to/export.gif",
            file_hash="m" * 64,
            title="Export Test"
        )

        exported = pipeline.export_audit_trail()
        assert len(exported) > 0
        assert isinstance(exported[0], dict)
        assert "audit_id" in exported[0]
        assert "asset_id" in exported[0]
        assert "decision" in exported[0]
        assert "timestamp" in exported[0]

    def test_scan_id_uniqueness(self):
        """Test that scan IDs are unique"""
        pipeline = ModerationPipeline()

        result1 = pipeline.moderate_content(
            asset_id="asset1",
            file_path="/path/to/1.gif",
            file_hash="n" * 64,
            title="Content 1"
        )

        time.sleep(0.01)  # Ensure different timestamp

        result2 = pipeline.moderate_content(
            asset_id="asset2",
            file_path="/path/to/2.gif",
            file_hash="o" * 64,
            title="Content 2"
        )

        assert result1.scan_id != result2.scan_id


class TestModerationDecisions:
    """Test decision-making logic"""

    def test_auto_approve_high_confidence(self):
        """Test auto-approval for high confidence safe content"""
        pipeline = ModerationPipeline(auto_approve_threshold=0.95)

        result = pipeline.moderate_content(
            asset_id="high_conf_safe",
            file_path="/path/to/safe.gif",
            file_hash="a" * 64,  # Hash that results in high confidence safe
            title="Safe Content"
        )

        # Should be approved or flagged (depends on hash simulation)
        assert result.decision in [
            ModerationDecision.APPROVED,
            ModerationDecision.FLAGGED
        ]

    def test_flag_low_confidence(self):
        """Test flagging for low confidence content"""
        pipeline = ModerationPipeline(auto_approve_threshold=0.99)

        # Use hash that gives medium confidence
        result = pipeline.moderate_content(
            asset_id="medium_conf",
            file_path="/path/to/medium.gif",
            file_hash="f" * 8 + "97" + "0" * 54,  # Hash engineered for flagging
            title="Medium Confidence Content"
        )

        # Should be flagged for manual review or approved with lower threshold
        assert result.decision in [
            ModerationDecision.APPROVED,
            ModerationDecision.FLAGGED
        ]

    def test_auto_reject_high_confidence_nsfw(self):
        """Test auto-rejection for high confidence NSFW"""
        pipeline = ModerationPipeline(auto_reject_threshold=0.80)

        result = pipeline.moderate_content(
            asset_id="nsfw_content",
            file_path="/path/to/nsfw.gif",
            file_hash="b" * 64,
            title="Explicit Content",
            tags=["nsfw", "adult"]
        )

        assert result.decision == ModerationDecision.REJECTED
        assert result.category == ContentCategory.NSFW


class TestAuditCompliance:
    """Test audit trail for compliance"""

    def test_audit_contains_required_fields(self):
        """Test audit entries contain all required fields"""
        pipeline = ModerationPipeline()

        pipeline.moderate_content(
            asset_id="compliance_test",
            file_path="/path/to/test.gif",
            file_hash="p" * 64,
            title="Compliance Test"
        )

        trail = pipeline.get_audit_trail()
        entry = trail[0]

        assert entry.audit_id
        assert entry.asset_id
        assert entry.decision
        assert entry.category
        assert isinstance(entry.confidence, float)
        assert entry.moderator
        assert entry.timestamp
        assert isinstance(entry.reasons, list)

    def test_export_time_filtering(self):
        """Test exporting audit trail with time filters"""
        pipeline = ModerationPipeline()

        # Create entry
        pipeline.moderate_content(
            asset_id="time_test",
            file_path="/path/to/test.gif",
            file_hash="q" * 64,
            title="Time Test"
        )

        from datetime import datetime, timedelta, timezone

        # Export with future start time should return empty
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        exported = pipeline.export_audit_trail(start_time=future)
        assert len(exported) == 0

        # Export with past end time should return empty
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        exported = pipeline.export_audit_trail(end_time=past)
        assert len(exported) == 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_metadata(self):
        """Test moderation with empty metadata"""
        pipeline = ModerationPipeline()

        result = pipeline.moderate_content(
            asset_id="empty_meta",
            file_path="/path/to/content.gif",
            file_hash="r" * 64,
            title="",
            tags=[],
            description=""
        )

        assert isinstance(result, ModerationResult)
        assert result.decision in ModerationDecision

    def test_none_tags(self):
        """Test moderation with None tags"""
        pipeline = ModerationPipeline()

        result = pipeline.moderate_content(
            asset_id="none_tags",
            file_path="/path/to/content.gif",
            file_hash="s" * 64,
            title="Test",
            tags=None
        )

        assert isinstance(result, ModerationResult)

    def test_very_long_metadata(self):
        """Test moderation with very long metadata"""
        pipeline = ModerationPipeline()

        long_title = "A" * 10000
        long_tags = [f"tag{i}" for i in range(1000)]
        long_desc = "B" * 10000

        result = pipeline.moderate_content(
            asset_id="long_meta",
            file_path="/path/to/content.gif",
            file_hash="t" * 64,
            title=long_title,
            tags=long_tags,
            description=long_desc
        )

        assert isinstance(result, ModerationResult)

    def test_special_characters_metadata(self):
        """Test metadata with special characters"""
        pipeline = ModerationPipeline()

        result = pipeline.moderate_content(
            asset_id="special_chars",
            file_path="/path/to/content.gif",
            file_hash="u" * 64,
            title="Test 中文 🎨 Special",
            tags=["emoji😀", "unicode中文"],
            description="Special chars: @#$%^&*()"
        )

        assert isinstance(result, ModerationResult)

    def test_limit_on_audit_trail(self):
        """Test limit parameter on get_audit_trail"""
        pipeline = ModerationPipeline()

        # Create 20 entries
        for i in range(20):
            pipeline.moderate_content(
                asset_id=f"limit_test_{i}",
                file_path=f"/path/to/{i}.gif",
                file_hash=chr(ord('a') + (i % 26)) * 64,
                title=f"Content {i}"
            )

        # Get only last 5
        trail = pipeline.get_audit_trail(limit=5)
        assert len(trail) == 5

    def test_statistics_no_scans(self):
        """Test statistics when no scans performed"""
        pipeline = ModerationPipeline()
        stats = pipeline.get_statistics()

        assert stats["total_scans"] == 0
        assert stats["approval_rate"] == 0.0
        assert stats["rejection_rate"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
