"""
Moderation Audit Logger with DB Schema & Retention
Provides persistent audit trail storage with configurable retention policies
Issue: #2
"""
import time
import sqlite3
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from enum import Enum


class AuditEventType(Enum):
    """Types of auditable events"""
    MODERATION_SCAN = "moderation_scan"
    MANUAL_REVIEW = "manual_review"
    CONTENT_APPROVED = "content_approved"
    CONTENT_REJECTED = "content_rejected"
    CONTENT_FLAGGED = "content_flagged"
    APPEAL_SUBMITTED = "appeal_submitted"
    APPEAL_RESOLVED = "appeal_resolved"
    POLICY_VIOLATION = "policy_violation"
    ACCOUNT_ACTION = "account_action"


class RetentionPolicy(Enum):
    """Audit data retention policies"""
    SHORT = 30  # 30 days
    MEDIUM = 90  # 90 days
    LONG = 365  # 1 year
    COMPLIANCE = 2555  # 7 years (legal compliance)
    INDEFINITE = -1  # Never expire


@dataclass
class AuditLog:
    """Audit log entry"""
    log_id: str
    event_type: str
    asset_id: Optional[str]
    user_id: Optional[str]
    moderator_id: Optional[str]
    decision: Optional[str]
    category: Optional[str]
    confidence: Optional[float]
    timestamp: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    reasons: List[str]
    metadata: Dict[str, Any]
    retention_days: int


class AuditLoggerError(Exception):
    """Exception raised when audit logging fails"""
    pass


class AuditLogger:
    """
    Persistent audit logger with database storage and retention policies

    Features:
    - SQLite database for audit trail storage
    - Configurable retention policies
    - Automatic cleanup of expired records
    - Query and export capabilities
    - Compliance reporting
    """

    # Database schema version
    SCHEMA_VERSION = 1

    def __init__(
        self,
        db_path: str = "audit_trail.db",
        default_retention: RetentionPolicy = RetentionPolicy.LONG,
        auto_cleanup: bool = True
    ):
        """
        Initialize audit logger

        Args:
            db_path: Path to SQLite database
            default_retention: Default retention policy
            auto_cleanup: Automatically clean expired records
        """
        self.db_path = db_path
        self.default_retention = default_retention
        self.auto_cleanup = auto_cleanup

        # Initialize database
        self._init_database()

        # Track statistics
        self._stats = {
            "total_logs": 0,
            "logs_by_type": {},
            "cleanup_runs": 0,
            "records_purged": 0
        }

    def _init_database(self) -> None:
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create audit_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                asset_id TEXT,
                user_id TEXT,
                moderator_id TEXT,
                decision TEXT,
                category TEXT,
                confidence REAL,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                reasons TEXT,  -- JSON array
                metadata TEXT,  -- JSON object
                retention_days INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_asset_id
            ON audit_logs(asset_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON audit_logs(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type
            ON audit_logs(event_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON audit_logs(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON audit_logs(expires_at)
        """)

        # Create metadata table for schema version
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Store schema version
        cursor.execute("""
            INSERT OR REPLACE INTO audit_metadata (key, value)
            VALUES ('schema_version', ?)
        """, (str(self.SCHEMA_VERSION),))

        conn.commit()
        conn.close()

    def _generate_log_id(self) -> str:
        """Generate unique log ID"""
        timestamp = str(time.time())
        random_data = str(time.time_ns())
        data = f"{timestamp}{random_data}".encode()
        return hashlib.sha256(data).hexdigest()[:32]

    def _calculate_expiration(self, retention_days: int) -> str:
        """Calculate expiration timestamp"""
        if retention_days == -1:
            # Indefinite retention - far future date
            return (datetime.now(timezone.utc) + timedelta(days=36500)).isoformat()

        expiration = datetime.now(timezone.utc) + timedelta(days=retention_days)
        return expiration.isoformat()

    def log_event(
        self,
        event_type: AuditEventType,
        asset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        moderator_id: Optional[str] = None,
        decision: Optional[str] = None,
        category: Optional[str] = None,
        confidence: Optional[float] = None,
        reasons: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        retention_policy: Optional[RetentionPolicy] = None
    ) -> str:
        """
        Log an audit event

        Args:
            event_type: Type of event being logged
            asset_id: Asset identifier
            user_id: User who triggered the event
            moderator_id: Moderator who performed action
            decision: Moderation decision
            category: Content category
            confidence: Confidence score
            reasons: List of reasons for decision
            metadata: Additional metadata
            ip_address: Client IP address
            user_agent: Client user agent
            retention_policy: Retention policy override

        Returns:
            log_id: Unique log entry identifier
        """
        import json

        log_id = self._generate_log_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        reasons = reasons or []
        metadata = metadata or {}

        # Determine retention period
        policy = retention_policy or self.default_retention
        retention_days = policy.value
        expires_at = self._calculate_expiration(retention_days)

        # Convert lists/dicts to JSON
        reasons_json = json.dumps(reasons)
        metadata_json = json.dumps(metadata)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO audit_logs (
                    log_id, event_type, asset_id, user_id, moderator_id,
                    decision, category, confidence, timestamp, ip_address,
                    user_agent, reasons, metadata, retention_days, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, event_type.value, asset_id, user_id, moderator_id,
                decision, category, confidence, timestamp, ip_address,
                user_agent, reasons_json, metadata_json, retention_days, expires_at
            ))

            conn.commit()

            # Update statistics
            self._stats["total_logs"] += 1
            event_key = event_type.value
            self._stats["logs_by_type"][event_key] = self._stats["logs_by_type"].get(event_key, 0) + 1

            # Run auto cleanup if enabled
            if self.auto_cleanup:
                self._auto_cleanup()

        except sqlite3.Error as e:
            conn.rollback()
            raise AuditLoggerError(f"Failed to log audit event: {e}")
        finally:
            conn.close()

        return log_id

    def get_logs(
        self,
        asset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs

        Args:
            asset_id: Filter by asset ID
            user_id: Filter by user ID
            event_type: Filter by event type
            start_time: ISO format start time
            end_time: ISO format end time
            limit: Maximum records to return
            offset: Offset for pagination

        Returns:
            List of audit log entries
        """
        import json

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if asset_id:
            query += " AND asset_id = ?"
            params.append(asset_id)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            logs = []

            for row in rows:
                log = dict(zip(columns, row))
                # Parse JSON fields
                log["reasons"] = json.loads(log["reasons"])
                log["metadata"] = json.loads(log["metadata"])
                logs.append(log)

            return logs

        except sqlite3.Error as e:
            raise AuditLoggerError(f"Failed to query logs: {e}")
        finally:
            conn.close()

    def get_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific audit log by ID

        Args:
            log_id: Log entry identifier

        Returns:
            Audit log entry or None if not found
        """
        import json

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM audit_logs WHERE log_id = ?",
                (log_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            log = dict(zip(columns, row))
            log["reasons"] = json.loads(log["reasons"])
            log["metadata"] = json.loads(log["metadata"])

            return log

        except sqlite3.Error as e:
            raise AuditLoggerError(f"Failed to get log: {e}")
        finally:
            conn.close()

    def cleanup_expired(self) -> int:
        """
        Remove expired audit logs based on retention policy

        Returns:
            Number of records purged
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        current_time = datetime.now(timezone.utc).isoformat()

        try:
            # Count records to be deleted
            cursor.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE expires_at <= ?",
                (current_time,)
            )
            count = cursor.fetchone()[0]

            # Delete expired records
            cursor.execute(
                "DELETE FROM audit_logs WHERE expires_at <= ?",
                (current_time,)
            )

            conn.commit()

            # Update statistics
            self._stats["cleanup_runs"] += 1
            self._stats["records_purged"] += count

            return count

        except sqlite3.Error as e:
            conn.rollback()
            raise AuditLoggerError(f"Failed to cleanup expired logs: {e}")
        finally:
            conn.close()

    def _auto_cleanup(self) -> None:
        """Automatically cleanup expired records (rate-limited)"""
        # Only run cleanup once per hour
        current_time = time.time()
        last_cleanup = getattr(self, '_last_cleanup', 0)

        if current_time - last_cleanup > 3600:  # 1 hour
            self.cleanup_expired()
            self._last_cleanup = current_time

    def export_compliance_report(
        self,
        start_date: str,
        end_date: str,
        event_types: Optional[List[AuditEventType]] = None
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit period

        Args:
            start_date: ISO format start date
            end_date: ISO format end date
            event_types: Filter by event types

        Returns:
            Compliance report with statistics and logs
        """
        logs = self.get_logs(
            start_time=start_date,
            end_time=end_date,
            limit=10000  # High limit for reports
        )

        if event_types:
            event_values = [e.value for e in event_types]
            logs = [log for log in logs if log["event_type"] in event_values]

        # Calculate statistics
        total_events = len(logs)
        events_by_type = {}
        decisions_by_type = {}

        for log in logs:
            event_type = log["event_type"]
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

            if log["decision"]:
                decision = log["decision"]
                decisions_by_type[decision] = decisions_by_type.get(decision, 0) + 1

        return {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "summary": {
                "total_events": total_events,
                "events_by_type": events_by_type,
                "decisions_by_type": decisions_by_type
            },
            "logs": logs
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit logger statistics

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Count total records
            cursor.execute("SELECT COUNT(*) FROM audit_logs")
            total_records = cursor.fetchone()[0]

            # Count by event type
            cursor.execute("""
                SELECT event_type, COUNT(*)
                FROM audit_logs
                GROUP BY event_type
            """)
            by_type = dict(cursor.fetchall())

            # Count expired but not yet purged
            current_time = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE expires_at <= ?",
                (current_time,)
            )
            expired_count = cursor.fetchone()[0]

            # Database size
            db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0

            return {
                "total_records": total_records,
                "records_by_type": by_type,
                "expired_not_purged": expired_count,
                "database_size_bytes": db_size,
                "cleanup_runs": self._stats["cleanup_runs"],
                "total_records_purged": self._stats["records_purged"]
            }

        except sqlite3.Error as e:
            raise AuditLoggerError(f"Failed to get statistics: {e}")
        finally:
            conn.close()

    def close(self) -> None:
        """Close audit logger and cleanup resources"""
        # Run final cleanup if enabled
        if self.auto_cleanup:
            self.cleanup_expired()
