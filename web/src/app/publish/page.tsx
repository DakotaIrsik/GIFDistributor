'use client';

import { useState } from 'react';
import UploadStep from '@/components/publisher/UploadStep';
import MetadataStep from '@/components/publisher/MetadataStep';
import PlatformStep from '@/components/publisher/PlatformStep';
import DistributeStep from '@/components/publisher/DistributeStep';

type Step = 'upload' | 'metadata' | 'platforms' | 'distribute';

export default function PublishPage() {
  const [currentStep, setCurrentStep] = useState<Step>('upload');
  const [fileData, setFileData] = useState<File | null>(null);
  const [metadata, setMetadata] = useState({ title: '', tags: [] as string[] });
  const [platforms, setPlatforms] = useState<string[]>([]);

  const steps: Step[] = ['upload', 'metadata', 'platforms', 'distribute'];
  const stepIndex = steps.indexOf(currentStep);

  return (
    <main style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Publish Content</h1>

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
        <UploadStep
          onNext={(file) => {
            setFileData(file);
            setCurrentStep('metadata');
          }}
        />
      )}

      {currentStep === 'metadata' && (
        <MetadataStep
          initialMetadata={metadata}
          onNext={(meta) => {
            setMetadata(meta);
            setCurrentStep('platforms');
          }}
          onBack={() => setCurrentStep('upload')}
        />
      )}

      {currentStep === 'platforms' && (
        <PlatformStep
          selectedPlatforms={platforms}
          onNext={(selected) => {
            setPlatforms(selected);
            setCurrentStep('distribute');
          }}
          onBack={() => setCurrentStep('metadata')}
        />
      )}

      {currentStep === 'distribute' && (
        <DistributeStep
          file={fileData}
          metadata={metadata}
          platforms={platforms}
          onBack={() => setCurrentStep('platforms')}
        />
      )}
    </main>
  );
}
