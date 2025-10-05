"""
Monetization Module - Revenue Tracking & Analytics Integration

Integrates ads_manager with analytics to provide comprehensive monetization metrics.
Tracks revenue, ad performance, and user engagement for business intelligence.

Issue: #45
Depends on: publisher-ui (#38), analytics (#33)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
import json


class RevenueSource(Enum):
    """Revenue sources for monetization tracking"""

    WEBSITE_ADS = "website_ads"
    PRO_SUBSCRIPTION = "pro_subscription"
    TEAM_SUBSCRIPTION = "team_subscription"
    CUSTOM_PARTNERSHIP = "custom_partnership"


@dataclass
class RevenueEvent:
    """Represents a revenue-generating event"""

    event_id: str
    source: RevenueSource
    amount_usd: float
    user_id: str
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class AdRevenueMetrics:
    """Metrics for ad revenue performance"""

    impressions: int
    clicks: int
    ctr: float  # Click-through rate
    revenue_usd: float
    ecpm: float  # Effective cost per mille (thousand impressions)
    fill_rate: float  # Percentage of ad requests filled


class MonetizationTracker:
    """
    Tracks revenue and monetization metrics across the platform.
    Integrates with ads_manager and analytics modules.
    """

    def __init__(self):
        self.revenue_events: List[RevenueEvent] = []
        self._metrics_cache: Dict[str, Any] = {}

    def track_ad_revenue(
        self,
        ad_id: str,
        user_id: str,
        impressions: int,
        clicks: int,
        revenue_usd: float,
    ) -> RevenueEvent:
        """
        Track revenue from website ads

        Args:
            ad_id: Ad unit ID
            user_id: User who saw the ad
            impressions: Number of ad impressions
            clicks: Number of ad clicks
            revenue_usd: Revenue generated in USD

        Returns:
            Created revenue event
        """
        event = RevenueEvent(
            event_id=f"ad_rev_{ad_id}_{int(datetime.now(timezone.utc).timestamp())}",
            source=RevenueSource.WEBSITE_ADS,
            amount_usd=revenue_usd,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            metadata={
                "ad_id": ad_id,
                "impressions": impressions,
                "clicks": clicks,
                "ctr": (clicks / impressions * 100) if impressions > 0 else 0.0,
            },
        )
        self.revenue_events.append(event)
        self._invalidate_cache()
        return event

    def track_subscription_revenue(
        self,
        user_id: str,
        tier: str,
        amount_usd: float,
        billing_period: str = "monthly",
    ) -> RevenueEvent:
        """
        Track revenue from Pro/Team subscriptions

        Args:
            user_id: Subscribing user ID
            tier: Subscription tier (pro/team)
            amount_usd: Subscription amount in USD
            billing_period: Billing period (monthly/annual)

        Returns:
            Created revenue event
        """
        source = (
            RevenueSource.PRO_SUBSCRIPTION
            if tier.lower() == "pro"
            else RevenueSource.TEAM_SUBSCRIPTION
        )

        event = RevenueEvent(
            event_id=f"sub_{tier}_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
            source=source,
            amount_usd=amount_usd,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            metadata={"tier": tier, "billing_period": billing_period},
        )
        self.revenue_events.append(event)
        self._invalidate_cache()
        return event

    def get_total_revenue(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        source: Optional[RevenueSource] = None,
    ) -> float:
        """
        Get total revenue for a time period and/or source

        Args:
            start_date: Start of period (inclusive)
            end_date: End of period (inclusive)
            source: Optional revenue source filter

        Returns:
            Total revenue in USD
        """
        filtered_events = self._filter_events(start_date, end_date, source)
        return sum(event.amount_usd for event in filtered_events)

    def get_ad_revenue_metrics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> AdRevenueMetrics:
        """
        Get aggregated ad revenue metrics

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Ad revenue metrics
        """
        ad_events = self._filter_events(start_date, end_date, RevenueSource.WEBSITE_ADS)

        if not ad_events:
            return AdRevenueMetrics(
                impressions=0,
                clicks=0,
                ctr=0.0,
                revenue_usd=0.0,
                ecpm=0.0,
                fill_rate=0.0,
            )

        total_impressions = sum(
            event.metadata.get("impressions", 0) for event in ad_events
        )
        total_clicks = sum(event.metadata.get("clicks", 0) for event in ad_events)
        total_revenue = sum(event.amount_usd for event in ad_events)

        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
        ecpm = (
            (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0.0
        )

        # Assume 95% fill rate (would come from actual ad server in production)
        fill_rate = 95.0

        return AdRevenueMetrics(
            impressions=total_impressions,
            clicks=total_clicks,
            ctr=round(ctr, 2),
            revenue_usd=round(total_revenue, 2),
            ecpm=round(ecpm, 2),
            fill_rate=fill_rate,
        )

    def get_revenue_by_source(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Get revenue breakdown by source

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Dictionary mapping revenue source to amount
        """
        filtered_events = self._filter_events(start_date, end_date)

        revenue_by_source = {}
        for source in RevenueSource:
            source_events = [e for e in filtered_events if e.source == source]
            revenue_by_source[source.value] = sum(
                event.amount_usd for event in source_events
            )

        return revenue_by_source

    def get_mrr(self) -> float:
        """
        Calculate Monthly Recurring Revenue (MRR) from subscriptions

        Returns:
            MRR in USD
        """
        # Get last 30 days of subscription events
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        subscription_sources = [
            RevenueSource.PRO_SUBSCRIPTION,
            RevenueSource.TEAM_SUBSCRIPTION,
        ]

        mrr = 0.0
        for source in subscription_sources:
            events = self._filter_events(start_date, end_date, source)
            # Sum monthly subscription amounts
            for event in events:
                amount = event.amount_usd
                period = event.metadata.get("billing_period", "monthly")

                # Normalize to monthly
                if period == "annual":
                    amount = amount / 12

                mrr += amount

        return round(mrr, 2)

    def get_arpu(
        self,
        total_users: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """
        Calculate Average Revenue Per User (ARPU)

        Args:
            total_users: Total number of users
            start_date: Start of period
            end_date: End of period

        Returns:
            ARPU in USD
        """
        if total_users == 0:
            return 0.0

        total_revenue = self.get_total_revenue(start_date, end_date)
        return round(total_revenue / total_users, 2)

    def get_monetization_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive monetization summary

        Returns:
            Dictionary with key monetization metrics
        """
        # Last 30 days
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        total_revenue = self.get_total_revenue(start_date, end_date)
        revenue_by_source = self.get_revenue_by_source(start_date, end_date)
        ad_metrics = self.get_ad_revenue_metrics(start_date, end_date)
        mrr = self.get_mrr()

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": 30,
            },
            "total_revenue_usd": round(total_revenue, 2),
            "revenue_by_source": revenue_by_source,
            "mrr": mrr,
            "ad_metrics": {
                "impressions": ad_metrics.impressions,
                "clicks": ad_metrics.clicks,
                "ctr": ad_metrics.ctr,
                "revenue_usd": ad_metrics.revenue_usd,
                "ecpm": ad_metrics.ecpm,
                "fill_rate": ad_metrics.fill_rate,
            },
            "subscription_metrics": {
                "pro_revenue": revenue_by_source.get("pro_subscription", 0.0),
                "team_revenue": revenue_by_source.get("team_subscription", 0.0),
                "total_subscription_revenue": (
                    revenue_by_source.get("pro_subscription", 0.0)
                    + revenue_by_source.get("team_subscription", 0.0)
                ),
            },
        }

    def export_revenue_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json",
    ) -> str:
        """
        Export revenue report

        Args:
            start_date: Start of period
            end_date: End of period
            format: Export format (json/csv)

        Returns:
            Report as formatted string
        """
        summary = self.get_monetization_summary()

        if format == "json":
            return json.dumps(summary, indent=2)
        elif format == "csv":
            # Simple CSV format
            lines = [
                "metric,value",
                f"total_revenue_usd,{summary['total_revenue_usd']}",
                f"mrr,{summary['mrr']}",
                f"ad_revenue,{summary['ad_metrics']['revenue_usd']}",
                f"subscription_revenue,{summary['subscription_metrics']['total_subscription_revenue']}",
                f"ad_impressions,{summary['ad_metrics']['impressions']}",
                f"ad_clicks,{summary['ad_metrics']['clicks']}",
                f"ad_ctr,{summary['ad_metrics']['ctr']}",
            ]
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _filter_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        source: Optional[RevenueSource] = None,
    ) -> List[RevenueEvent]:
        """Filter revenue events by criteria"""
        events = self.revenue_events

        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        if source:
            events = [e for e in events if e.source == source]

        return events

    def _invalidate_cache(self):
        """Invalidate metrics cache"""
        self._metrics_cache.clear()


# Watermark Policy Reference (from ads_manager.py)
WATERMARK_POLICY_REFERENCE = {
    "module": "ads_manager",
    "policy": "NO watermarks on media files",
    "implementation": "See ads_manager.py and docs/ads-watermark-policy.md",
    "monetization_strategy": {
        "free_tier": "Display ads on website UI only",
        "pro_tier": "Ad-free website, subscription revenue",
        "team_tier": "Ad-free website, subscription revenue",
        "media_files": "Always clean, no watermarks, 100% shareable",
    },
}
