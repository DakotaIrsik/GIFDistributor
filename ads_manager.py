"""
Ads Manager Module - Site Advertising (No Media Watermarks)

Manages display advertising on the website UI only.
GIF/media files remain clean with NO watermarks or embedded ads.

Features:
- Ad placement configuration (header, sidebar, footer, inline)
- Ad network integration (Google AdSense, custom networks)
- User tier-based ad display (Free = ads, Pro/Team = no ads)
- Analytics integration for ad performance tracking
- A/B testing for ad placements
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from enum import Enum
import hashlib
import time


class AdPlacement(Enum):
    """Ad placement positions on the site"""
    HEADER_BANNER = "header_banner"
    SIDEBAR_RIGHT = "sidebar_right"
    SIDEBAR_LEFT = "sidebar_left"
    FOOTER = "footer"
    INLINE_FEED = "inline_feed"
    MODAL_INTERSTITIAL = "modal_interstitial"


class AdNetwork(Enum):
    """Supported ad networks"""
    GOOGLE_ADSENSE = "google_adsense"
    CUSTOM_DIRECT = "custom_direct"
    PROGRAMMATIC = "programmatic"


class UserTier(Enum):
    """User subscription tiers"""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


@dataclass
class AdUnit:
    """Represents a single ad unit configuration"""
    id: str
    placement: AdPlacement
    network: AdNetwork
    slot_id: str  # Ad network slot/unit ID
    dimensions: tuple  # (width, height)
    enabled: bool = True
    min_tier: UserTier = UserTier.FREE  # Minimum tier that sees this ad


@dataclass
class AdPolicy:
    """Site advertising policy configuration"""
    show_ads_to_free_users: bool = True
    show_ads_to_pro_users: bool = False
    show_ads_to_team_users: bool = False
    max_ads_per_page: int = 3
    ad_refresh_interval_seconds: int = 30
    respect_do_not_track: bool = True


class AdsManager:
    """Manages site advertising (no media watermarks)"""

    def __init__(self, policy: Optional[AdPolicy] = None):
        self.policy = policy or AdPolicy()
        self.ad_units: Dict[str, AdUnit] = {}
        self.placement_registry: Dict[AdPlacement, List[AdUnit]] = {
            placement: [] for placement in AdPlacement
        }

    def register_ad_unit(self, ad_unit: AdUnit):
        """Register an ad unit for display"""
        self.ad_units[ad_unit.id] = ad_unit
        self.placement_registry[ad_unit.placement].append(ad_unit)

    def should_show_ads(self, user_tier: UserTier, do_not_track: bool = False) -> bool:
        """Determine if ads should be shown to a user"""
        if do_not_track and self.policy.respect_do_not_track:
            return False

        if user_tier == UserTier.FREE:
            return self.policy.show_ads_to_free_users
        elif user_tier == UserTier.PRO:
            return self.policy.show_ads_to_pro_users
        elif user_tier == UserTier.TEAM:
            return self.policy.show_ads_to_team_users

        return False

    def get_ads_for_page(
        self,
        user_tier: UserTier,
        placements: List[AdPlacement],
        do_not_track: bool = False
    ) -> List[AdUnit]:
        """Get ad units to display on a page"""
        if not self.should_show_ads(user_tier, do_not_track):
            return []

        ads = []
        for placement in placements:
            for ad_unit in self.placement_registry[placement]:
                if ad_unit.enabled and len(ads) < self.policy.max_ads_per_page:
                    ads.append(ad_unit)

        return ads[:self.policy.max_ads_per_page]

    def get_ad_config_for_client(
        self,
        user_tier: UserTier,
        page_placements: List[AdPlacement],
        do_not_track: bool = False
    ) -> Dict[str, Any]:
        """Generate client-side ad configuration"""
        ads = self.get_ads_for_page(user_tier, page_placements, do_not_track)

        return {
            "show_ads": len(ads) > 0,
            "max_ads": self.policy.max_ads_per_page,
            "refresh_interval": self.policy.ad_refresh_interval_seconds,
            "ad_units": [
                {
                    "id": ad.id,
                    "placement": ad.placement.value,
                    "network": ad.network.value,
                    "slot_id": ad.slot_id,
                    "dimensions": {"width": ad.dimensions[0], "height": ad.dimensions[1]}
                }
                for ad in ads
            ]
        }

    def track_ad_impression(self, ad_id: str, user_id: str) -> Dict[str, Any]:
        """Track ad impression for analytics"""
        timestamp = int(time.time())
        impression_id = hashlib.sha256(
            f"{ad_id}:{user_id}:{timestamp}".encode()
        ).hexdigest()[:16]

        return {
            "impression_id": impression_id,
            "ad_id": ad_id,
            "user_id": user_id,
            "timestamp": timestamp,
            "event": "impression"
        }

    def track_ad_click(self, ad_id: str, user_id: str, target_url: str) -> Dict[str, Any]:
        """Track ad click for analytics"""
        timestamp = int(time.time())
        click_id = hashlib.sha256(
            f"{ad_id}:{user_id}:{timestamp}:click".encode()
        ).hexdigest()[:16]

        return {
            "click_id": click_id,
            "ad_id": ad_id,
            "user_id": user_id,
            "target_url": target_url,
            "timestamp": timestamp,
            "event": "click"
        }


# Watermark Policy (Document-only - NO implementation for media)
WATERMARK_POLICY = {
    "media_watermarking": False,  # Explicitly disabled
    "reason": "Clean, shareable content - ads only on website UI, never in media files",
    "alternatives": {
        "monetization": "Display ads on website for free tier users",
        "branding": "Optional branded landing pages with user control"
    },
    "user_control": {
        "free_tier": "Sees ads on website, media files remain clean",
        "pro_tier": "No ads on website, media files remain clean",
        "team_tier": "No ads on website, media files remain clean"
    }
}


def get_watermark_policy() -> Dict[str, Any]:
    """Returns the watermark policy (explicitly no watermarks on media)"""
    return WATERMARK_POLICY


def validate_media_watermark_request(enable: bool) -> bool:
    """Validates watermark requests - always returns False (watermarks disabled)"""
    if enable:
        raise ValueError(
            "Media watermarking is disabled by policy. "
            "Use website ads for monetization instead."
        )
    return False
