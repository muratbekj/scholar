import { useState } from 'react';
import { apiService, FileUploadResponse } from '../api';
import { useRetry } from './useRetry';

export interface UploadState {
  isUploading: boolean;
  uploadProgress: number;
  error: string | null;
  uploadResult: FileUploadResponse | null;
  processingSteps: ProcessingStep[];
}

export interface ProcessingStep {
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  details?: string;
  duration?: number;
}

export const useFileUpload = () => {
  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    uploadProgress: 0,
    error: null,
    uploadResult: null,
    processingSteps: [],
  });

  const { retry } = useRetry({ maxAttempts: 3 });

  const uploadFile = async (file: File, studyMode: string) => {
    // Initialize processing steps based on study mode
    const initialSteps: ProcessingStep[] = [
      { name: 'Uploading file', status: 'pending' as const },
      { name: 'Extracting text', status: 'pending' as const },
      { name: 'Chunking content', status: 'pending' as const },
      ...(studyMode === 'qa' ? [
        { name: 'Generating embeddings', status: 'pending' as const },
        { name: 'Storing in vector database', status: 'pending' as const }
      ] : []),
      { name: 'Finalizing', status: 'pending' as const }
    ];

    setUploadState(prev => ({
      ...prev,
      isUploading: true,
      uploadProgress: 0,
      error: null,
      uploadResult: null,
      processingSteps: initialSteps,
    }));

    return retry(
      async () => {
        // Simulate progress updates and step progression
        const progressInterval = setInterval(() => {
          setUploadState(prev => ({
            ...prev,
            uploadProgress: Math.min(prev.uploadProgress + 5, 90),
          }));
        }, 300);

        // Simulate step progression
        const stepInterval = setInterval(() => {
          setUploadState(prev => {
            const currentStepIndex = Math.floor((prev.uploadProgress / 90) * (prev.processingSteps.length - 1));
            const updatedSteps = prev.processingSteps.map((step, index) => {
              if (index < currentStepIndex) {
                return { ...step, status: 'completed' as const, duration: Math.random() * 2 + 0.5 };
              } else if (index === currentStepIndex) {
                return { ...step, status: 'processing' as const };
              }
              return step;
            });
            return { ...prev, processingSteps: updatedSteps };
          });
        }, 800);

        try {
          const result = await apiService.uploadFile(file, studyMode);

          clearInterval(progressInterval);
          clearInterval(stepInterval);

          // Mark all steps as completed
          setUploadState(prev => ({
            ...prev,
            isUploading: false,
            uploadProgress: 100,
            uploadResult: result,
            processingSteps: prev.processingSteps.map(step => ({
              ...step,
              status: 'completed' as const,
              duration: step.duration || Math.random() * 2 + 0.5
            }))
          }));

          return result;
        } catch (error) {
          clearInterval(progressInterval);
          clearInterval(stepInterval);
          throw error;
        }
      },
      (result) => {
        // Success callback
        console.log('Upload successful:', result);
      },
      (error, attempts) => {
        // Error callback
        setUploadState(prev => ({
          ...prev,
          isUploading: false,
          uploadProgress: 0,
          error: `Upload failed after ${attempts} attempts: ${error.message}`,
          processingSteps: prev.processingSteps.map(step => ({
            ...step,
            status: 'error' as const
          }))
        }));
      }
    );
  };

  const resetUpload = () => {
    setUploadState({
      isUploading: false,
      uploadProgress: 0,
      error: null,
      uploadResult: null,
      processingSteps: [],
    });
  };

  return {
    uploadState,
    uploadFile,
    resetUpload,
  };
};
