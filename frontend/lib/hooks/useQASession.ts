import { useState, useEffect } from 'react';
import { apiService, QASessionCreate, QASessionResponse, QASession, QARequest, QAResponse } from '../api';

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
      
      // Create a minimal session object for immediate use
      const session: QASession = {
        session_id: response.session_id,
        file_id: response.file_id,
        filename: response.filename,
        created_at: response.created_at,
        messages: [],
        total_messages: 0
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

  const askQuestion = async (question: string): Promise<QAResponse | null> => {
    if (!sessionState.session) {
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
        file_id: sessionState.session.file_id,
        session_id: sessionState.session.session_id,
        filename: sessionState.session.filename,  // Add filename to avoid file lookup
      };

      const response = await apiService.askQuestion(request);
      
      // Reload session to get updated messages
      await loadSession(sessionState.session.session_id);
      
      // Reset isAsking state after successful completion
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
    deleteSession,
    clearError,
    resetSession,
  };
};
