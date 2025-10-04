"""
Tests for Pricing Plans & Quotas Module
Issue: #47
"""
import pytest
from datetime import datetime, timedelta
from pricing import (
    PricingManager, PlanTier, QuotaType, QuotaExceededError,
    PlanFeatures, UsageStats, PLAN_CONFIGS
)


class TestPlanConfigurations:
    """Test predefined plan configurations"""

    def test_free_plan_exists(self):
        """Free plan should be defined"""
        assert PlanTier.FREE in PLAN_CONFIGS
        free_plan = PLAN_CONFIGS[PlanTier.FREE]
        assert free_plan.name == "Free"
        assert free_plan.price_monthly_usd == 0.0

    def test_pro_plan_exists(self):
        """Pro plan should be defined"""
        assert PlanTier.PRO in PLAN_CONFIGS
        pro_plan = PLAN_CONFIGS[PlanTier.PRO]
        assert pro_plan.name == "Pro"
        assert pro_plan.price_monthly_usd > 0

    def test_team_plan_exists(self):
        """Team plan should be defined"""
        assert PlanTier.TEAM in PLAN_CONFIGS
        team_plan = PLAN_CONFIGS[PlanTier.TEAM]
        assert team_plan.name == "Team"
        assert team_plan.price_monthly_usd > PLAN_CONFIGS[PlanTier.PRO].price_monthly_usd

    def test_plan_tier_progression(self):
        """Plans should have increasing limits"""
        free = PLAN_CONFIGS[PlanTier.FREE]
        pro = PLAN_CONFIGS[PlanTier.PRO]
        team = PLAN_CONFIGS[PlanTier.TEAM]

        # Uploads
        assert free.max_uploads_per_month < pro.max_uploads_per_month < team.max_uploads_per_month

        # Storage
        assert free.max_storage_gb < pro.max_storage_gb < team.max_storage_gb

        # Bandwidth
        assert free.max_bandwidth_gb_per_month < pro.max_bandwidth_gb_per_month < team.max_bandwidth_gb_per_month

        # API requests
        assert free.api_requests_per_day < pro.api_requests_per_day < team.api_requests_per_day

    def test_free_plan_limitations(self):
        """Free plan should have basic features"""
        free = PLAN_CONFIGS[PlanTier.FREE]
        assert free.max_team_members == 1
        assert free.team_collaboration is False
        assert free.priority_support is False
        assert free.custom_branding is False
        assert free.watermark_removal is False
        assert free.custom_domain is False

    def test_premium_plan_features(self):
        """Pro and Team plans should have premium features"""
        pro = PLAN_CONFIGS[PlanTier.PRO]
        team = PLAN_CONFIGS[PlanTier.TEAM]

        assert pro.priority_support is True
        assert pro.custom_branding is True
        assert pro.watermark_removal is True
        assert pro.webhook_notifications is True

        assert team.team_collaboration is True
        assert team.max_team_members > 1


class TestPricingManager:
    """Test pricing manager functionality"""

    def test_init(self):
        """Manager should initialize correctly"""
        manager = PricingManager()
        assert manager is not None

    def test_assign_plan(self):
        """Should be able to assign plans to users"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.PRO)

        plan = manager.get_plan("user1")
        assert plan.tier == PlanTier.PRO

    def test_default_free_plan(self):
        """Users without assigned plan should get free plan"""
        manager = PricingManager()
        plan = manager.get_plan("newuser")
        assert plan.tier == PlanTier.FREE

    def test_get_usage_creates_stats(self):
        """Getting usage should create stats if they don't exist"""
        manager = PricingManager()
        usage = manager.get_usage("user1")
        assert isinstance(usage, UsageStats)
        assert usage.uploads_this_month == 0

    def test_usage_monthly_reset(self):
        """Monthly usage should reset at month boundary"""
        manager = PricingManager()
        usage = manager.get_usage("user1")

        # Set usage to last month
        usage.month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=32)
        usage.uploads_this_month = 50
        usage.bandwidth_used_gb_this_month = 10.0

        # Get usage again - should reset
        usage = manager.get_usage("user1")
        assert usage.uploads_this_month == 0
        assert usage.bandwidth_used_gb_this_month == 0.0

    def test_usage_daily_reset(self):
        """Daily usage should reset at day boundary"""
        manager = PricingManager()
        usage = manager.get_usage("user1")

        # Set usage to yesterday
        usage.day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        usage.api_requests_today = 100

        # Get usage again - should reset
        usage = manager.get_usage("user1")
        assert usage.api_requests_today == 0


class TestQuotaChecking:
    """Test quota checking functionality"""

    def test_check_upload_quota_available(self):
        """Should allow upload when quota available"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        # Free plan has 50 uploads/month
        assert manager.check_quota("user1", QuotaType.UPLOADS_PER_MONTH, 1.0) is True

    def test_check_upload_quota_exceeded(self):
        """Should raise error when upload quota exceeded"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        # Consume all quota
        usage = manager.get_usage("user1")
        usage.uploads_this_month = 50  # Free plan limit

        with pytest.raises(QuotaExceededError) as excinfo:
            manager.check_quota("user1", QuotaType.UPLOADS_PER_MONTH, 1.0)

        assert excinfo.value.quota_type == QuotaType.UPLOADS_PER_MONTH
        assert excinfo.value.current == 50
        assert excinfo.value.limit == 50

    def test_check_storage_quota(self):
        """Should enforce storage quota"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        usage = manager.get_usage("user1")
        usage.storage_used_gb = 0.9  # Free plan has 1.0GB

        # Should allow 0.1GB more
        assert manager.check_quota("user1", QuotaType.STORAGE_GB, 0.1) is True

        # Should not allow 0.2GB more
        with pytest.raises(QuotaExceededError):
            manager.check_quota("user1", QuotaType.STORAGE_GB, 0.2)

    def test_check_bandwidth_quota(self):
        """Should enforce bandwidth quota"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.PRO)

        usage = manager.get_usage("user1")
        usage.bandwidth_used_gb_this_month = 95.0  # Pro has 100GB

        assert manager.check_quota("user1", QuotaType.BANDWIDTH_GB, 5.0) is True

        with pytest.raises(QuotaExceededError):
            manager.check_quota("user1", QuotaType.BANDWIDTH_GB, 6.0)

    def test_check_team_members_quota(self):
        """Should enforce team member limits"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        usage = manager.get_usage("user1")
        usage.team_members_count = 1  # Free plan max

        with pytest.raises(QuotaExceededError):
            manager.check_quota("user1", QuotaType.TEAM_MEMBERS, 1.0)

    def test_check_api_quota(self):
        """Should enforce API request limits"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        usage = manager.get_usage("user1")
        usage.api_requests_today = 100  # Free plan limit

        with pytest.raises(QuotaExceededError):
            manager.check_quota("user1", QuotaType.API_REQUESTS_PER_DAY, 1.0)


class TestQuotaConsumption:
    """Test quota consumption functionality"""

    def test_consume_upload_quota(self):
        """Should consume upload quota"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 5.0)

        usage = manager.get_usage("user1")
        assert usage.uploads_this_month == 5

    def test_consume_storage_quota(self):
        """Should consume storage quota"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.PRO)

        manager.consume_quota("user1", QuotaType.STORAGE_GB, 0.5)

        usage = manager.get_usage("user1")
        assert usage.storage_used_gb == 0.5

    def test_consume_bandwidth_quota(self):
        """Should consume bandwidth quota"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.TEAM)

        manager.consume_quota("user1", QuotaType.BANDWIDTH_GB, 10.0)

        usage = manager.get_usage("user1")
        assert usage.bandwidth_used_gb_this_month == 10.0

    def test_consume_quota_prevents_over_limit(self):
        """Should not allow consumption beyond limit"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        # Try to consume more than allowed
        with pytest.raises(QuotaExceededError):
            manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 51.0)

        # Verify nothing was consumed
        usage = manager.get_usage("user1")
        assert usage.uploads_this_month == 0

    def test_consume_incremental_quota(self):
        """Should accumulate quota consumption"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 10.0)
        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 15.0)
        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 20.0)

        usage = manager.get_usage("user1")
        assert usage.uploads_this_month == 45


class TestQuotaStatus:
    """Test quota status reporting"""

    def test_get_quota_status_structure(self):
        """Should return properly structured quota status"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.PRO)

        status = manager.get_quota_status("user1")

        assert "plan" in status
        assert "tier" in status
        assert "quotas" in status
        assert "features" in status

    def test_quota_status_includes_all_quotas(self):
        """Status should include all quota types"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.TEAM)

        status = manager.get_quota_status("user1")

        quotas = status["quotas"]
        assert "uploads" in quotas
        assert "storage_gb" in quotas
        assert "bandwidth_gb" in quotas
        assert "team_members" in quotas
        assert "api_requests" in quotas

    def test_quota_status_shows_usage(self):
        """Status should show current usage"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 10.0)

        status = manager.get_quota_status("user1")

        assert status["quotas"]["uploads"]["used"] == 10
        assert status["quotas"]["uploads"]["limit"] == 50
        assert status["quotas"]["uploads"]["percentage"] == 20.0

    def test_quota_status_includes_features(self):
        """Status should include plan features"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.PRO)

        status = manager.get_quota_status("user1")

        features = status["features"]
        assert features["priority_support"] is True
        assert features["custom_branding"] is True
        assert features["watermark_removal"] is True
        assert "platforms" in features
        assert "analytics_retention_days" in features


class TestUpgradeOptions:
    """Test plan upgrade functionality"""

    def test_free_can_upgrade(self):
        """Free users should see upgrade options"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        upgrades = manager.can_upgrade("user1")

        assert upgrades["current_plan"] == "free"
        assert len(upgrades["upgrade_options"]) == 2

    def test_pro_can_upgrade_to_team(self):
        """Pro users should see Team upgrade"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.PRO)

        upgrades = manager.can_upgrade("user1")

        assert upgrades["current_plan"] == "pro"
        assert len(upgrades["upgrade_options"]) == 1
        assert upgrades["upgrade_options"][0]["tier"] == "team"

    def test_team_cannot_upgrade(self):
        """Team users should have no upgrades"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.TEAM)

        upgrades = manager.can_upgrade("user1")

        assert upgrades["current_plan"] == "team"
        assert len(upgrades["upgrade_options"]) == 0

    def test_upgrade_benefits_listed(self):
        """Upgrade options should list benefits"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        upgrades = manager.can_upgrade("user1")
        pro_option = upgrades["upgrade_options"][0]

        assert "benefits" in pro_option
        assert len(pro_option["benefits"]) > 0

    def test_upgrade_shows_pricing(self):
        """Upgrade options should show pricing"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        upgrades = manager.can_upgrade("user1")

        for option in upgrades["upgrade_options"]:
            assert "price" in option
            assert option["price"] > 0


class TestIntegrationScenarios:
    """Test real-world usage scenarios"""

    def test_new_user_workflow(self):
        """Test typical new user workflow"""
        manager = PricingManager()

        # New user gets free plan by default
        plan = manager.get_plan("newuser")
        assert plan.tier == PlanTier.FREE

        # User uploads some files
        for i in range(10):
            manager.consume_quota("newuser", QuotaType.UPLOADS_PER_MONTH, 1.0)

        # Check status
        status = manager.get_quota_status("newuser")
        assert status["quotas"]["uploads"]["used"] == 10

    def test_quota_exhaustion_and_upgrade(self):
        """Test hitting quota limit and upgrading"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        # Exhaust upload quota
        for i in range(50):
            manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 1.0)

        # Next upload should fail
        with pytest.raises(QuotaExceededError):
            manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 1.0)

        # Upgrade to Pro
        manager.assign_plan("user1", PlanTier.PRO)

        # Now should work (Pro has 500 uploads)
        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 1.0)

    def test_team_collaboration_limits(self):
        """Test team member limits"""
        manager = PricingManager()
        manager.assign_plan("team1", PlanTier.FREE)

        # Free plan allows only 1 member (self)
        usage = manager.get_usage("team1")
        assert usage.team_members_count == 1

        # Cannot add more
        with pytest.raises(QuotaExceededError):
            manager.consume_quota("team1", QuotaType.TEAM_MEMBERS, 1.0)

        # Upgrade to Team plan
        manager.assign_plan("team1", PlanTier.TEAM)

        # Now can add members (up to 10)
        for i in range(9):
            manager.consume_quota("team1", QuotaType.TEAM_MEMBERS, 1.0)

        usage = manager.get_usage("team1")
        assert usage.team_members_count == 10

    def test_api_rate_limiting_integration(self):
        """Test API quota limits"""
        manager = PricingManager()
        manager.assign_plan("api_user", PlanTier.FREE)

        # Free plan: 100 requests/day
        for i in range(100):
            manager.consume_quota("api_user", QuotaType.API_REQUESTS_PER_DAY, 1.0)

        # Should fail on 101st
        with pytest.raises(QuotaExceededError):
            manager.consume_quota("api_user", QuotaType.API_REQUESTS_PER_DAY, 1.0)

    def test_storage_accumulation(self):
        """Test storage quota accumulation"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        # Upload several files
        manager.consume_quota("user1", QuotaType.STORAGE_GB, 0.3)
        manager.consume_quota("user1", QuotaType.STORAGE_GB, 0.4)
        manager.consume_quota("user1", QuotaType.STORAGE_GB, 0.2)

        usage = manager.get_usage("user1")
        assert usage.storage_used_gb == pytest.approx(0.9)

        # One more should exceed
        with pytest.raises(QuotaExceededError):
            manager.consume_quota("user1", QuotaType.STORAGE_GB, 0.2)


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_zero_quota_consumption(self):
        """Should handle zero quota consumption"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 0.0)

        usage = manager.get_usage("user1")
        assert usage.uploads_this_month == 0

    def test_fractional_quota_consumption(self):
        """Should handle fractional quota amounts"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.PRO)

        manager.consume_quota("user1", QuotaType.STORAGE_GB, 0.123)

        usage = manager.get_usage("user1")
        assert usage.storage_used_gb == pytest.approx(0.123)

    def test_exact_quota_limit(self):
        """Should handle consuming exactly to the limit"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)

        # Consume exactly 50 uploads (the limit)
        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 50.0)

        usage = manager.get_usage("user1")
        assert usage.uploads_this_month == 50

        # One more should fail
        with pytest.raises(QuotaExceededError):
            manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 1.0)

    def test_multiple_users_independent(self):
        """Different users should have independent quotas"""
        manager = PricingManager()
        manager.assign_plan("user1", PlanTier.FREE)
        manager.assign_plan("user2", PlanTier.PRO)

        manager.consume_quota("user1", QuotaType.UPLOADS_PER_MONTH, 40.0)
        manager.consume_quota("user2", QuotaType.UPLOADS_PER_MONTH, 100.0)

        usage1 = manager.get_usage("user1")
        usage2 = manager.get_usage("user2")

        assert usage1.uploads_this_month == 40
        assert usage2.uploads_this_month == 100
