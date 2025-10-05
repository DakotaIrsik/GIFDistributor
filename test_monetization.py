"""
Tests for Monetization Module
Issue: #45
"""

import pytest
from datetime import datetime, timedelta, timezone
from monetization import (
    MonetizationTracker,
    RevenueSource,
    RevenueEvent,
    AdRevenueMetrics,
    WATERMARK_POLICY_REFERENCE,
)


@pytest.fixture
def tracker():
    """Create a fresh monetization tracker"""
    return MonetizationTracker()


class TestAdRevenueTracking:
    """Test ad revenue tracking functionality"""

    def test_track_ad_revenue(self, tracker):
        """Test tracking ad revenue event"""
        event = tracker.track_ad_revenue(
            ad_id="ad_001",
            user_id="user_123",
            impressions=1000,
            clicks=25,
            revenue_usd=5.50,
        )

        assert event.source == RevenueSource.WEBSITE_ADS
        assert event.amount_usd == 5.50
        assert event.user_id == "user_123"
        assert event.metadata["impressions"] == 1000
        assert event.metadata["clicks"] == 25
        assert event.metadata["ctr"] == 2.5

    def test_track_multiple_ad_events(self, tracker):
        """Test tracking multiple ad revenue events"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 5.50)
        tracker.track_ad_revenue("ad_002", "user_2", 2000, 50, 11.00)

        total = tracker.get_total_revenue(source=RevenueSource.WEBSITE_ADS)
        assert total == 16.50

    def test_ad_revenue_metrics(self, tracker):
        """Test aggregated ad revenue metrics"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 5.00)
        tracker.track_ad_revenue("ad_002", "user_2", 1000, 15, 3.00)

        metrics = tracker.get_ad_revenue_metrics()

        assert metrics.impressions == 2000
        assert metrics.clicks == 40
        assert metrics.ctr == 2.0
        assert metrics.revenue_usd == 8.00
        assert metrics.ecpm == 4.00  # (8 / 2000) * 1000

    def test_ad_metrics_empty_tracker(self, tracker):
        """Test ad metrics with no events"""
        metrics = tracker.get_ad_revenue_metrics()

        assert metrics.impressions == 0
        assert metrics.clicks == 0
        assert metrics.ctr == 0.0
        assert metrics.revenue_usd == 0.0
        assert metrics.ecpm == 0.0


class TestSubscriptionRevenue:
    """Test subscription revenue tracking"""

    def test_track_pro_subscription(self, tracker):
        """Test tracking Pro tier subscription"""
        event = tracker.track_subscription_revenue(
            user_id="user_123", tier="pro", amount_usd=9.99, billing_period="monthly"
        )

        assert event.source == RevenueSource.PRO_SUBSCRIPTION
        assert event.amount_usd == 9.99
        assert event.metadata["tier"] == "pro"
        assert event.metadata["billing_period"] == "monthly"

    def test_track_team_subscription(self, tracker):
        """Test tracking Team tier subscription"""
        event = tracker.track_subscription_revenue(
            user_id="team_001", tier="team", amount_usd=49.99, billing_period="monthly"
        )

        assert event.source == RevenueSource.TEAM_SUBSCRIPTION
        assert event.amount_usd == 49.99

    def test_annual_subscription(self, tracker):
        """Test tracking annual subscription"""
        event = tracker.track_subscription_revenue(
            user_id="user_456", tier="pro", amount_usd=99.99, billing_period="annual"
        )

        assert event.metadata["billing_period"] == "annual"
        assert event.amount_usd == 99.99


class TestRevenueCalculations:
    """Test revenue calculation methods"""

    def test_total_revenue_all_sources(self, tracker):
        """Test calculating total revenue across all sources"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 5.00)
        tracker.track_subscription_revenue("user_2", "pro", 9.99)
        tracker.track_subscription_revenue("user_3", "team", 49.99)

        total = tracker.get_total_revenue()
        assert total == 64.98

    def test_revenue_by_source(self, tracker):
        """Test revenue breakdown by source"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 10.00)
        tracker.track_subscription_revenue("user_2", "pro", 9.99)
        tracker.track_subscription_revenue("user_3", "team", 49.99)

        breakdown = tracker.get_revenue_by_source()

        assert breakdown["website_ads"] == 10.00
        assert breakdown["pro_subscription"] == 9.99
        assert breakdown["team_subscription"] == 49.99

    def test_revenue_filtered_by_source(self, tracker):
        """Test filtering revenue by specific source"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 10.00)
        tracker.track_subscription_revenue("user_2", "pro", 9.99)

        ad_revenue = tracker.get_total_revenue(source=RevenueSource.WEBSITE_ADS)
        sub_revenue = tracker.get_total_revenue(source=RevenueSource.PRO_SUBSCRIPTION)

        assert ad_revenue == 10.00
        assert sub_revenue == 9.99

    def test_revenue_date_filtering(self, tracker):
        """Test filtering revenue by date range"""
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=60)

        # Create events with different timestamps
        event_old = tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 5.00)
        event_old.timestamp = old_date

        event_new = tracker.track_ad_revenue("ad_002", "user_2", 1000, 25, 10.00)

        # Get revenue for last 30 days
        start_date = now - timedelta(days=30)
        recent_revenue = tracker.get_total_revenue(start_date=start_date)

        assert recent_revenue == 10.00  # Only the recent event


class TestMRR:
    """Test Monthly Recurring Revenue calculations"""

    def test_mrr_monthly_subscriptions(self, tracker):
        """Test MRR with monthly subscriptions"""
        tracker.track_subscription_revenue("user_1", "pro", 9.99, "monthly")
        tracker.track_subscription_revenue("user_2", "pro", 9.99, "monthly")
        tracker.track_subscription_revenue("user_3", "team", 49.99, "monthly")

        mrr = tracker.get_mrr()
        assert mrr == 69.97

    def test_mrr_annual_subscriptions(self, tracker):
        """Test MRR with annual subscriptions (normalized to monthly)"""
        tracker.track_subscription_revenue("user_1", "pro", 119.88, "annual")

        mrr = tracker.get_mrr()
        assert mrr == 9.99  # 119.88 / 12

    def test_mrr_mixed_subscriptions(self, tracker):
        """Test MRR with mix of monthly and annual"""
        tracker.track_subscription_revenue("user_1", "pro", 9.99, "monthly")
        tracker.track_subscription_revenue("user_2", "pro", 119.88, "annual")

        mrr = tracker.get_mrr()
        assert mrr == 19.98  # 9.99 + (119.88 / 12)

    def test_mrr_empty_tracker(self, tracker):
        """Test MRR with no subscriptions"""
        mrr = tracker.get_mrr()
        assert mrr == 0.0


class TestARPU:
    """Test Average Revenue Per User calculations"""

    def test_arpu_calculation(self, tracker):
        """Test ARPU calculation"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 5.00)
        tracker.track_subscription_revenue("user_2", "pro", 9.99)

        arpu = tracker.get_arpu(total_users=100)
        assert arpu == 0.15  # 14.99 / 100

    def test_arpu_zero_users(self, tracker):
        """Test ARPU with zero users"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 5.00)

        arpu = tracker.get_arpu(total_users=0)
        assert arpu == 0.0


class TestMonetizationSummary:
    """Test comprehensive monetization summary"""

    def test_monetization_summary(self, tracker):
        """Test complete monetization summary"""
        tracker.track_ad_revenue("ad_001", "user_1", 5000, 100, 25.00)
        tracker.track_subscription_revenue("user_2", "pro", 9.99)
        tracker.track_subscription_revenue("user_3", "team", 49.99)

        summary = tracker.get_monetization_summary()

        assert "period" in summary
        assert summary["total_revenue_usd"] == 84.98
        assert summary["mrr"] == 59.98
        assert summary["ad_metrics"]["revenue_usd"] == 25.00
        assert summary["ad_metrics"]["impressions"] == 5000
        assert summary["ad_metrics"]["clicks"] == 100
        assert summary["subscription_metrics"]["pro_revenue"] == 9.99
        assert summary["subscription_metrics"]["team_revenue"] == 49.99

    def test_summary_structure(self, tracker):
        """Test summary has correct structure"""
        summary = tracker.get_monetization_summary()

        assert "period" in summary
        assert "total_revenue_usd" in summary
        assert "revenue_by_source" in summary
        assert "mrr" in summary
        assert "ad_metrics" in summary
        assert "subscription_metrics" in summary


class TestRevenueExport:
    """Test revenue report export"""

    def test_export_json(self, tracker):
        """Test exporting report as JSON"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 5.00)

        report = tracker.export_revenue_report(format="json")

        assert isinstance(report, str)
        assert "total_revenue_usd" in report
        assert "mrr" in report

    def test_export_csv(self, tracker):
        """Test exporting report as CSV"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 25, 5.00)

        report = tracker.export_revenue_report(format="csv")

        assert isinstance(report, str)
        assert "metric,value" in report
        assert "total_revenue_usd" in report

    def test_export_unsupported_format(self, tracker):
        """Test exporting with unsupported format"""
        with pytest.raises(ValueError, match="Unsupported format"):
            tracker.export_revenue_report(format="xml")


class TestWatermarkPolicy:
    """Test watermark policy reference"""

    def test_watermark_policy_exists(self):
        """Test that watermark policy reference is defined"""
        assert WATERMARK_POLICY_REFERENCE is not None
        assert "module" in WATERMARK_POLICY_REFERENCE
        assert "policy" in WATERMARK_POLICY_REFERENCE

    def test_watermark_policy_content(self):
        """Test watermark policy content"""
        policy = WATERMARK_POLICY_REFERENCE

        assert policy["policy"] == "NO watermarks on media files"
        assert policy["module"] == "ads_manager"
        assert "monetization_strategy" in policy
        assert (
            policy["monetization_strategy"]["media_files"]
            == "Always clean, no watermarks, 100% shareable"
        )


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_zero_impressions_ctr(self, tracker):
        """Test CTR calculation with zero impressions"""
        event = tracker.track_ad_revenue(
            ad_id="ad_001", user_id="user_123", impressions=0, clicks=0, revenue_usd=0.0
        )

        assert event.metadata["ctr"] == 0.0

    def test_large_revenue_values(self, tracker):
        """Test handling large revenue values"""
        tracker.track_subscription_revenue("enterprise_1", "team", 999999.99)

        total = tracker.get_total_revenue()
        assert total == 999999.99

    def test_multiple_users_same_ad(self, tracker):
        """Test multiple users interacting with same ad"""
        tracker.track_ad_revenue("ad_001", "user_1", 1000, 10, 2.00)
        tracker.track_ad_revenue("ad_001", "user_2", 1000, 15, 3.00)
        tracker.track_ad_revenue("ad_001", "user_3", 1000, 20, 4.00)

        metrics = tracker.get_ad_revenue_metrics()
        assert metrics.impressions == 3000
        assert metrics.clicks == 45
        assert metrics.revenue_usd == 9.00
