import { useState, useEffect, useRef } from 'react';
import {
  apiService,
  QASessionCreate,
  QASessionResponse,
  QASession,
  QARequest,
  QAResponse,
  QAGenerationMode,
} from '../api';

export interface QASessionState {
  session: QASession | null;
  isLoading: boolean;
  error: string | null;
  isCreating: boolean;
  isAsking: boolean;
}

export const useQASession = () => {
  const [sessionState, setSessionState] = useState<QASessionState>({
    session: null,
    isLoading: false,
    error: null,
    isCreating: false,
    isAsking: false,
  });

  const sessionRef = useRef<QASession | null>(null);
  useEffect(() => {
    sessionRef.current = sessionState.session;
  }, [sessionState.session]);

  const createSession = async (fileId: string, filename: string): Promise<QASessionResponse | null> => {
    setSessionState(prev => ({
      ...prev,
      isCreating: true,
      error: null,
    }));

    try {
      const sessionData: QASessionCreate = {
        file_id: fileId,
        filename: filename,
      };

      const response = await apiService.createQASession(sessionData);

      const session: QASession = {
        session_id: response.session_id,
        file_id: response.file_id,
        filename: response.filename,
        created_at: response.created_at,
        messages: [],
        total_messages: 0,
      };

      setSessionState(prev => ({
        ...prev,
        session,
        isCreating: false,
      }));

      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create session';
      setSessionState(prev => ({
        ...prev,
        isCreating: false,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const loadSession = async (sessionId: string): Promise<QASession | null> => {
    setSessionState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
    }));

    try {
      const session = await apiService.getSession(sessionId);
      setSessionState(prev => ({
        ...prev,
        session,
        isLoading: false,
        isCreating: false,
      }));
      return session;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load session';
      setSessionState(prev => ({
        ...prev,
        isLoading: false,
        isCreating: false,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const askQuestion = async (
    question: string,
    options?: { generationMode?: QAGenerationMode }
  ): Promise<QAResponse | null> => {
    const sess = sessionRef.current;
    if (!sess) {
      throw new Error('No active session');
    }

    setSessionState(prev => ({
      ...prev,
      isAsking: true,
      error: null,
    }));

    try {
      const request: QARequest = {
        question,
        file_id: sess.file_id,
        session_id: sess.session_id,
        filename: sess.filename,
        generation_mode: options?.generationMode ?? 'standard',
      };

      const response = await apiService.askQuestion(request);

      await loadSession(sess.session_id);

      setSessionState(prev => ({
        ...prev,
        isAsking: false,
      }));

      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to get answer';
      setSessionState(prev => ({
        ...prev,
        isAsking: false,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const submitReflection = async (
    reflection: string,
    pendingQuestionId?: string | null
  ): Promise<QAResponse | null> => {
    const sess = sessionRef.current;
    if (!sess) {
      throw new Error('No active session');
    }

    setSessionState(prev => ({
      ...prev,
      isAsking: true,
      error: null,
    }));

    try {
      const response = await apiService.submitReflection({
        session_id: sess.session_id,
        reflection: reflection.trim(),
        pending_question_id: pendingQuestionId ?? undefined,
      });

      await loadSession(sess.session_id);

      setSessionState(prev => ({
        ...prev,
        isAsking: false,
      }));

      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to submit reflection';
      setSessionState(prev => ({
        ...prev,
        isAsking: false,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const deleteSession = async (sessionId: string): Promise<boolean> => {
    try {
      await apiService.deleteSession(sessionId);
      setSessionState({
        session: null,
        isLoading: false,
        error: null,
        isCreating: false,
        isAsking: false,
      });
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete session';
      setSessionState(prev => ({
        ...prev,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const clearError = () => {
    setSessionState(prev => ({
      ...prev,
      error: null,
    }));
  };

  const resetSession = () => {
    setSessionState({
      session: null,
      isLoading: false,
      error: null,
      isCreating: false,
      isAsking: false,
    });
  };

  return {
    sessionState,
    createSession,
    loadSession,
    askQuestion,
    submitReflection,
    deleteSession,
    clearError,
    resetSession,
  };
};
