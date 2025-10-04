'use client';

import { useState } from 'react';

interface PlatformStepProps {
  selectedPlatforms: string[];
  onNext: (platforms: string[]) => void;
  onBack: () => void;
}

const platforms = [
  { id: 'giphy', name: 'GIPHY', icon: '🎨', description: 'Largest GIF platform' },
  { id: 'tenor', name: 'Tenor', icon: '🎭', description: 'Google-owned GIF library' },
  { id: 'slack', name: 'Slack', icon: '💬', description: 'Team communication' },
  { id: 'discord', name: 'Discord', icon: '🎮', description: 'Community chat platform' },
  { id: 'teams', name: 'Microsoft Teams', icon: '💼', description: 'Business collaboration' },
];

export default function PlatformStep({ selectedPlatforms, onNext, onBack }: PlatformStepProps) {
  const [selected, setSelected] = useState<string[]>(selectedPlatforms);

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
      <p style={{ color: '#666', marginTop: '0.5rem' }}>
        Select where you want to publish your content
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1.5rem' }}>
        {platforms.map((platform) => {
          const isSelected = selected.includes(platform.id);
          return (
            <div
              key={platform.id}
              onClick={() => togglePlatform(platform.id)}
              style={{
                padding: '1rem',
                border: `2px solid ${isSelected ? '#0070f3' : '#e0e0e0'}`,
                borderRadius: '8px',
                cursor: 'pointer',
                backgroundColor: isSelected ? '#f0f8ff' : 'white',
                transition: 'all 0.2s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ fontSize: '2rem' }}>{platform.icon}</span>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{platform.name}</h3>
                  <p style={{ margin: '0.25rem 0 0', color: '#666', fontSize: '0.9rem' }}>
                    {platform.description}
                  </p>
                </div>
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
          );
        })}
      </div>

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
          }}
        >
          Next: Distribute
        </button>
      </div>
    </div>
  );
}
