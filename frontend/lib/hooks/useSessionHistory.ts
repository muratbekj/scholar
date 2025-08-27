import { useState, useEffect } from 'react';
import { apiService, QASessionResponse } from '../api';

export interface SessionHistoryState {
  sessions: QASessionResponse[];
  isLoading: boolean;
  error: string | null;
}

export const useSessionHistory = () => {
  const [historyState, setHistoryState] = useState<SessionHistoryState>({
    sessions: [],
    isLoading: false,
    error: null,
  });

  const loadSessions = async () => {
    setHistoryState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
    }));

    try {
      const sessions = await apiService.getAllSessions();
      setHistoryState({
        sessions,
        isLoading: false,
        error: null,
      });
      return sessions;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load sessions';
      setHistoryState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const refreshSessions = () => {
    return loadSessions();
  };

  const removeSessionFromList = (sessionId: string) => {
    setHistoryState(prev => ({
      ...prev,
      sessions: prev.sessions.filter(session => session.session_id !== sessionId),
    }));
  };

  const addSessionToList = (session: QASessionResponse) => {
    setHistoryState(prev => ({
      ...prev,
      sessions: [session, ...prev.sessions],
    }));
  };

  const clearError = () => {
    setHistoryState(prev => ({
      ...prev,
      error: null,
    }));
  };

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  return {
    historyState,
    loadSessions,
    refreshSessions,
    removeSessionFromList,
    addSessionToList,
    clearError,
  };
};
