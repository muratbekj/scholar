import { useState, useCallback } from 'react';

interface RetryConfig {
  maxAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
}

interface RetryState {
  attempts: number;
  isRetrying: boolean;
  lastError?: Error;
}

export const useRetry = (config: RetryConfig = {}) => {
  const {
    maxAttempts = 3,
    baseDelay = 1000,
    maxDelay = 10000,
    backoffMultiplier = 2
  } = config;

  const [retryState, setRetryState] = useState<RetryState>({
    attempts: 0,
    isRetrying: false
  });

  const calculateDelay = useCallback((attempt: number): number => {
    const delay = baseDelay * Math.pow(backoffMultiplier, attempt);
    return Math.min(delay, maxDelay);
  }, [baseDelay, maxDelay, backoffMultiplier]);

  const retry = useCallback(async <T>(
    operation: () => Promise<T>,
    onSuccess?: (result: T) => void,
    onError?: (error: Error, attempts: number) => void
  ): Promise<T | null> => {
    let lastError: Error;

    for (let attempt = 0; attempt <= maxAttempts; attempt++) {
      try {
        setRetryState(prev => ({
          ...prev,
          attempts: attempt,
          isRetrying: attempt > 0
        }));

        const result = await operation();
        
        // Success - reset retry state
        setRetryState({
          attempts: 0,
          isRetrying: false
        });

        if (onSuccess) {
          onSuccess(result);
        }

        return result;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        setRetryState(prev => ({
          ...prev,
          lastError
        }));

        // If this was the last attempt, don't wait
        if (attempt === maxAttempts) {
          break;
        }

        // Wait before retrying (exponential backoff)
        const delay = calculateDelay(attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    // All attempts failed
    setRetryState(prev => ({
      ...prev,
      isRetrying: false
    }));

    if (onError) {
      onError(lastError!, retryState.attempts);
    }

    return null;
  }, [maxAttempts, calculateDelay]);

  const reset = useCallback(() => {
    setRetryState({
      attempts: 0,
      isRetrying: false
    });
  }, []);

  return {
    retry,
    reset,
    attempts: retryState.attempts,
    isRetrying: retryState.isRetrying,
    lastError: retryState.lastError,
    hasAttemptsLeft: retryState.attempts < maxAttempts
  };
};
