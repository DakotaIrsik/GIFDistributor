/**
 * UploadNotice Component
 * Displays SFW policy notice during upload flow
 * Issue: #31
 */

import React, { useState } from 'react';

interface UploadNoticeProps {
  onAccept: () => void;
  onDecline?: () => void;
  compact?: boolean;
}

export const UploadNotice: React.FC<UploadNoticeProps> = ({
  onAccept,
  onDecline,
  compact = false
}) => {
  const [acknowledged, setAcknowledged] = useState(false);

  const handleAccept = () => {
    if (acknowledged) {
      onAccept();
    }
  };

  if (compact) {
    return (
      <div className="upload-notice upload-notice--compact">
        <div className="upload-notice__content">
          <span className="upload-notice__icon">ℹ️</span>
          <p className="upload-notice__text">
            All content is automatically scanned. Only SFW content is allowed.{' '}
            <a href="/content-policy" target="_blank" rel="noopener noreferrer">
              View Policy
            </a>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="upload-notice">
      <div className="upload-notice__header">
        <h3 className="upload-notice__title">
          📢 Before You Upload
        </h3>
      </div>

      <div className="upload-notice__body">
        <div className="upload-notice__section">
          <h4>🤖 Automated Scanning</h4>
          <p>
            Your content will be automatically scanned using AI-powered moderation:
          </p>
          <ul>
            <li>Metadata analysis (title, tags, description)</li>
            <li>Visual content scanning</li>
            <li>Instant decision in most cases</li>
          </ul>
        </div>

        <div className="upload-notice__section">
          <h4>✅ Three Possible Outcomes</h4>
          <ul>
            <li>
              <strong>Approved:</strong> Published immediately
            </li>
            <li>
              <strong>Rejected:</strong> Policy violation detected
            </li>
            <li>
              <strong>Flagged:</strong> Queued for manual review (24-48hrs)
            </li>
          </ul>
        </div>

        <div className="upload-notice__section upload-notice__section--highlight">
          <h4>⚠️ SFW-Only Platform</h4>
          <p>
            <strong>GIFDistributor is strictly safe-for-work.</strong> Do not upload:
          </p>
          <ul>
            <li>Adult or NSFW content</li>
            <li>Graphic violence or gore</li>
            <li>Hate speech or harassment</li>
            <li>Illegal or copyright-infringing content</li>
          </ul>
        </div>

        <div className="upload-notice__links">
          <a
            href="/content-policy"
            target="_blank"
            rel="noopener noreferrer"
            className="upload-notice__link"
          >
            📋 Full Content Policy
          </a>
          <a
            href="/moderation-faq"
            target="_blank"
            rel="noopener noreferrer"
            className="upload-notice__link"
          >
            ❓ Moderation FAQ
          </a>
          <a
            href="/user-notice"
            target="_blank"
            rel="noopener noreferrer"
            className="upload-notice__link"
          >
            📖 User Guide
          </a>
        </div>

        <div className="upload-notice__acknowledgment">
          <label className="upload-notice__checkbox-label">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="upload-notice__checkbox"
            />
            <span>
              I confirm my content is safe-for-work and complies with the{' '}
              <a href="/content-policy" target="_blank" rel="noopener noreferrer">
                Content Policy
              </a>
            </span>
          </label>
        </div>
      </div>

      <div className="upload-notice__footer">
        <button
          onClick={handleAccept}
          disabled={!acknowledged}
          className="upload-notice__button upload-notice__button--primary"
        >
          Continue Upload
        </button>
        {onDecline && (
          <button
            onClick={onDecline}
            className="upload-notice__button upload-notice__button--secondary"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
};

/**
 * ModerationResult Component
 * Displays the result of automated moderation
 */

export interface ModerationResultData {
  decision: 'approved' | 'rejected' | 'flagged';
  category?: string;
  confidence: number;
  reasons: string[];
  scanId: string;
  timestamp: string;
}

interface ModerationResultProps {
  result: ModerationResultData;
  onAppeal?: (scanId: string) => void;
  onDismiss?: () => void;
}

export const ModerationResult: React.FC<ModerationResultProps> = ({
  result,
  onAppeal,
  onDismiss
}) => {
  const getIcon = () => {
    switch (result.decision) {
      case 'approved':
        return '✅';
      case 'rejected':
        return '❌';
      case 'flagged':
        return '⚠️';
      default:
        return 'ℹ️';
    }
  };

  const getTitle = () => {
    switch (result.decision) {
      case 'approved':
        return 'Content Approved';
      case 'rejected':
        return 'Content Rejected';
      case 'flagged':
        return 'Flagged for Review';
      default:
        return 'Moderation Result';
    }
  };

  const getMessage = () => {
    switch (result.decision) {
      case 'approved':
        return 'Your content passed all moderation checks and is now published!';
      case 'rejected':
        return 'Your content violates our SFW policy and cannot be published.';
      case 'flagged':
        return 'Your content has been flagged for manual review. You\'ll receive an email when a decision is made (usually within 24-48 hours).';
      default:
        return '';
    }
  };

  return (
    <div className={`moderation-result moderation-result--${result.decision}`}>
      <div className="moderation-result__header">
        <span className="moderation-result__icon">{getIcon()}</span>
        <h3 className="moderation-result__title">{getTitle()}</h3>
      </div>

      <div className="moderation-result__body">
        <p className="moderation-result__message">{getMessage()}</p>

        {result.category && (
          <div className="moderation-result__detail">
            <strong>Category:</strong> {result.category}
          </div>
        )}

        <div className="moderation-result__detail">
          <strong>Confidence:</strong> {(result.confidence * 100).toFixed(0)}%
        </div>

        {result.reasons.length > 0 && (
          <div className="moderation-result__reasons">
            <strong>Reasons:</strong>
            <ul>
              {result.reasons.map((reason, index) => (
                <li key={index}>{reason}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="moderation-result__meta">
          <small>Scan ID: {result.scanId}</small>
          <small>Time: {new Date(result.timestamp).toLocaleString()}</small>
        </div>

        {result.decision === 'rejected' && (
          <div className="moderation-result__help">
            <p>
              <strong>What to do next:</strong>
            </p>
            <ul>
              <li>Review our <a href="/content-policy">Content Policy</a></li>
              <li>Ensure your content is safe-for-work</li>
              <li>If you believe this is an error, you may appeal this decision</li>
            </ul>
          </div>
        )}

        {result.decision === 'flagged' && (
          <div className="moderation-result__help">
            <p>
              Our AI couldn't confidently classify your content. A human moderator will review it shortly.
            </p>
          </div>
        )}
      </div>

      <div className="moderation-result__footer">
        {result.decision === 'rejected' && onAppeal && (
          <button
            onClick={() => onAppeal(result.scanId)}
            className="moderation-result__button moderation-result__button--appeal"
          >
            Appeal Decision
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="moderation-result__button moderation-result__button--dismiss"
          >
            {result.decision === 'approved' ? 'Continue' : 'Close'}
          </button>
        )}
      </div>
    </div>
  );
};

/**
 * Usage Example:
 *
 * import { UploadNotice, ModerationResult } from './components/UploadNotice';
 *
 * // During upload flow
 * <UploadNotice
 *   onAccept={() => proceedWithUpload()}
 *   onDecline={() => cancelUpload()}
 * />
 *
 * // After moderation
 * <ModerationResult
 *   result={moderationResult}
 *   onAppeal={(scanId) => handleAppeal(scanId)}
 *   onDismiss={() => closeModal()}
 * />
 */
