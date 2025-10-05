'use client';

import { useState } from 'react';

interface SimplePlatformStepProps {
  file: File | null;
  uploadedFileUrl: string;
  selectedPlatforms: string[];
  onNext: (platforms: string[]) => void;
  onBack: () => void;
}

interface Platform {
  id: string;
  name: string;
  icon: string;
  description: string;
  status: 'available' | 'coming-soon';
  requirements?: string[];
}

const platforms: Platform[] = [
  {
    id: 'giphy',
    name: 'GIPHY',
    icon: '🎨',
    description: 'Largest GIF platform with searchable library',
    status: 'available',
    requirements: ['GIPHY partner account', 'API key'],
  },
  {
    id: 'tenor',
    name: 'Tenor',
    icon: '🎭',
    description: 'Google-owned GIF library for search & share',
    status: 'available',
    requirements: ['Tenor partner account', 'API credentials'],
  },
  {
    id: 'slack',
    name: 'Slack',
    icon: '💬',
    description: 'Post to Slack channels with hosted media',
    status: 'available',
    requirements: ['Slack app OAuth', 'Workspace access'],
  },
  {
    id: 'discord',
    name: 'Discord',
    icon: '🎮',
    description: 'Share in Discord servers as embeds',
    status: 'available',
    requirements: ['Discord bot token', 'Server permissions'],
  },
  {
    id: 'teams',
    name: 'Microsoft Teams',
    icon: '💼',
    description: 'Distribute via Teams message extension',
    status: 'available',
    requirements: ['Teams app registration', 'OAuth'],
  },
];

export default function SimplePlatformStep({
  file,
  uploadedFileUrl,
  selectedPlatforms,
  onNext,
  onBack,
}: SimplePlatformStepProps) {
  const [selected, setSelected] = useState<string[]>(selectedPlatforms);
  const [showDetails, setShowDetails] = useState<string | null>(null);

  const togglePlatform = (platformId: string) => {
    setSelected((prev) =>
      prev.includes(platformId)
        ? prev.filter((id) => id !== platformId)
        : [...prev, platformId]
    );
  };

  return (
    <div>
      <h2>Choose Distribution Platforms</h2>
      <p style={{ color: '#666', marginTop: '0.5rem', marginBottom: '1.5rem' }}>
        Select where you want to publish your content
      </p>

      {/* File preview */}
      {file && (
        <div
          style={{
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '6px',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          <span style={{ fontSize: '2rem' }}>
            {file.type.startsWith('video') ? '🎬' : '🖼️'}
          </span>
          <div style={{ flex: 1 }}>
            <p style={{ margin: 0, fontWeight: 500, fontSize: '0.95rem' }}>{file.name}</p>
            <p style={{ margin: '0.25rem 0 0', color: '#666', fontSize: '0.85rem' }}>
              {(file.size / 1024 / 1024).toFixed(2)} MB · Ready to distribute
            </p>
          </div>
        </div>
      )}

      {/* Platform selection */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {platforms.map((platform) => {
          const isSelected = selected.includes(platform.id);
          const isExpanded = showDetails === platform.id;
          const isComingSoon = platform.status === 'coming-soon';

          return (
            <div
              key={platform.id}
              style={{
                border: `2px solid ${isSelected ? '#0070f3' : '#e0e0e0'}`,
                borderRadius: '8px',
                backgroundColor: isSelected ? '#f0f8ff' : 'white',
                opacity: isComingSoon ? 0.6 : 1,
              }}
            >
              <div
                onClick={() => !isComingSoon && togglePlatform(platform.id)}
                style={{
                  padding: '1rem',
                  cursor: isComingSoon ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                }}
              >
                <span style={{ fontSize: '2rem' }}>{platform.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{platform.name}</h3>
                    {isComingSoon && (
                      <span
                        style={{
                          fontSize: '0.7rem',
                          padding: '0.2rem 0.5rem',
                          backgroundColor: '#ffa500',
                          color: 'white',
                          borderRadius: '3px',
                          fontWeight: 600,
                        }}
                      >
                        COMING SOON
                      </span>
                    )}
                  </div>
                  <p style={{ margin: '0.25rem 0 0', color: '#666', fontSize: '0.9rem' }}>
                    {platform.description}
                  </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {!isComingSoon && platform.requirements && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowDetails(isExpanded ? null : platform.id);
                      }}
                      style={{
                        padding: '0.4rem 0.8rem',
                        fontSize: '0.8rem',
                        backgroundColor: 'white',
                        color: '#0070f3',
                        border: '1px solid #0070f3',
                        borderRadius: '4px',
                        cursor: 'pointer',
                      }}
                    >
                      {isExpanded ? 'Hide' : 'Info'}
                    </button>
                  )}
                  <div
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      border: `2px solid ${isSelected ? '#0070f3' : '#ccc'}`,
                      backgroundColor: isSelected ? '#0070f3' : 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {isSelected && <span style={{ color: 'white', fontSize: '1rem' }}>✓</span>}
                  </div>
                </div>
              </div>

              {/* Platform requirements details */}
              {isExpanded && platform.requirements && (
                <div
                  style={{
                    padding: '1rem',
                    borderTop: '1px solid #e0e0e0',
                    backgroundColor: '#fafafa',
                  }}
                >
                  <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>
                    Requirements:
                  </p>
                  <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                    {platform.requirements.map((req, idx) => (
                      <li key={idx} style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>
                        {req}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary */}
      {selected.length > 0 && (
        <div
          style={{
            marginTop: '1.5rem',
            padding: '1rem',
            backgroundColor: '#e7f5ff',
            borderRadius: '6px',
            border: '1px solid #339af0',
          }}
        >
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#1971c2' }}>
            ✓ Selected {selected.length} platform{selected.length !== 1 ? 's' : ''}: {' '}
            <strong>{platforms.filter((p) => selected.includes(p.id)).map((p) => p.name).join(', ')}</strong>
          </p>
        </div>
      )}

      {/* Navigation buttons */}
      <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
        <button
          onClick={onBack}
          style={{
            flex: 1,
            padding: '0.75rem',
            fontSize: '1rem',
            backgroundColor: 'white',
            color: '#666',
            border: '1px solid #ccc',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 500,
          }}
        >
          Back
        </button>
        <button
          onClick={() => onNext(selected)}
          disabled={selected.length === 0}
          style={{
            flex: 1,
            padding: '0.75rem',
            fontSize: '1rem',
            backgroundColor: selected.length > 0 ? '#0070f3' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: selected.length > 0 ? 'pointer' : 'not-allowed',
            fontWeight: 500,
          }}
        >
          Distribute Now
        </button>
      </div>
    </div>
  );
}
