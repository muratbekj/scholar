import { useState, useCallback } from 'react';
import { apiService, QuizRequest, QuizResponse, QuizQuestionResponse, QuizSessionCreate, QuizSubmission, QuizResult } from '@/lib/api';

interface QuizState {
  isGenerating: boolean;
  isCreatingSession: boolean;
  isSubmitting: boolean;
  error: string | null;
  quiz: QuizResponse | null;
  questions: QuizQuestionResponse[];
  sessionId: string | null;
  result: QuizResult | null;
}

export function useQuiz() {
  const [state, setState] = useState<QuizState>({
    isGenerating: false,
    isCreatingSession: false,
    isSubmitting: false,
    error: null,
    quiz: null,
    questions: [],
    sessionId: null,
    result: null,
  });

  const generateQuiz = useCallback(async (request: QuizRequest) => {
    setState(prev => ({ ...prev, isGenerating: true, error: null }));
    
    try {
      const quiz = await apiService.generateQuiz(request);
      setState(prev => ({ ...prev, quiz, isGenerating: false }));
      return quiz;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate quiz';
      setState(prev => ({ ...prev, error: errorMessage, isGenerating: false }));
      throw error;
    }
  }, []);

  const createSession = useCallback(async (sessionData: QuizSessionCreate) => {
    setState(prev => ({ ...prev, isCreatingSession: true, error: null }));
    
    try {
      const session = await apiService.createQuizSession(sessionData);
      setState(prev => ({ 
        ...prev, 
        sessionId: session.session_id, 
        isCreatingSession: false 
      }));
      return session;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create session';
      setState(prev => ({ ...prev, error: errorMessage, isCreatingSession: false }));
      throw error;
    }
  }, []);

  const getQuestions = useCallback(async (quizId: string) => {
    try {
      const questions = await apiService.getQuizQuestions(quizId);
      setState(prev => ({ ...prev, questions }));
      return questions;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to get questions';
      setState(prev => ({ ...prev, error: errorMessage }));
      throw error;
    }
  }, []);

  const submitQuiz = useCallback(async (submission: QuizSubmission) => {
    setState(prev => ({ ...prev, isSubmitting: true, error: null }));
    
    try {
      const result = await apiService.submitQuiz(submission);
      setState(prev => ({ ...prev, result, isSubmitting: false }));
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to submit quiz';
      setState(prev => ({ ...prev, error: errorMessage, isSubmitting: false }));
      throw error;
    }
  }, []);

  const resetQuiz = useCallback(() => {
    setState({
      isGenerating: false,
      isCreatingSession: false,
      isSubmitting: false,
      error: null,
      quiz: null,
      questions: [],
      sessionId: null,
      result: null,
    });
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    generateQuiz,
    createSession,
    getQuestions,
    submitQuiz,
    resetQuiz,
    clearError,
  };
}
