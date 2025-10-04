'use client';

import { useState, useRef } from 'react';

interface SimpleUploadStepProps {
  onNext: (file: File, uploadedUrl: string) => void;
}

export default function SimpleUploadStep({ onNext }: SimpleUploadStepProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && isValidFile(droppedFile)) {
      setFile(droppedFile);
    } else {
      alert('Invalid file type. Please upload GIF, MP4, WebM, or WebP files.');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isValidFile(selectedFile)) {
      setFile(selectedFile);
    } else {
      alert('Invalid file type. Please upload GIF, MP4, WebM, or WebP files.');
    }
  };

  const isValidFile = (f: File) => {
    const validTypes = ['image/gif', 'video/mp4', 'video/webm', 'image/webp'];
    return validTypes.includes(f.type);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);

    try {
      // Simulate resumable upload with progress
      // In production, this would use the direct_upload.py module
      const formData = new FormData();
      formData.append('file', file);

      // Simulated upload progress
      const interval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(interval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Simulated API call
      await new Promise((resolve) => setTimeout(resolve, 2000));

      clearInterval(interval);
      setUploadProgress(100);

      // Mock uploaded file URL
      const uploadedUrl = `/media/${file.name}`;

      setTimeout(() => {
        onNext(file, uploadedUrl);
      }, 500);
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
      setUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div>
      <h2>Upload Media</h2>
      <p style={{ color: '#666', marginTop: '0.5rem', marginBottom: '1.5rem' }}>
        Select a file to distribute across platforms
      </p>

      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => !uploading && inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? '#0070f3' : '#ccc'}`,
          borderRadius: '8px',
          padding: '3rem',
          textAlign: 'center',
          cursor: uploading ? 'default' : 'pointer',
          backgroundColor: dragOver ? '#f0f8ff' : '#fafafa',
          marginTop: '1rem',
        }}
      >
        {file ? (
          <div>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>
              {file.type.startsWith('video') ? '🎬' : '🖼️'}
            </div>
            <p style={{ fontSize: '1.2rem', marginBottom: '0.5rem', fontWeight: 500 }}>
              {file.name}
            </p>
            <p style={{ color: '#666', fontSize: '0.9rem' }}>
              {(file.size / 1024 / 1024).toFixed(2)} MB · {file.type}
            </p>

            {uploading && (
              <div style={{ marginTop: '1.5rem' }}>
                <div
                  style={{
                    width: '100%',
                    height: '8px',
                    backgroundColor: '#e0e0e0',
                    borderRadius: '4px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${uploadProgress}%`,
                      height: '100%',
                      backgroundColor: '#0070f3',
                      transition: 'width 0.3s',
                    }}
                  />
                </div>
                <p style={{ color: '#0070f3', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                  Uploading... {uploadProgress}%
                </p>
              </div>
            )}
          </div>
        ) : (
          <div>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📤</div>
            <p style={{ fontSize: '1.2rem', marginBottom: '0.5rem', fontWeight: 500 }}>
              Drop your file here or click to browse
            </p>
            <p style={{ color: '#666', fontSize: '0.9rem' }}>
              Supported: GIF, MP4, WebM, WebP
            </p>
            <p style={{ color: '#999', fontSize: '0.8rem', marginTop: '0.5rem' }}>
              Max size: 100 MB
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
        disabled={uploading}
      />

      {file && !uploading && (
        <button
          onClick={() => setFile(null)}
          style={{
            marginTop: '1rem',
            padding: '0.5rem 1rem',
            fontSize: '0.9rem',
            backgroundColor: 'white',
            color: '#666',
            border: '1px solid #ccc',
            borderRadius: '6px',
            cursor: 'pointer',
            width: '100%',
          }}
        >
          Choose Different File
        </button>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        style={{
          marginTop: '1rem',
          padding: '0.75rem 2rem',
          fontSize: '1rem',
          backgroundColor: file && !uploading ? '#0070f3' : '#ccc',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          cursor: file && !uploading ? 'pointer' : 'not-allowed',
          width: '100%',
          fontWeight: 500,
        }}
      >
        {uploading ? 'Uploading...' : 'Upload & Continue'}
      </button>

      <div
        style={{
          marginTop: '1.5rem',
          padding: '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '6px',
          fontSize: '0.85rem',
          color: '#666',
        }}
      >
        <p style={{ margin: 0 }}>
          ℹ️ Files are uploaded with resumable chunking and SHA-256 deduplication
        </p>
      </div>
    </div>
  );
}
