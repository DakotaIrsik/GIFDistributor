"""
Analytics Module for GIF Distributor
Tracks views, plays, CTR by platform
Issue: #33
"""

from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
from enum import Enum


class EventType(Enum):
    """Types of analytics events"""

    VIEW = "view"  # Link was viewed (page loaded)
    PLAY = "play"  # Media was played
    CLICK = "click"  # Link was clicked through


class Platform(Enum):
    """Platforms where content can be shared"""

    WEB = "web"
    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    OTHER = "other"


class AnalyticsTracker:
    """Tracks analytics events for assets and share links"""

    def __init__(self):
        self._events: List[Dict] = []
        self._metrics_cache: Dict[str, Dict] = {}

    def track_event(
        self,
        asset_id: str,
        event_type: EventType,
        platform: Platform = Platform.WEB,
        short_code: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Track an analytics event

        Args:
            asset_id: The asset being tracked
            event_type: Type of event (view, play, click)
            platform: Platform where event occurred
            short_code: Optional short code if from share link
            metadata: Optional additional metadata

        Returns:
            The created event record
        """
        event = {
            "asset_id": asset_id,
            "event_type": event_type.value,
            "platform": platform.value,
            "short_code": short_code,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        self._events.append(event)

        # Invalidate cache for this asset
        if asset_id in self._metrics_cache:
            del self._metrics_cache[asset_id]

        return event

    def get_asset_metrics(self, asset_id: str) -> Dict:
        """
        Get aggregated metrics for an asset

        Args:
            asset_id: The asset to get metrics for

        Returns:
            Dictionary with views, plays, clicks, and CTR
        """
        # Check cache
        if asset_id in self._metrics_cache:
            return self._metrics_cache[asset_id]

        asset_events = [e for e in self._events if e["asset_id"] == asset_id]

        views = sum(1 for e in asset_events if e["event_type"] == EventType.VIEW.value)
        plays = sum(1 for e in asset_events if e["event_type"] == EventType.PLAY.value)
        clicks = sum(
            1 for e in asset_events if e["event_type"] == EventType.CLICK.value
        )

        # Calculate CTR (Click-Through Rate): clicks / views
        ctr = (clicks / views * 100) if views > 0 else 0.0

        # Play rate: plays / views
        play_rate = (plays / views * 100) if views > 0 else 0.0

        metrics = {
            "asset_id": asset_id,
            "views": views,
            "plays": plays,
            "clicks": clicks,
            "ctr": round(ctr, 2),
            "play_rate": round(play_rate, 2),
            "total_events": len(asset_events),
        }

        # Cache the result
        self._metrics_cache[asset_id] = metrics
        return metrics

    def get_platform_metrics(self, asset_id: str) -> Dict[str, Dict]:
        """
        Get metrics broken down by platform

        Args:
            asset_id: The asset to get platform metrics for

        Returns:
            Dictionary mapping platform names to their metrics
        """
        asset_events = [e for e in self._events if e["asset_id"] == asset_id]

        platform_data = defaultdict(lambda: {"views": 0, "plays": 0, "clicks": 0})

        for event in asset_events:
            platform = event["platform"]
            event_type = event["event_type"]

            if event_type == EventType.VIEW.value:
                platform_data[platform]["views"] += 1
            elif event_type == EventType.PLAY.value:
                platform_data[platform]["plays"] += 1
            elif event_type == EventType.CLICK.value:
                platform_data[platform]["clicks"] += 1

        # Calculate CTR for each platform
        result = {}
        for platform, data in platform_data.items():
            views = data["views"]
            clicks = data["clicks"]
            plays = data["plays"]

            result[platform] = {
                "views": views,
                "plays": plays,
                "clicks": clicks,
                "ctr": round((clicks / views * 100) if views > 0 else 0.0, 2),
                "play_rate": round((plays / views * 100) if views > 0 else 0.0, 2),
            }

        return result

    def get_short_link_metrics(self, short_code: str) -> Dict:
        """
        Get metrics for a specific short link

        Args:
            short_code: The short code to get metrics for

        Returns:
            Dictionary with metrics for this short link
        """
        link_events = [e for e in self._events if e.get("short_code") == short_code]

        if not link_events:
            return {
                "short_code": short_code,
                "views": 0,
                "plays": 0,
                "clicks": 0,
                "ctr": 0.0,
                "play_rate": 0.0,
            }

        views = sum(1 for e in link_events if e["event_type"] == EventType.VIEW.value)
        plays = sum(1 for e in link_events if e["event_type"] == EventType.PLAY.value)
        clicks = sum(1 for e in link_events if e["event_type"] == EventType.CLICK.value)

        return {
            "short_code": short_code,
            "asset_id": link_events[0]["asset_id"],
            "views": views,
            "plays": plays,
            "clicks": clicks,
            "ctr": round((clicks / views * 100) if views > 0 else 0.0, 2),
            "play_rate": round((plays / views * 100) if views > 0 else 0.0, 2),
        }

    def get_top_assets(self, metric: str = "views", limit: int = 10) -> List[Dict]:
        """
        Get top performing assets by a specific metric

        Args:
            metric: Metric to sort by (views, plays, clicks, ctr)
            limit: Maximum number of results

        Returns:
            List of assets with their metrics, sorted by the specified metric
        """
        # Get unique asset IDs
        asset_ids = set(e["asset_id"] for e in self._events)

        # Get metrics for each asset
        asset_metrics = [self.get_asset_metrics(aid) for aid in asset_ids]

        # Sort by the specified metric
        sorted_assets = sorted(
            asset_metrics, key=lambda x: x.get(metric, 0), reverse=True
        )

        return sorted_assets[:limit]

    def get_events_by_timeframe(
        self,
        asset_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get events for an asset within a timeframe

        Args:
            asset_id: The asset to get events for
            start_time: Start of timeframe (inclusive)
            end_time: End of timeframe (inclusive)

        Returns:
            List of events within the timeframe
        """
        asset_events = [e for e in self._events if e["asset_id"] == asset_id]

        if start_time:
            asset_events = [
                e
                for e in asset_events
                if datetime.fromisoformat(e["timestamp"]) >= start_time
            ]

        if end_time:
            asset_events = [
                e
                for e in asset_events
                if datetime.fromisoformat(e["timestamp"]) <= end_time
            ]

        return asset_events

    def clear_events(self, asset_id: Optional[str] = None):
        """
        Clear events, optionally for a specific asset

        Args:
            asset_id: If provided, only clear events for this asset
        """
        if asset_id:
            self._events = [e for e in self._events if e["asset_id"] != asset_id]
            if asset_id in self._metrics_cache:
                del self._metrics_cache[asset_id]
        else:
            self._events.clear()
            self._metrics_cache.clear()
