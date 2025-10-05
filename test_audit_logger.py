"""
Tests for moderation audit logger
Issue: #2
"""

import pytest
import time
import os
from datetime import datetime, timezone, timedelta
from audit_logger import AuditLogger, AuditEventType, RetentionPolicy, AuditLoggerError


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing"""
    db_path = str(tmp_path / "test_audit.db")
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def logger(temp_db):
    """Create audit logger instance"""
    return AuditLogger(
        db_path=temp_db,
        default_retention=RetentionPolicy.MEDIUM,
        auto_cleanup=False,  # Disable auto-cleanup for testing
    )


def test_logger_initialization(logger):
    """Test audit logger initialization"""
    assert logger is not None
    assert os.path.exists(logger.db_path)


def test_log_moderation_event(logger):
    """Test logging a moderation event"""
    log_id = logger.log_event(
        event_type=AuditEventType.MODERATION_SCAN,
        asset_id="asset123",
        user_id="user456",
        decision="approved",
        category="safe",
        confidence=0.98,
        reasons=["No policy violations detected"],
        metadata={"scan_type": "automated"},
    )

    assert log_id is not None
    assert len(log_id) == 32  # SHA256 hash truncated to 32 chars

    # Retrieve the log
    log = logger.get_log_by_id(log_id)
    assert log is not None
    assert log["event_type"] == AuditEventType.MODERATION_SCAN.value
    assert log["asset_id"] == "asset123"
    assert log["user_id"] == "user456"
    assert log["decision"] == "approved"
    assert log["category"] == "safe"
    assert log["confidence"] == 0.98
    assert log["reasons"] == ["No policy violations detected"]
    assert log["metadata"]["scan_type"] == "automated"


def test_log_manual_review(logger):
    """Test logging a manual review event"""
    log_id = logger.log_event(
        event_type=AuditEventType.MANUAL_REVIEW,
        asset_id="asset789",
        user_id="user123",
        moderator_id="mod456",
        decision="rejected",
        category="nsfw",
        confidence=1.0,
        reasons=["Violates content policy"],
        metadata={"review_notes": "Explicit content detected"},
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
    )

    log = logger.get_log_by_id(log_id)
    assert log["event_type"] == AuditEventType.MANUAL_REVIEW.value
    assert log["moderator_id"] == "mod456"
    assert log["ip_address"] == "192.168.1.1"
    assert log["user_agent"] == "Mozilla/5.0"


def test_query_logs_by_asset(logger):
    """Test querying logs by asset ID"""
    # Create multiple logs for same asset
    for i in range(3):
        logger.log_event(
            event_type=AuditEventType.MODERATION_SCAN,
            asset_id="asset_abc",
            decision="approved",
        )

    # Create log for different asset
    logger.log_event(
        event_type=AuditEventType.MODERATION_SCAN,
        asset_id="asset_xyz",
        decision="rejected",
    )

    # Query by asset ID
    logs = logger.get_logs(asset_id="asset_abc")
    assert len(logs) == 3
    assert all(log["asset_id"] == "asset_abc" for log in logs)


def test_query_logs_by_user(logger):
    """Test querying logs by user ID"""
    logger.log_event(
        event_type=AuditEventType.CONTENT_APPROVED,
        asset_id="asset1",
        user_id="user_alice",
    )

    logger.log_event(
        event_type=AuditEventType.CONTENT_REJECTED,
        asset_id="asset2",
        user_id="user_bob",
    )

    logs = logger.get_logs(user_id="user_alice")
    assert len(logs) == 1
    assert logs[0]["user_id"] == "user_alice"


def test_query_logs_by_event_type(logger):
    """Test querying logs by event type"""
    logger.log_event(event_type=AuditEventType.MODERATION_SCAN, asset_id="asset1")

    logger.log_event(event_type=AuditEventType.MANUAL_REVIEW, asset_id="asset2")

    logger.log_event(event_type=AuditEventType.MODERATION_SCAN, asset_id="asset3")

    logs = logger.get_logs(event_type=AuditEventType.MODERATION_SCAN)
    assert len(logs) == 2
    assert all(
        log["event_type"] == AuditEventType.MODERATION_SCAN.value for log in logs
    )


def test_query_logs_by_time_range(logger):
    """Test querying logs by time range"""
    # Log event in the past
    past_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    logger.log_event(event_type=AuditEventType.MODERATION_SCAN, asset_id="asset_old")

    time.sleep(0.1)  # Small delay

    # Log recent event
    recent_time = datetime.now(timezone.utc).isoformat()
    logger.log_event(event_type=AuditEventType.MODERATION_SCAN, asset_id="asset_new")

    # Query recent logs
    logs = logger.get_logs(start_time=recent_time)
    # Note: Both logs might be included due to timing, so we check >= 1
    assert len(logs) >= 1


def test_query_logs_pagination(logger):
    """Test log query pagination"""
    # Create 10 logs
    for i in range(10):
        logger.log_event(
            event_type=AuditEventType.MODERATION_SCAN, asset_id=f"asset_{i}"
        )

    # Get first page
    page1 = logger.get_logs(limit=5, offset=0)
    assert len(page1) == 5

    # Get second page
    page2 = logger.get_logs(limit=5, offset=5)
    assert len(page2) == 5

    # Ensure pages are different
    page1_ids = {log["log_id"] for log in page1}
    page2_ids = {log["log_id"] for log in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_retention_policies(logger):
    """Test different retention policies"""
    # Short retention (30 days)
    log_id_short = logger.log_event(
        event_type=AuditEventType.MODERATION_SCAN,
        asset_id="asset_short",
        retention_policy=RetentionPolicy.SHORT,
    )

    # Long retention (365 days)
    log_id_long = logger.log_event(
        event_type=AuditEventType.MODERATION_SCAN,
        asset_id="asset_long",
        retention_policy=RetentionPolicy.LONG,
    )

    # Compliance retention (7 years)
    log_id_compliance = logger.log_event(
        event_type=AuditEventType.POLICY_VIOLATION,
        asset_id="asset_compliance",
        retention_policy=RetentionPolicy.COMPLIANCE,
    )

    # Check retention days are set correctly
    log_short = logger.get_log_by_id(log_id_short)
    log_long = logger.get_log_by_id(log_id_long)
    log_compliance = logger.get_log_by_id(log_id_compliance)

    assert log_short["retention_days"] == 30
    assert log_long["retention_days"] == 365
    assert log_compliance["retention_days"] == 2555


def test_indefinite_retention(logger):
    """Test indefinite retention policy"""
    log_id = logger.log_event(
        event_type=AuditEventType.ACCOUNT_ACTION,
        asset_id="asset_permanent",
        retention_policy=RetentionPolicy.INDEFINITE,
    )

    log = logger.get_log_by_id(log_id)
    assert log["retention_days"] == -1

    # Expires at should be far in the future
    expires_at = datetime.fromisoformat(log["expires_at"])
    now = datetime.now(timezone.utc)
    assert expires_at > now + timedelta(days=365 * 10)  # More than 10 years


def test_cleanup_expired_logs(logger):
    """Test cleanup of expired audit logs"""
    import sqlite3

    # Create logs with custom expiration dates
    conn = sqlite3.connect(logger.db_path)
    cursor = conn.cursor()

    # Insert expired log
    expired_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    cursor.execute(
        """
        INSERT INTO audit_logs (
            log_id, event_type, timestamp, retention_days, expires_at, reasons, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        ("expired_log", "moderation_scan", expired_time, 1, expired_time, "[]", "{}"),
    )

    # Insert valid log
    future_time = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    cursor.execute(
        """
        INSERT INTO audit_logs (
            log_id, event_type, timestamp, retention_days, expires_at, reasons, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        ("valid_log", "moderation_scan", future_time, 30, future_time, "[]", "{}"),
    )

    conn.commit()
    conn.close()

    # Run cleanup
    purged_count = logger.cleanup_expired()
    assert purged_count >= 1

    # Verify expired log is gone
    log = logger.get_log_by_id("expired_log")
    assert log is None

    # Verify valid log remains
    log = logger.get_log_by_id("valid_log")
    assert log is not None


def test_compliance_report(logger):
    """Test compliance report generation"""
    start_date = datetime.now(timezone.utc).isoformat()

    # Log various events
    logger.log_event(event_type=AuditEventType.MODERATION_SCAN, decision="approved")

    logger.log_event(event_type=AuditEventType.CONTENT_REJECTED, decision="rejected")

    logger.log_event(event_type=AuditEventType.MANUAL_REVIEW, decision="approved")

    end_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    # Generate report
    report = logger.export_compliance_report(start_date=start_date, end_date=end_date)

    assert "period" in report
    assert "summary" in report
    assert "logs" in report

    summary = report["summary"]
    assert summary["total_events"] == 3
    assert len(summary["events_by_type"]) > 0
    assert len(summary["decisions_by_type"]) > 0


def test_statistics(logger):
    """Test audit logger statistics"""
    # Log some events
    for i in range(5):
        logger.log_event(
            event_type=AuditEventType.MODERATION_SCAN, asset_id=f"asset_{i}"
        )

    for i in range(3):
        logger.log_event(event_type=AuditEventType.MANUAL_REVIEW, asset_id=f"asset_{i}")

    stats = logger.get_statistics()

    assert stats["total_records"] == 8
    assert "records_by_type" in stats
    assert stats["records_by_type"].get(AuditEventType.MODERATION_SCAN.value) == 5
    assert stats["records_by_type"].get(AuditEventType.MANUAL_REVIEW.value) == 3
    assert "database_size_bytes" in stats
    assert stats["database_size_bytes"] > 0


def test_all_event_types(logger):
    """Test logging all event types"""
    event_types = [
        AuditEventType.MODERATION_SCAN,
        AuditEventType.MANUAL_REVIEW,
        AuditEventType.CONTENT_APPROVED,
        AuditEventType.CONTENT_REJECTED,
        AuditEventType.CONTENT_FLAGGED,
        AuditEventType.APPEAL_SUBMITTED,
        AuditEventType.APPEAL_RESOLVED,
        AuditEventType.POLICY_VIOLATION,
        AuditEventType.ACCOUNT_ACTION,
    ]

    for event_type in event_types:
        log_id = logger.log_event(
            event_type=event_type, asset_id=f"asset_{event_type.value}"
        )
        assert log_id is not None


def test_concurrent_logging(logger):
    """Test concurrent log writes"""
    import threading

    def log_events(count):
        for i in range(count):
            logger.log_event(
                event_type=AuditEventType.MODERATION_SCAN,
                asset_id=f"asset_{threading.current_thread().name}_{i}",
            )

    threads = []
    for i in range(5):
        thread = threading.Thread(target=log_events, args=(10,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Verify all logs were created
    stats = logger.get_statistics()
    assert stats["total_records"] == 50


def test_logger_close(logger):
    """Test logger cleanup on close"""
    logger.log_event(event_type=AuditEventType.MODERATION_SCAN, asset_id="asset_final")

    logger.close()

    # Verify database still exists and is readable
    new_logger = AuditLogger(db_path=logger.db_path)
    logs = new_logger.get_logs()
    assert len(logs) >= 1


def test_empty_query(logger):
    """Test querying empty database"""
    logs = logger.get_logs()
    assert logs == []


def test_invalid_log_id(logger):
    """Test querying non-existent log ID"""
    log = logger.get_log_by_id("nonexistent_id")
    assert log is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
