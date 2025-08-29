import { useState, useCallback } from 'react';
import { apiService, FlashcardRequest, FlashcardResponse, Flashcard } from '@/lib/api';

interface FlashcardState {
  isGenerating: boolean;
  error: string | null;
  flashcards: Flashcard[];
  response: FlashcardResponse | null;
}

export function useFlashcardGeneration() {
  const [state, setState] = useState<FlashcardState>({
    isGenerating: false,
    error: null,
    flashcards: [],
    response: null,
  });

  const generateFlashcards = useCallback(async (request: FlashcardRequest) => {
    setState(prev => ({ ...prev, isGenerating: true, error: null }));
    
    try {
      const response = await apiService.generateFlashcards(request);
      setState(prev => ({ 
        ...prev, 
        flashcards: response.flashcards,
        response,
        isGenerating: false 
      }));
      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate flashcards';
      setState(prev => ({ ...prev, error: errorMessage, isGenerating: false }));
      throw error;
    }
  }, []);

  const resetFlashcards = useCallback(() => {
    setState({
      isGenerating: false,
      error: null,
      flashcards: [],
      response: null,
    });
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    generateFlashcards,
    resetFlashcards,
    clearError,
  };
}
