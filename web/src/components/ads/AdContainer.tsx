"use client";

import { useEffect, useState } from 'react';

export type AdPlacement =
  | 'header_banner'
  | 'sidebar_right'
  | 'sidebar_left'
  | 'footer'
  | 'inline_feed'
  | 'modal_interstitial';

export type AdNetwork = 'google_adsense' | 'custom_direct' | 'programmatic';

export interface AdUnit {
  id: string;
  placement: AdPlacement;
  network: AdNetwork;
  slot_id: string;
  dimensions: { width: number; height: number };
}

export interface AdConfig {
  show_ads: boolean;
  max_ads: number;
  refresh_interval: number;
  ad_units: AdUnit[];
}

interface AdContainerProps {
  placement: AdPlacement;
  userTier?: 'free' | 'pro' | 'team';
  doNotTrack?: boolean;
}

/**
 * AdContainer - Displays ads on the site UI only
 *
 * NO WATERMARKS on media files - ads are website-only for monetization.
 * Free tier users see ads, Pro/Team users have ad-free experience.
 */
export default function AdContainer({
  placement,
  userTier = 'free',
  doNotTrack = false
}: AdContainerProps) {
  const [adConfig, setAdConfig] = useState<AdConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchAdConfig() {
      try {
        const response = await fetch('/api/ads/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_tier: userTier,
            placements: [placement],
            do_not_track: doNotTrack
          })
        });

        if (response.ok) {
          const config = await response.json();
          setAdConfig(config);
        }
      } catch (error) {
        console.error('Failed to load ad config:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchAdConfig();
  }, [placement, userTier, doNotTrack]);

  useEffect(() => {
    // Track ad impressions
    if (adConfig?.ad_units) {
      adConfig.ad_units.forEach(ad => {
        if (ad.placement === placement) {
          fetch('/api/ads/impression', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ad_id: ad.id })
          });
        }
      });
    }
  }, [adConfig, placement]);

  if (isLoading || !adConfig || !adConfig.show_ads) {
    return null;
  }

  const adsForPlacement = adConfig.ad_units.filter(
    ad => ad.placement === placement
  );

  if (adsForPlacement.length === 0) {
    return null;
  }

  return (
    <div className="ad-container" data-placement={placement}>
      {adsForPlacement.map(ad => (
        <div
          key={ad.id}
          className={`ad-unit ad-${ad.placement}`}
          style={{
            width: ad.dimensions.width,
            height: ad.dimensions.height,
            margin: '16px 0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#f5f5f5',
            border: '1px solid #e0e0e0',
            borderRadius: '4px'
          }}
        >
          {ad.network === 'google_adsense' && (
            <ins
              className="adsbygoogle"
              style={{ display: 'block' }}
              data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
              data-ad-slot={ad.slot_id}
              data-ad-format="auto"
              data-full-width-responsive="true"
            />
          )}
          {ad.network === 'custom_direct' && (
            <div className="custom-ad-placeholder">
              <p style={{ color: '#666', fontSize: '14px' }}>
                Advertisement
              </p>
            </div>
          )}
        </div>
      ))}
      <style jsx>{`
        .ad-container {
          margin: 16px 0;
        }
        .ad-unit {
          position: relative;
        }
      `}</style>
    </div>
  );
}
