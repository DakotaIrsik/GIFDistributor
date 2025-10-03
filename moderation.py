"""
SFW-only Moderation Pipeline & Audit
Provides content moderation with automated scanning and audit trail
Issue: #25
"""
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class ModerationDecision(Enum):
    """Moderation decision outcomes"""
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"  # Requires manual review
    PENDING = "pending"


class ContentCategory(Enum):
    """Content classification categories"""
    SAFE = "safe"
    NSFW = "nsfw"
    GRAPHIC_VIOLENCE = "graphic_violence"
    HATE_SPEECH = "hate_speech"
    ILLEGAL = "illegal"
    SPAM = "spam"
    UNKNOWN = "unknown"


class ModerationError(Exception):
    """Exception raised when moderation fails"""
    pass


@dataclass
class ModerationResult:
    """Result of content moderation"""
    decision: ModerationDecision
    category: ContentCategory
    confidence: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    scan_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict = field(default_factory=dict)


@dataclass
class AuditEntry:
    """Audit trail entry for moderation actions"""
    audit_id: str
    asset_id: str
    decision: ModerationDecision
    category: ContentCategory
    confidence: float
    moderator: str  # "automated" or user ID
    timestamp: str
    reasons: List[str]
    metadata: Dict = field(default_factory=dict)


class ContentScanner:
    """Simulated content scanner (would integrate with real AI/ML service)"""

    def __init__(self, strict_mode: bool = True):
        """
        Initialize content scanner

        Args:
            strict_mode: If True, flag borderline content for review
        """
        self.strict_mode = strict_mode
        # Simulated keyword blocklist
        self.nsfw_keywords = {
            "explicit", "nude", "adult", "xxx", "porn", "sex",
            "nsfw", "18+", "mature"
        }
        self.violence_keywords = {
            "gore", "blood", "violence", "brutal", "graphic"
        }
        self.hate_keywords = {
            "hate", "slur", "racist", "nazi", "supremacist"
        }

    def scan_metadata(
        self,
        title: str = "",
        tags: Optional[List[str]] = None,
        description: str = ""
    ) -> Tuple[ContentCategory, float, List[str]]:
        """
        Scan text metadata for inappropriate content

        Args:
            title: Asset title
            tags: Asset tags
            description: Asset description

        Returns:
            Tuple of (category, confidence, reasons)
        """
        tags = tags or []
        reasons = []

        # Combine all text for scanning
        text = f"{title} {description} {' '.join(tags)}".lower()

        # Check for NSFW content
        for keyword in self.nsfw_keywords:
            if keyword in text:
                reasons.append(f"NSFW keyword detected: '{keyword}'")
                return ContentCategory.NSFW, 0.95, reasons

        # Check for violence
        for keyword in self.violence_keywords:
            if keyword in text:
                reasons.append(f"Violence keyword detected: '{keyword}'")
                return ContentCategory.GRAPHIC_VIOLENCE, 0.90, reasons

        # Check for hate speech
        for keyword in self.hate_keywords:
            if keyword in text:
                reasons.append(f"Hate speech keyword detected: '{keyword}'")
                return ContentCategory.HATE_SPEECH, 0.95, reasons

        return ContentCategory.SAFE, 0.99, ["No policy violations detected"]

    def scan_visual_content(
        self,
        file_path: str,
        file_hash: str
    ) -> Tuple[ContentCategory, float, List[str]]:
        """
        Scan visual content (simulated - would use AI/ML service)

        Args:
            file_path: Path to content file
            file_hash: Hash of file content

        Returns:
            Tuple of (category, confidence, reasons)
        """
        # Simulate visual AI scanning
        # In production, this would call services like:
        # - AWS Rekognition
        # - Google Cloud Vision AI
        # - Azure Content Moderator
        # - OpenAI Moderation API

        # For simulation, use hash to deterministically classify
        # Convert hash to integer (handle non-hex characters)
        try:
            hash_int = int(file_hash[:8], 16)
        except ValueError:
            # Fall back to sum of character codes for non-hex hashes
            hash_int = sum(ord(c) for c in file_hash[:8])

        # 95% of content is safe in simulation
        if hash_int % 100 < 95:
            return (
                ContentCategory.SAFE,
                0.98,
                ["Visual content analysis passed"]
            )

        # 3% is flagged for review
        if hash_int % 100 < 98:
            return (
                ContentCategory.UNKNOWN,
                0.60,
                ["Low confidence - requires manual review"]
            )

        # 2% is rejected
        return (
            ContentCategory.NSFW,
            0.85,
            ["Visual content detected inappropriate imagery"]
        )


class ModerationPipeline:
    """Main moderation pipeline for content approval"""

    def __init__(
        self,
        strict_mode: bool = True,
        auto_approve_threshold: float = 0.95,
        auto_reject_threshold: float = 0.80,
        enable_audit: bool = True
    ):
        """
        Initialize moderation pipeline

        Args:
            strict_mode: Enable strict content filtering
            auto_approve_threshold: Confidence threshold for auto-approval
            auto_reject_threshold: Confidence threshold for auto-rejection
            enable_audit: Enable audit trail logging
        """
        self.scanner = ContentScanner(strict_mode=strict_mode)
        self.strict_mode = strict_mode
        self.auto_approve_threshold = auto_approve_threshold
        self.auto_reject_threshold = auto_reject_threshold
        self.enable_audit = enable_audit

        # Audit trail storage
        self._audit_trail: List[AuditEntry] = []

        # Statistics
        self._stats = {
            "total_scans": 0,
            "approved": 0,
            "rejected": 0,
            "flagged": 0,
            "pending": 0
        }

    def _generate_scan_id(self, asset_id: str) -> str:
        """Generate unique scan ID"""
        timestamp = str(time.time())
        data = f"{asset_id}{timestamp}".encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def _generate_audit_id(self, scan_id: str) -> str:
        """Generate unique audit ID"""
        timestamp = str(time.time())
        data = f"{scan_id}{timestamp}".encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def moderate_content(
        self,
        asset_id: str,
        file_path: str,
        file_hash: str,
        title: str = "",
        tags: Optional[List[str]] = None,
        description: str = "",
        metadata: Optional[Dict] = None
    ) -> ModerationResult:
        """
        Moderate content through complete pipeline

        Args:
            asset_id: Unique asset identifier
            file_path: Path to content file
            file_hash: Hash of file content
            title: Asset title
            tags: Asset tags
            description: Asset description
            metadata: Additional metadata

        Returns:
            ModerationResult with decision and details
        """
        self._stats["total_scans"] += 1
        scan_id = self._generate_scan_id(asset_id)
        metadata = metadata or {}

        # Step 1: Scan metadata
        meta_category, meta_confidence, meta_reasons = self.scanner.scan_metadata(
            title=title,
            tags=tags,
            description=description
        )

        # Early rejection if metadata fails
        if meta_category != ContentCategory.SAFE:
            result = ModerationResult(
                decision=ModerationDecision.REJECTED,
                category=meta_category,
                confidence=meta_confidence,
                reasons=meta_reasons,
                scan_id=scan_id,
                metadata={"scan_type": "metadata_only"}
            )
            self._record_decision(asset_id, result, "automated")
            return result

        # Step 2: Scan visual content
        visual_category, visual_confidence, visual_reasons = self.scanner.scan_visual_content(
            file_path=file_path,
            file_hash=file_hash
        )

        # Determine overall decision
        reasons = meta_reasons + visual_reasons

        if visual_category == ContentCategory.SAFE:
            # High confidence safe content
            if visual_confidence >= self.auto_approve_threshold:
                decision = ModerationDecision.APPROVED
                category = ContentCategory.SAFE
                confidence = visual_confidence
            else:
                # Lower confidence, flag for review
                decision = ModerationDecision.FLAGGED
                category = ContentCategory.UNKNOWN
                confidence = visual_confidence
                reasons.append(f"Low confidence ({confidence:.2f}) - manual review required")

        elif visual_category == ContentCategory.UNKNOWN:
            # Uncertain content - flag for manual review
            decision = ModerationDecision.FLAGGED
            category = ContentCategory.UNKNOWN
            confidence = visual_confidence

        else:
            # Inappropriate content detected
            if visual_confidence >= self.auto_reject_threshold:
                decision = ModerationDecision.REJECTED
                category = visual_category
                confidence = visual_confidence
            else:
                # Lower confidence rejection - flag for review
                decision = ModerationDecision.FLAGGED
                category = visual_category
                confidence = visual_confidence
                reasons.append(f"Potential violation (confidence: {confidence:.2f}) - manual review required")

        result = ModerationResult(
            decision=decision,
            category=category,
            confidence=confidence,
            reasons=reasons,
            scan_id=scan_id,
            metadata={
                "scan_type": "full",
                "metadata_check": "passed",
                "visual_check": visual_category.value
            }
        )

        self._record_decision(asset_id, result, "automated")
        return result

    def manual_review(
        self,
        asset_id: str,
        scan_id: str,
        decision: ModerationDecision,
        reviewer_id: str,
        notes: str = ""
    ) -> AuditEntry:
        """
        Record manual review decision

        Args:
            asset_id: Asset being reviewed
            scan_id: Original scan ID
            decision: Manual review decision
            reviewer_id: ID of human reviewer
            notes: Review notes

        Returns:
            AuditEntry for the manual review
        """
        audit_id = self._generate_audit_id(scan_id)

        # Determine category based on decision
        if decision == ModerationDecision.APPROVED:
            category = ContentCategory.SAFE
        elif decision == ModerationDecision.REJECTED:
            category = ContentCategory.NSFW  # Default for manual rejection
        else:
            category = ContentCategory.UNKNOWN

        entry = AuditEntry(
            audit_id=audit_id,
            asset_id=asset_id,
            decision=decision,
            category=category,
            confidence=1.0,  # Manual review is definitive
            moderator=reviewer_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reasons=[f"Manual review: {notes}"] if notes else ["Manual review"],
            metadata={
                "scan_id": scan_id,
                "review_type": "manual"
            }
        )

        if self.enable_audit:
            self._audit_trail.append(entry)

        self._stats[decision.value] = self._stats.get(decision.value, 0) + 1

        return entry

    def _record_decision(
        self,
        asset_id: str,
        result: ModerationResult,
        moderator: str
    ) -> None:
        """Record moderation decision in audit trail"""
        if not self.enable_audit:
            return

        audit_id = self._generate_audit_id(result.scan_id)

        entry = AuditEntry(
            audit_id=audit_id,
            asset_id=asset_id,
            decision=result.decision,
            category=result.category,
            confidence=result.confidence,
            moderator=moderator,
            timestamp=result.timestamp,
            reasons=result.reasons,
            metadata=result.metadata
        )

        self._audit_trail.append(entry)
        self._stats[result.decision.value] += 1

    def get_audit_trail(
        self,
        asset_id: Optional[str] = None,
        decision: Optional[ModerationDecision] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """
        Get audit trail entries

        Args:
            asset_id: Filter by asset ID
            decision: Filter by decision type
            limit: Maximum entries to return

        Returns:
            List of audit entries
        """
        entries = self._audit_trail

        if asset_id:
            entries = [e for e in entries if e.asset_id == asset_id]

        if decision:
            entries = [e for e in entries if e.decision == decision]

        return entries[-limit:]

    def get_statistics(self) -> Dict:
        """
        Get moderation statistics

        Returns:
            Dictionary with statistics
        """
        stats = self._stats.copy()

        if stats["total_scans"] > 0:
            stats["approval_rate"] = stats["approved"] / stats["total_scans"] * 100
            stats["rejection_rate"] = stats["rejected"] / stats["total_scans"] * 100
            stats["flag_rate"] = stats["flagged"] / stats["total_scans"] * 100
        else:
            stats["approval_rate"] = 0.0
            stats["rejection_rate"] = 0.0
            stats["flag_rate"] = 0.0

        return stats

    def clear_audit_trail(self, asset_id: Optional[str] = None) -> None:
        """
        Clear audit trail

        Args:
            asset_id: Clear entries for specific asset, or all if None
        """
        if asset_id:
            self._audit_trail = [
                e for e in self._audit_trail if e.asset_id != asset_id
            ]
        else:
            self._audit_trail.clear()

    def export_audit_trail(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict]:
        """
        Export audit trail for compliance reporting

        Args:
            start_time: ISO format start time
            end_time: ISO format end time

        Returns:
            List of audit entries as dictionaries
        """
        entries = self._audit_trail

        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]

        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        return [
            {
                "audit_id": e.audit_id,
                "asset_id": e.asset_id,
                "decision": e.decision.value,
                "category": e.category.value,
                "confidence": e.confidence,
                "moderator": e.moderator,
                "timestamp": e.timestamp,
                "reasons": e.reasons,
                "metadata": e.metadata
            }
            for e in entries
        ]
