'use client';

import { useState } from 'react';

interface DistributeStepProps {
  file: File | null;
  metadata: { title: string; tags: string[] };
  platforms: string[];
  onBack: () => void;
}

type DistributionStatus = 'pending' | 'uploading' | 'processing' | 'success' | 'error';

interface PlatformStatus {
  platform: string;
  status: DistributionStatus;
  message?: string;
}

export default function DistributeStep({ file, metadata, platforms, onBack }: DistributeStepProps) {
  const [isDistributing, setIsDistributing] = useState(false);
  const [platformStatuses, setPlatformStatuses] = useState<PlatformStatus[]>([]);

  const startDistribution = async () => {
    setIsDistributing(true);

    // Initialize statuses
    const initialStatuses = platforms.map((p) => ({
      platform: p,
      status: 'pending' as DistributionStatus,
    }));
    setPlatformStatuses(initialStatuses);

    // Simulate distribution process
    for (let i = 0; i < platforms.length; i++) {
      const platform = platforms[i];

      // Update to uploading
      setPlatformStatuses((prev) =>
        prev.map((ps) =>
          ps.platform === platform ? { ...ps, status: 'uploading' } : ps
        )
      );
      await delay(1000);

      // Update to processing
      setPlatformStatuses((prev) =>
        prev.map((ps) =>
          ps.platform === platform ? { ...ps, status: 'processing' } : ps
        )
      );
      await delay(1500);

      // Update to success
      setPlatformStatuses((prev) =>
        prev.map((ps) =>
          ps.platform === platform
            ? { ...ps, status: 'success', message: 'Published successfully' }
            : ps
        )
      );
    }

    setIsDistributing(false);
  };

  const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  const getStatusIcon = (status: DistributionStatus) => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'uploading':
        return '📤';
      case 'processing':
        return '⚙️';
      case 'success':
        return '✅';
      case 'error':
        return '❌';
    }
  };

  const getStatusColor = (status: DistributionStatus) => {
    switch (status) {
      case 'pending':
        return '#999';
      case 'uploading':
      case 'processing':
        return '#0070f3';
      case 'success':
        return '#10b981';
      case 'error':
        return '#ef4444';
    }
  };

  const allSuccess = platformStatuses.every((ps) => ps.status === 'success');

  return (
    <div>
      <h2>Distribute Content</h2>

      <div
        style={{
          padding: '1.5rem',
          backgroundColor: '#f9fafb',
          borderRadius: '8px',
          marginTop: '1.5rem',
        }}
      >
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Summary</h3>
        <p style={{ margin: '0.5rem 0' }}>
          <strong>File:</strong> {file?.name}
        </p>
        <p style={{ margin: '0.5rem 0' }}>
          <strong>Title:</strong> {metadata.title}
        </p>
        <p style={{ margin: '0.5rem 0' }}>
          <strong>Tags:</strong> {metadata.tags.join(', ') || 'None'}
        </p>
        <p style={{ margin: '0.5rem 0' }}>
          <strong>Platforms:</strong> {platforms.join(', ')}
        </p>
      </div>

      {platformStatuses.length > 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Distribution Status</h3>
          {platformStatuses.map((ps) => (
            <div
              key={ps.platform}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                padding: '1rem',
                border: '1px solid #e0e0e0',
                borderRadius: '6px',
                marginBottom: '0.5rem',
              }}
            >
              <span style={{ fontSize: '1.5rem' }}>{getStatusIcon(ps.status)}</span>
              <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontWeight: '500', textTransform: 'capitalize' }}>
                  {ps.platform}
                </p>
                {ps.message && (
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.9rem', color: '#666' }}>
                    {ps.message}
                  </p>
                )}
              </div>
              <span
                style={{
                  fontSize: '0.85rem',
                  fontWeight: '500',
                  color: getStatusColor(ps.status),
                  textTransform: 'capitalize',
                }}
              >
                {ps.status}
              </span>
            </div>
          ))}
        </div>
      )}

      {allSuccess && (
        <div
          style={{
            padding: '1rem',
            backgroundColor: '#d1fae5',
            color: '#065f46',
            borderRadius: '6px',
            marginTop: '1rem',
            textAlign: 'center',
          }}
        >
          🎉 All platforms published successfully!
        </div>
      )}

      <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
        <button
          onClick={onBack}
          disabled={isDistributing}
          style={{
            flex: 1,
            padding: '0.75rem',
            fontSize: '1rem',
            backgroundColor: 'white',
            color: '#666',
            border: '1px solid #ccc',
            borderRadius: '6px',
            cursor: isDistributing ? 'not-allowed' : 'pointer',
            opacity: isDistributing ? 0.5 : 1,
          }}
        >
          Back
        </button>
        <button
          onClick={startDistribution}
          disabled={isDistributing || allSuccess}
          style={{
            flex: 1,
            padding: '0.75rem',
            fontSize: '1rem',
            backgroundColor: isDistributing || allSuccess ? '#ccc' : '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: isDistributing || allSuccess ? 'not-allowed' : 'pointer',
          }}
        >
          {isDistributing ? 'Distributing...' : allSuccess ? 'Complete' : 'Start Distribution'}
        </button>
      </div>
    </div>
  );
}
