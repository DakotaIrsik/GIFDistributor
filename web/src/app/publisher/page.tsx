'use client';

import { useState } from 'react';
import SimpleUploadStep from '@/components/publisher-simple/SimpleUploadStep';
import SimplePlatformStep from '@/components/publisher-simple/SimplePlatformStep';

type Step = 'upload' | 'platforms';

export default function PublisherPage() {
  const [currentStep, setCurrentStep] = useState<Step>('upload');
  const [fileData, setFileData] = useState<File | null>(null);
  const [uploadedFileUrl, setUploadedFileUrl] = useState<string>('');
  const [platforms, setPlatforms] = useState<string[]>([]);

  const steps: Step[] = ['upload', 'platforms'];
  const stepIndex = steps.indexOf(currentStep);

  return (
    <main style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Quick Publish</h1>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        Upload your media and choose distribution platforms
      </p>

      {/* Progress indicator */}
      <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem', marginBottom: '2rem' }}>
        {steps.map((step, idx) => (
          <div
            key={step}
            style={{
              flex: 1,
              height: '4px',
              backgroundColor: idx <= stepIndex ? '#0070f3' : '#eaeaea',
              borderRadius: '2px',
            }}
          />
        ))}
      </div>

      {/* Step content */}
      {currentStep === 'upload' && (
        <SimpleUploadStep
          onNext={(file, fileUrl) => {
            setFileData(file);
            setUploadedFileUrl(fileUrl);
            setCurrentStep('platforms');
          }}
        />
      )}

      {currentStep === 'platforms' && (
        <SimplePlatformStep
          file={fileData}
          uploadedFileUrl={uploadedFileUrl}
          selectedPlatforms={platforms}
          onNext={(selected) => {
            setPlatforms(selected);
            // Distribution logic would go here
            alert(`Publishing to: ${selected.join(', ')}`);
          }}
          onBack={() => setCurrentStep('upload')}
        />
      )}
    </main>
  );
}
