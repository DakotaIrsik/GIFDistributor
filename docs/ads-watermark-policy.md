# Advertising & Watermark Policy

**TL;DR:** Ads only on website UI. Media files stay 100% clean - **NO watermarks**, **NO embedded ads**, ever.

---

## Policy Overview

GIFDistributor uses a **clean media guarantee** approach to monetization:

- ✅ **Display ads on website** for Free tier users
- ✅ **Clean media files** for all users (no watermarks or embedded ads)
- ✅ **Ad-free website** for Pro and Team tier users
- ❌ **No media watermarking** (explicitly disabled by policy)

---

## Monetization Strategy

### Website Ads (Free Tier Only)

Free tier users will see non-intrusive display advertising on the website UI:

**Ad Placements:**
- Header banner (728x90)
- Sidebar (300x250)
- Footer banner (728x90)
- Inline feed ads (responsive)

**Ad Networks:**
- Google AdSense (primary)
- Custom direct partnerships
- Programmatic advertising

**Privacy-First:**
- Respects "Do Not Track" browser setting
- GDPR/CCPA compliant ad selection
- No cross-site tracking

### No Media Watermarks

Media files (GIF, MP4, WebP) remain **completely clean**:

- ❌ No logos burned into media
- ❌ No watermarks overlaid
- ❌ No embedded advertising frames
- ✅ 100% shareable, professional-quality output

**Rationale:**
- Watermarks reduce shareability and virality
- Clean media enhances user trust and platform reputation
- Website ads provide monetization without compromising media quality

---

## User Tier Comparison

| Feature | Free Tier | Pro Tier | Team Tier |
|---------|-----------|----------|-----------|
| Media Files | ✅ Clean (no watermarks) | ✅ Clean (no watermarks) | ✅ Clean (no watermarks) |
| Website Ads | 📺 Yes (non-intrusive) | ❌ No (ad-free) | ❌ No (ad-free) |
| Ad Refresh | Every 30s | N/A | N/A |
| Max Ads/Page | 3 | 0 | 0 |

---

## Implementation

### Python Backend

```python
from ads_manager import AdsManager, AdUnit, AdPlacement, AdNetwork, UserTier

# Initialize ads manager
manager = AdsManager()

# Register ad units
manager.register_ad_unit(AdUnit(
    id="header-main",
    placement=AdPlacement.HEADER_BANNER,
    network=AdNetwork.GOOGLE_ADSENSE,
    slot_id="1234567890",
    dimensions=(728, 90)
))

# Get ad config for client
config = manager.get_ad_config_for_client(
    user_tier=UserTier.FREE,
    page_placements=[AdPlacement.HEADER_BANNER, AdPlacement.SIDEBAR_RIGHT],
    do_not_track=False
)
```

### React Frontend

```tsx
import AdContainer from '@/components/ads/AdContainer';
import WatermarkPolicyNotice from '@/components/ads/WatermarkPolicyNotice';

export default function Page() {
  return (
    <>
      <AdContainer placement="header_banner" userTier="free" />

      <main>
        <WatermarkPolicyNotice />
        {/* Page content */}
      </main>

      <AdContainer placement="footer" userTier="free" />
    </>
  );
}
```

---

## Analytics & Tracking

### Ad Performance Metrics

- **Impressions:** Total ad views
- **Clicks:** User clicks on ads
- **CTR:** Click-through rate
- **Revenue:** Estimated earnings (AdSense)

### Privacy Controls

- Respects browser Do Not Track (DNT) setting
- GDPR consent management
- No PII collection in ad tracking
- Anonymous impression/click IDs

---

## Upgrade Path (Revenue Strategy)

### Free Tier → Pro Tier

**Value Proposition:**
- Remove all website ads for $9.99/month
- Media files already clean (no change)
- Priority support and advanced features

**Conversion Strategy:**
- Non-intrusive ad experience (3 ads max per page)
- Clear upgrade CTA in ad-free zones
- 30-day trial option for Pro tier

### Pro Tier → Team Tier

**Value Proposition:**
- Team collaboration features
- Shared asset library
- Centralized billing
- Admin dashboard

---

## Ad Policy Enforcement

### Prohibited

- ❌ Watermarking media files
- ❌ Embedding ads in GIF/MP4/WebP
- ❌ Intrusive pop-ups or interstitials
- ❌ Auto-playing video ads with sound
- ❌ Misleading or deceptive ad content

### Allowed

- ✅ Static display ads (banners, sidebars)
- ✅ Native content recommendations
- ✅ Sponsored platform partnerships
- ✅ Text-based contextual ads

---

## Watermark Policy (Explicit Denial)

```python
from ads_manager import validate_media_watermark_request

# This will raise ValueError
try:
    validate_media_watermark_request(enable=True)
except ValueError as e:
    print(e)  # "Media watermarking is disabled by policy."
```

**Policy Rationale:**
1. **User Trust:** Clean media builds platform credibility
2. **Shareability:** Unwatermarked content spreads faster
3. **Professional Quality:** No visual distractions in media
4. **Competitive Advantage:** Differentiation from competitors

---

## Future Considerations

### Alternative Monetization (Under Evaluation)

- **API Access Plans:** Programmatic upload pricing
- **Platform Partnerships:** Revenue sharing with GIPHY/Tenor
- **Enterprise Licenses:** White-label solutions for brands
- **Media Storage Tiers:** Pay-per-GB for high-volume users

### Ad Experience Improvements

- A/B testing ad placements
- Contextual targeting (tags, categories)
- Performance-based optimization
- User feedback integration

---

## FAQ

**Q: Will you ever add watermarks to media files?**
A: No. This is a core policy and will not change. Media files remain clean for all users.

**Q: Can I upgrade to Pro to remove website ads?**
A: Yes. Pro tier ($9.99/mo) and Team tier ($49.99/mo) offer completely ad-free website experience.

**Q: Are ads shown to logged-out users?**
A: Yes, public pages show ads to anonymous visitors (free tier experience).

**Q: Do ads respect privacy laws (GDPR/CCPA)?**
A: Yes. We use privacy-compliant ad networks and respect Do Not Track settings.

**Q: Can I opt out of ads temporarily?**
A: Enable "Do Not Track" in your browser, or upgrade to Pro tier for permanent ad-free experience.

---

## Support

- Documentation: `/docs/ads-watermark-policy.md`
- Upgrade Plans: `/pricing`
- Privacy Policy: `/docs/privacy-policy.md`
- Terms of Service: `/docs/terms-of-service.md`
