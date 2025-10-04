"""
Pricing Plans & Quotas Module for GIF Distributor
Implements Free, Pro, and Team pricing tiers with quota management
Issue: #47
Depends on: rate-limits, analytics
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import time


class PlanTier(Enum):
    """Available subscription tiers"""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class QuotaType(Enum):
    """Types of quotas that can be enforced"""
    UPLOADS_PER_MONTH = "uploads_per_month"
    STORAGE_GB = "storage_gb"
    BANDWIDTH_GB = "bandwidth_gb"
    TEAM_MEMBERS = "team_members"
    API_REQUESTS_PER_DAY = "api_requests_per_day"


@dataclass
class PlanFeatures:
    """Features included in a pricing plan"""
    name: str
    tier: PlanTier
    price_monthly_usd: float

    # Upload quotas
    max_uploads_per_month: int
    max_file_size_mb: int

    # Storage quotas
    max_storage_gb: float

    # Bandwidth quotas
    max_bandwidth_gb_per_month: float

    # Team features
    max_team_members: int
    team_collaboration: bool

    # API limits
    api_requests_per_day: int
    api_rate_limit_per_minute: int

    # Platform features
    platform_distribution: List[str]
    analytics_retention_days: int
    priority_support: bool
    custom_branding: bool
    watermark_removal: bool

    # Advanced features
    cdn_enabled: bool
    custom_domain: bool
    webhook_notifications: bool


# Predefined plan configurations
PLAN_CONFIGS = {
    PlanTier.FREE: PlanFeatures(
        name="Free",
        tier=PlanTier.FREE,
        price_monthly_usd=0.0,
        max_uploads_per_month=50,
        max_file_size_mb=10,
        max_storage_gb=1.0,
        max_bandwidth_gb_per_month=5.0,
        max_team_members=1,
        team_collaboration=False,
        api_requests_per_day=100,
        api_rate_limit_per_minute=10,
        platform_distribution=["giphy", "tenor"],
        analytics_retention_days=30,
        priority_support=False,
        custom_branding=False,
        watermark_removal=False,
        cdn_enabled=True,
        custom_domain=False,
        webhook_notifications=False
    ),
    PlanTier.PRO: PlanFeatures(
        name="Pro",
        tier=PlanTier.PRO,
        price_monthly_usd=19.99,
        max_uploads_per_month=500,
        max_file_size_mb=50,
        max_storage_gb=25.0,
        max_bandwidth_gb_per_month=100.0,
        max_team_members=1,
        team_collaboration=False,
        api_requests_per_day=10000,
        api_rate_limit_per_minute=100,
        platform_distribution=["giphy", "tenor", "slack", "discord", "teams"],
        analytics_retention_days=365,
        priority_support=True,
        custom_branding=True,
        watermark_removal=True,
        cdn_enabled=True,
        custom_domain=True,
        webhook_notifications=True
    ),
    PlanTier.TEAM: PlanFeatures(
        name="Team",
        tier=PlanTier.TEAM,
        price_monthly_usd=99.99,
        max_uploads_per_month=5000,
        max_file_size_mb=100,
        max_storage_gb=250.0,
        max_bandwidth_gb_per_month=1000.0,
        max_team_members=10,
        team_collaboration=True,
        api_requests_per_day=100000,
        api_rate_limit_per_minute=1000,
        platform_distribution=["giphy", "tenor", "slack", "discord", "teams"],
        analytics_retention_days=730,
        priority_support=True,
        custom_branding=True,
        watermark_removal=True,
        cdn_enabled=True,
        custom_domain=True,
        webhook_notifications=True
    )
}


@dataclass
class UsageStats:
    """Current usage statistics for a user/account"""
    uploads_this_month: int = 0
    storage_used_gb: float = 0.0
    bandwidth_used_gb_this_month: float = 0.0
    team_members_count: int = 1
    api_requests_today: int = 0

    # Timestamps for period tracking
    month_start: datetime = field(default_factory=lambda: datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0))
    day_start: datetime = field(default_factory=lambda: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))


class QuotaExceededError(Exception):
    """Exception raised when a quota is exceeded"""
    def __init__(self, quota_type: QuotaType, current: float, limit: float):
        self.quota_type = quota_type
        self.current = current
        self.limit = limit
        super().__init__(
            f"Quota exceeded for {quota_type.value}: {current} / {limit}"
        )


class PricingManager:
    """Manages pricing plans and quota enforcement"""

    def __init__(self):
        self._user_plans: Dict[str, PlanTier] = {}
        self._user_usage: Dict[str, UsageStats] = {}

    def assign_plan(self, user_id: str, plan: PlanTier) -> None:
        """
        Assign a pricing plan to a user

        Args:
            user_id: User identifier
            plan: The plan tier to assign
        """
        self._user_plans[user_id] = plan
        if user_id not in self._user_usage:
            self._user_usage[user_id] = UsageStats()

    def get_plan(self, user_id: str) -> PlanFeatures:
        """
        Get the pricing plan for a user

        Args:
            user_id: User identifier

        Returns:
            The plan features for the user's current plan
        """
        plan_tier = self._user_plans.get(user_id, PlanTier.FREE)
        return PLAN_CONFIGS[plan_tier]

    def get_usage(self, user_id: str) -> UsageStats:
        """
        Get current usage statistics for a user

        Args:
            user_id: User identifier

        Returns:
            Current usage statistics
        """
        if user_id not in self._user_usage:
            self._user_usage[user_id] = UsageStats()

        # Reset monthly counters if needed
        usage = self._user_usage[user_id]
        now = datetime.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if usage.month_start < current_month_start:
            usage.uploads_this_month = 0
            usage.bandwidth_used_gb_this_month = 0.0
            usage.month_start = current_month_start

        # Reset daily counters if needed
        current_day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if usage.day_start < current_day_start:
            usage.api_requests_today = 0
            usage.day_start = current_day_start

        return usage

    def check_quota(
        self,
        user_id: str,
        quota_type: QuotaType,
        amount: float = 1.0
    ) -> bool:
        """
        Check if a user has quota available for an action

        Args:
            user_id: User identifier
            quota_type: Type of quota to check
            amount: Amount to check (e.g., file size in MB, number of uploads)

        Returns:
            True if quota is available, False otherwise

        Raises:
            QuotaExceededError: If quota would be exceeded
        """
        plan = self.get_plan(user_id)
        usage = self.get_usage(user_id)

        if quota_type == QuotaType.UPLOADS_PER_MONTH:
            limit = plan.max_uploads_per_month
            current = usage.uploads_this_month
        elif quota_type == QuotaType.STORAGE_GB:
            limit = plan.max_storage_gb
            current = usage.storage_used_gb
        elif quota_type == QuotaType.BANDWIDTH_GB:
            limit = plan.max_bandwidth_gb_per_month
            current = usage.bandwidth_used_gb_this_month
        elif quota_type == QuotaType.TEAM_MEMBERS:
            limit = plan.max_team_members
            current = usage.team_members_count
        elif quota_type == QuotaType.API_REQUESTS_PER_DAY:
            limit = plan.api_requests_per_day
            current = usage.api_requests_today
        else:
            return True  # Unknown quota type, allow

        if current + amount > limit:
            raise QuotaExceededError(quota_type, current, limit)

        return True

    def consume_quota(
        self,
        user_id: str,
        quota_type: QuotaType,
        amount: float = 1.0
    ) -> None:
        """
        Consume quota for a user action

        Args:
            user_id: User identifier
            quota_type: Type of quota to consume
            amount: Amount to consume

        Raises:
            QuotaExceededError: If quota would be exceeded
        """
        # Check quota first
        self.check_quota(user_id, quota_type, amount)

        # Update usage
        usage = self.get_usage(user_id)

        if quota_type == QuotaType.UPLOADS_PER_MONTH:
            usage.uploads_this_month += int(amount)
        elif quota_type == QuotaType.STORAGE_GB:
            usage.storage_used_gb += amount
        elif quota_type == QuotaType.BANDWIDTH_GB:
            usage.bandwidth_used_gb_this_month += amount
        elif quota_type == QuotaType.TEAM_MEMBERS:
            usage.team_members_count += int(amount)
        elif quota_type == QuotaType.API_REQUESTS_PER_DAY:
            usage.api_requests_today += int(amount)

    def get_quota_status(self, user_id: str) -> Dict:
        """
        Get detailed quota status for a user

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing quota limits and current usage
        """
        plan = self.get_plan(user_id)
        usage = self.get_usage(user_id)

        return {
            "plan": plan.name,
            "tier": plan.tier.value,
            "quotas": {
                "uploads": {
                    "used": usage.uploads_this_month,
                    "limit": plan.max_uploads_per_month,
                    "percentage": (usage.uploads_this_month / plan.max_uploads_per_month * 100) if plan.max_uploads_per_month > 0 else 0
                },
                "storage_gb": {
                    "used": usage.storage_used_gb,
                    "limit": plan.max_storage_gb,
                    "percentage": (usage.storage_used_gb / plan.max_storage_gb * 100) if plan.max_storage_gb > 0 else 0
                },
                "bandwidth_gb": {
                    "used": usage.bandwidth_used_gb_this_month,
                    "limit": plan.max_bandwidth_gb_per_month,
                    "percentage": (usage.bandwidth_used_gb_this_month / plan.max_bandwidth_gb_per_month * 100) if plan.max_bandwidth_gb_per_month > 0 else 0
                },
                "team_members": {
                    "used": usage.team_members_count,
                    "limit": plan.max_team_members,
                    "percentage": (usage.team_members_count / plan.max_team_members * 100) if plan.max_team_members > 0 else 0
                },
                "api_requests": {
                    "used": usage.api_requests_today,
                    "limit": plan.api_requests_per_day,
                    "percentage": (usage.api_requests_today / plan.api_requests_per_day * 100) if plan.api_requests_per_day > 0 else 0
                }
            },
            "features": {
                "team_collaboration": plan.team_collaboration,
                "priority_support": plan.priority_support,
                "custom_branding": plan.custom_branding,
                "watermark_removal": plan.watermark_removal,
                "custom_domain": plan.custom_domain,
                "webhook_notifications": plan.webhook_notifications,
                "platforms": plan.platform_distribution,
                "analytics_retention_days": plan.analytics_retention_days
            }
        }

    def can_upgrade(self, user_id: str) -> Dict:
        """
        Check if a user can upgrade and what plans are available

        Args:
            user_id: User identifier

        Returns:
            Dictionary with upgrade options
        """
        current_plan = self._user_plans.get(user_id, PlanTier.FREE)

        upgrade_options = []
        if current_plan == PlanTier.FREE:
            upgrade_options = [
                {
                    "tier": PlanTier.PRO.value,
                    "name": PLAN_CONFIGS[PlanTier.PRO].name,
                    "price": PLAN_CONFIGS[PlanTier.PRO].price_monthly_usd,
                    "benefits": self._get_upgrade_benefits(PlanTier.FREE, PlanTier.PRO)
                },
                {
                    "tier": PlanTier.TEAM.value,
                    "name": PLAN_CONFIGS[PlanTier.TEAM].name,
                    "price": PLAN_CONFIGS[PlanTier.TEAM].price_monthly_usd,
                    "benefits": self._get_upgrade_benefits(PlanTier.FREE, PlanTier.TEAM)
                }
            ]
        elif current_plan == PlanTier.PRO:
            upgrade_options = [
                {
                    "tier": PlanTier.TEAM.value,
                    "name": PLAN_CONFIGS[PlanTier.TEAM].name,
                    "price": PLAN_CONFIGS[PlanTier.TEAM].price_monthly_usd,
                    "benefits": self._get_upgrade_benefits(PlanTier.PRO, PlanTier.TEAM)
                }
            ]

        return {
            "current_plan": current_plan.value,
            "upgrade_options": upgrade_options
        }

    def _get_upgrade_benefits(self, from_tier: PlanTier, to_tier: PlanTier) -> List[str]:
        """Get list of benefits when upgrading between tiers"""
        from_plan = PLAN_CONFIGS[from_tier]
        to_plan = PLAN_CONFIGS[to_tier]

        benefits = []

        if to_plan.max_uploads_per_month > from_plan.max_uploads_per_month:
            benefits.append(f"{to_plan.max_uploads_per_month} uploads/month (from {from_plan.max_uploads_per_month})")

        if to_plan.max_storage_gb > from_plan.max_storage_gb:
            benefits.append(f"{to_plan.max_storage_gb}GB storage (from {from_plan.max_storage_gb}GB)")

        if to_plan.max_bandwidth_gb_per_month > from_plan.max_bandwidth_gb_per_month:
            benefits.append(f"{to_plan.max_bandwidth_gb_per_month}GB bandwidth/month (from {from_plan.max_bandwidth_gb_per_month}GB)")

        if to_plan.max_team_members > from_plan.max_team_members:
            benefits.append(f"Up to {to_plan.max_team_members} team members")

        if to_plan.team_collaboration and not from_plan.team_collaboration:
            benefits.append("Team collaboration features")

        if to_plan.priority_support and not from_plan.priority_support:
            benefits.append("Priority support")

        if to_plan.custom_branding and not from_plan.custom_branding:
            benefits.append("Custom branding")

        if to_plan.watermark_removal and not from_plan.watermark_removal:
            benefits.append("Watermark removal")

        if to_plan.custom_domain and not from_plan.custom_domain:
            benefits.append("Custom domain support")

        if to_plan.webhook_notifications and not from_plan.webhook_notifications:
            benefits.append("Webhook notifications")

        # Platform differences
        new_platforms = set(to_plan.platform_distribution) - set(from_plan.platform_distribution)
        if new_platforms:
            benefits.append(f"Additional platforms: {', '.join(new_platforms)}")

        return benefits
