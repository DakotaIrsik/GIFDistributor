"""
Tests for Ads Manager Module
"""

import pytest
from ads_manager import (
    AdsManager,
    AdUnit,
    AdPolicy,
    AdPlacement,
    AdNetwork,
    UserTier,
    get_watermark_policy,
    validate_media_watermark_request,
    WATERMARK_POLICY,
)


class TestAdsManager:
    """Test suite for AdsManager"""

    def test_initialization(self):
        """Test AdsManager initialization"""
        manager = AdsManager()
        assert manager.policy is not None
        assert manager.policy.show_ads_to_free_users is True
        assert manager.policy.show_ads_to_pro_users is False
        assert manager.ad_units == {}

    def test_custom_policy(self):
        """Test AdsManager with custom policy"""
        policy = AdPolicy(
            show_ads_to_free_users=True,
            show_ads_to_pro_users=False,
            max_ads_per_page=5,
            respect_do_not_track=True,
        )
        manager = AdsManager(policy)
        assert manager.policy.max_ads_per_page == 5
        assert manager.policy.respect_do_not_track is True

    def test_register_ad_unit(self):
        """Test registering ad units"""
        manager = AdsManager()
        ad_unit = AdUnit(
            id="header-1",
            placement=AdPlacement.HEADER_BANNER,
            network=AdNetwork.GOOGLE_ADSENSE,
            slot_id="1234567890",
            dimensions=(728, 90),
        )
        manager.register_ad_unit(ad_unit)

        assert "header-1" in manager.ad_units
        assert len(manager.placement_registry[AdPlacement.HEADER_BANNER]) == 1

    def test_should_show_ads_free_tier(self):
        """Test ad display for free tier users"""
        manager = AdsManager()
        assert manager.should_show_ads(UserTier.FREE, do_not_track=False) is True

    def test_should_show_ads_pro_tier(self):
        """Test ad display for pro tier users (no ads)"""
        manager = AdsManager()
        assert manager.should_show_ads(UserTier.PRO, do_not_track=False) is False

    def test_should_show_ads_team_tier(self):
        """Test ad display for team tier users (no ads)"""
        manager = AdsManager()
        assert manager.should_show_ads(UserTier.TEAM, do_not_track=False) is False

    def test_should_show_ads_with_do_not_track(self):
        """Test ad display respects Do Not Track"""
        manager = AdsManager()
        assert manager.should_show_ads(UserTier.FREE, do_not_track=True) is False

    def test_get_ads_for_page(self):
        """Test getting ads for a page"""
        manager = AdsManager()

        # Register multiple ad units
        manager.register_ad_unit(
            AdUnit(
                id="header-1",
                placement=AdPlacement.HEADER_BANNER,
                network=AdNetwork.GOOGLE_ADSENSE,
                slot_id="1234567890",
                dimensions=(728, 90),
            )
        )
        manager.register_ad_unit(
            AdUnit(
                id="sidebar-1",
                placement=AdPlacement.SIDEBAR_RIGHT,
                network=AdNetwork.GOOGLE_ADSENSE,
                slot_id="0987654321",
                dimensions=(300, 250),
            )
        )

        placements = [AdPlacement.HEADER_BANNER, AdPlacement.SIDEBAR_RIGHT]
        ads = manager.get_ads_for_page(UserTier.FREE, placements)

        assert len(ads) == 2
        assert any(ad.id == "header-1" for ad in ads)
        assert any(ad.id == "sidebar-1" for ad in ads)

    def test_get_ads_for_page_respects_max_ads(self):
        """Test max ads per page limit"""
        policy = AdPolicy(max_ads_per_page=2)
        manager = AdsManager(policy)

        # Register 3 ad units
        for i in range(3):
            manager.register_ad_unit(
                AdUnit(
                    id=f"ad-{i}",
                    placement=AdPlacement.INLINE_FEED,
                    network=AdNetwork.GOOGLE_ADSENSE,
                    slot_id=f"slot-{i}",
                    dimensions=(300, 250),
                )
            )

        ads = manager.get_ads_for_page(UserTier.FREE, [AdPlacement.INLINE_FEED])
        assert len(ads) == 2  # Only 2 ads due to max_ads_per_page

    def test_get_ads_for_page_pro_tier_no_ads(self):
        """Test pro tier users get no ads"""
        manager = AdsManager()
        manager.register_ad_unit(
            AdUnit(
                id="header-1",
                placement=AdPlacement.HEADER_BANNER,
                network=AdNetwork.GOOGLE_ADSENSE,
                slot_id="1234567890",
                dimensions=(728, 90),
            )
        )

        ads = manager.get_ads_for_page(UserTier.PRO, [AdPlacement.HEADER_BANNER])
        assert len(ads) == 0

    def test_get_ad_config_for_client(self):
        """Test generating client-side ad config"""
        manager = AdsManager()
        manager.register_ad_unit(
            AdUnit(
                id="header-1",
                placement=AdPlacement.HEADER_BANNER,
                network=AdNetwork.GOOGLE_ADSENSE,
                slot_id="1234567890",
                dimensions=(728, 90),
            )
        )

        config = manager.get_ad_config_for_client(
            UserTier.FREE, [AdPlacement.HEADER_BANNER]
        )

        assert config["show_ads"] is True
        assert len(config["ad_units"]) == 1
        assert config["ad_units"][0]["id"] == "header-1"
        assert config["ad_units"][0]["dimensions"]["width"] == 728
        assert config["ad_units"][0]["dimensions"]["height"] == 90

    def test_get_ad_config_for_client_no_ads(self):
        """Test ad config when no ads should show"""
        manager = AdsManager()
        config = manager.get_ad_config_for_client(
            UserTier.PRO, [AdPlacement.HEADER_BANNER]
        )

        assert config["show_ads"] is False
        assert len(config["ad_units"]) == 0

    def test_track_ad_impression(self):
        """Test ad impression tracking"""
        manager = AdsManager()
        impression = manager.track_ad_impression("ad-123", "user-456")

        assert "impression_id" in impression
        assert impression["ad_id"] == "ad-123"
        assert impression["user_id"] == "user-456"
        assert impression["event"] == "impression"
        assert "timestamp" in impression

    def test_track_ad_click(self):
        """Test ad click tracking"""
        manager = AdsManager()
        click = manager.track_ad_click("ad-123", "user-456", "https://example.com")

        assert "click_id" in click
        assert click["ad_id"] == "ad-123"
        assert click["user_id"] == "user-456"
        assert click["target_url"] == "https://example.com"
        assert click["event"] == "click"
        assert "timestamp" in click

    def test_disabled_ad_units_not_shown(self):
        """Test that disabled ad units are not shown"""
        manager = AdsManager()
        manager.register_ad_unit(
            AdUnit(
                id="disabled-1",
                placement=AdPlacement.HEADER_BANNER,
                network=AdNetwork.GOOGLE_ADSENSE,
                slot_id="1234567890",
                dimensions=(728, 90),
                enabled=False,
            )
        )

        ads = manager.get_ads_for_page(UserTier.FREE, [AdPlacement.HEADER_BANNER])
        assert len(ads) == 0


class TestWatermarkPolicy:
    """Test suite for watermark policy (explicitly no watermarks)"""

    def test_get_watermark_policy(self):
        """Test getting watermark policy"""
        policy = get_watermark_policy()
        assert policy["media_watermarking"] is False
        assert "reason" in policy
        assert "alternatives" in policy

    def test_watermark_policy_constants(self):
        """Test watermark policy constants"""
        assert WATERMARK_POLICY["media_watermarking"] is False
        assert "monetization" in WATERMARK_POLICY["alternatives"]
        assert "user_control" in WATERMARK_POLICY

    def test_validate_media_watermark_request_disabled(self):
        """Test that watermark requests are rejected"""
        # Requesting False (disabled) should be allowed
        assert validate_media_watermark_request(False) is False

    def test_validate_media_watermark_request_enabled_raises(self):
        """Test that enabling watermarks raises an error"""
        with pytest.raises(ValueError) as excinfo:
            validate_media_watermark_request(True)
        assert "disabled by policy" in str(excinfo.value)

    def test_watermark_policy_user_control(self):
        """Test user control policy in watermark config"""
        policy = get_watermark_policy()
        assert (
            policy["user_control"]["free_tier"]
            == "Sees ads on website, media files remain clean"
        )
        assert (
            policy["user_control"]["pro_tier"]
            == "No ads on website, media files remain clean"
        )
        assert (
            policy["user_control"]["team_tier"]
            == "No ads on website, media files remain clean"
        )


class TestAdPlacementEnum:
    """Test ad placement enum"""

    def test_all_placements(self):
        """Test all ad placement values"""
        assert AdPlacement.HEADER_BANNER.value == "header_banner"
        assert AdPlacement.SIDEBAR_RIGHT.value == "sidebar_right"
        assert AdPlacement.SIDEBAR_LEFT.value == "sidebar_left"
        assert AdPlacement.FOOTER.value == "footer"
        assert AdPlacement.INLINE_FEED.value == "inline_feed"
        assert AdPlacement.MODAL_INTERSTITIAL.value == "modal_interstitial"


class TestAdNetworkEnum:
    """Test ad network enum"""

    def test_all_networks(self):
        """Test all ad network values"""
        assert AdNetwork.GOOGLE_ADSENSE.value == "google_adsense"
        assert AdNetwork.CUSTOM_DIRECT.value == "custom_direct"
        assert AdNetwork.PROGRAMMATIC.value == "programmatic"


class TestUserTierEnum:
    """Test user tier enum"""

    def test_all_tiers(self):
        """Test all user tier values"""
        assert UserTier.FREE.value == "free"
        assert UserTier.PRO.value == "pro"
        assert UserTier.TEAM.value == "team"
