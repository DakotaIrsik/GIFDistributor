"use client";

/**
 * WatermarkPolicyNotice - Explains the no-watermark policy
 *
 * This component informs users that:
 * - Media files NEVER have watermarks or embedded ads
 * - Only the website UI shows ads (free tier users only)
 * - Pro/Team tiers get completely ad-free experience
 */
export default function WatermarkPolicyNotice() {
  return (
    <div className="watermark-policy-notice">
      <div className="policy-card">
        <h3>🎨 Clean Media Guarantee</h3>
        <div className="policy-content">
          <div className="policy-item">
            <span className="icon">✨</span>
            <div>
              <strong>No Watermarks</strong>
              <p>Your GIFs and media files remain completely clean - no logos, no watermarks, ever.</p>
            </div>
          </div>

          <div className="policy-item">
            <span className="icon">🚫</span>
            <div>
              <strong>No Embedded Ads</strong>
              <p>Media files never contain burned-in advertisements. They stay 100% shareable.</p>
            </div>
          </div>

          <div className="policy-item">
            <span className="icon">💰</span>
            <div>
              <strong>Website Ads Only</strong>
              <p>Free tier: Ads appear on the website UI. Pro/Team tiers: Completely ad-free.</p>
            </div>
          </div>
        </div>

        <div className="tier-comparison">
          <div className="tier">
            <h4>Free Tier</h4>
            <ul>
              <li>✅ Clean media files (no watermarks)</li>
              <li>📺 Ads on website UI</li>
            </ul>
          </div>
          <div className="tier highlight">
            <h4>Pro / Team Tier</h4>
            <ul>
              <li>✅ Clean media files (no watermarks)</li>
              <li>✨ Ad-free website experience</li>
            </ul>
          </div>
        </div>
      </div>

      <style jsx>{`
        .watermark-policy-notice {
          margin: 24px 0;
        }
        .policy-card {
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 24px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .policy-card h3 {
          margin: 0 0 16px 0;
          color: #333;
          font-size: 20px;
        }
        .policy-content {
          display: flex;
          flex-direction: column;
          gap: 16px;
          margin-bottom: 24px;
        }
        .policy-item {
          display: flex;
          gap: 12px;
          align-items: flex-start;
        }
        .policy-item .icon {
          font-size: 24px;
          flex-shrink: 0;
        }
        .policy-item strong {
          display: block;
          color: #333;
          margin-bottom: 4px;
        }
        .policy-item p {
          margin: 0;
          color: #666;
          font-size: 14px;
        }
        .tier-comparison {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-top: 16px;
        }
        .tier {
          padding: 16px;
          background: #f9f9f9;
          border-radius: 6px;
        }
        .tier.highlight {
          background: #e3f2fd;
          border: 2px solid #2196f3;
        }
        .tier h4 {
          margin: 0 0 12px 0;
          color: #333;
          font-size: 16px;
        }
        .tier ul {
          margin: 0;
          padding: 0;
          list-style: none;
        }
        .tier li {
          padding: 4px 0;
          color: #666;
          font-size: 14px;
        }
        @media (max-width: 768px) {
          .tier-comparison {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
