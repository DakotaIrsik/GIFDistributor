'use client';

import { useState, useRef } from 'react';

interface UploadStepProps {
  onNext: (file: File) => void;
}

export default function UploadStep({ onNext }: UploadStepProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && isValidFile(droppedFile)) {
      setFile(droppedFile);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isValidFile(selectedFile)) {
      setFile(selectedFile);
    }
  };

  const isValidFile = (f: File) => {
    const validTypes = ['image/gif', 'video/mp4', 'video/webm', 'image/webp'];
    return validTypes.includes(f.type);
  };

  return (
    <div>
      <h2>Upload Media</h2>

      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? '#0070f3' : '#ccc'}`,
          borderRadius: '8px',
          padding: '3rem',
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: dragOver ? '#f0f8ff' : '#fafafa',
          marginTop: '1rem',
        }}
      >
        {file ? (
          <div>
            <p style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>✓ {file.name}</p>
            <p style={{ color: '#666', fontSize: '0.9rem' }}>
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        ) : (
          <div>
            <p style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>
              Drop your file here or click to browse
            </p>
            <p style={{ color: '#666', fontSize: '0.9rem' }}>
              Supported: GIF, MP4, WebM, WebP
            </p>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".gif,.mp4,.webm,.webp"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />

      <button
        onClick={() => file && onNext(file)}
        disabled={!file}
        style={{
          marginTop: '2rem',
          padding: '0.75rem 2rem',
          fontSize: '1rem',
          backgroundColor: file ? '#0070f3' : '#ccc',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          cursor: file ? 'pointer' : 'not-allowed',
          width: '100%',
        }}
      >
        Next: Add Title & Tags
      </button>
    </div>
  );
}
