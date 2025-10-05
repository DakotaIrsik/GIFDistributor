'use client';

import { useState } from 'react';

interface MetadataStepProps {
  initialMetadata: { title: string; tags: string[] };
  onNext: (metadata: { title: string; tags: string[] }) => void;
  onBack: () => void;
}

export default function MetadataStep({ initialMetadata, onNext, onBack }: MetadataStepProps) {
  const [title, setTitle] = useState(initialMetadata.title);
  const [tags, setTags] = useState<string[]>(initialMetadata.tags);
  const [tagInput, setTagInput] = useState('');

  const addTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  };

  return (
    <div>
      <h2>Add Title & Tags</h2>

      <div style={{ marginTop: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
          Title
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Enter a descriptive title"
          style={{
            width: '100%',
            padding: '0.75rem',
            fontSize: '1rem',
            border: '1px solid #ccc',
            borderRadius: '6px',
          }}
        />
      </div>

      <div style={{ marginTop: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
          Tags
        </label>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Add tags (press Enter)"
            style={{
              flex: 1,
              padding: '0.75rem',
              fontSize: '1rem',
              border: '1px solid #ccc',
              borderRadius: '6px',
            }}
          />
          <button
            onClick={addTag}
            style={{
              padding: '0.75rem 1.5rem',
              fontSize: '1rem',
              backgroundColor: '#0070f3',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            Add
          </button>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
          {tags.map((tag) => (
            <span
              key={tag}
              style={{
                padding: '0.5rem 0.75rem',
                backgroundColor: '#e0f2fe',
                color: '#0369a1',
                borderRadius: '16px',
                fontSize: '0.9rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              {tag}
              <button
                onClick={() => removeTag(tag)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#0369a1',
                  cursor: 'pointer',
                  padding: '0',
                  fontSize: '1.1rem',
                }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
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
          onClick={() => onNext({ title, tags })}
          disabled={!title.trim()}
          style={{
            flex: 1,
            padding: '0.75rem',
            fontSize: '1rem',
            backgroundColor: title.trim() ? '#0070f3' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: title.trim() ? 'pointer' : 'not-allowed',
          }}
        >
          Next: Choose Platforms
        </button>
      </div>
    </div>
  );
}
