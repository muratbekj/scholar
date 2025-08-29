// API service layer for backend communication
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types matching backend models
export interface FileUploadResponse {
  message: string;
  file_id: string;
  filename: string;
  size: number;
  upload_time: string;
  content_summary: string;
  rag_processing?: {
    processing_time_seconds: number;
    chunking: any;
    embedding: any;
    vector_storage: any;
  };
}

export interface QARequest {
  question: string;
  file_id?: string;
  session_id?: string;
  filename?: string;  // Add filename field
  use_rag?: boolean;
  search_k?: number;
}

export interface QAResponse {
  answer: string;
  session_id: string;
  message_id: string;
  timestamp: string;
  rag_context?: any;
  processing_time: number;
  confidence_score?: number;
}

export interface QASessionCreate {
  file_id: string;
  filename: string;
}

export interface QASessionResponse {
  session_id: string;
  file_id: string;
  filename: string;
  created_at: string;
  message_count: number;
}

export interface QAMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: string;
  metadata?: any;
}

export interface QASession {
  session_id: string;
  file_id: string;
  filename: string;
  created_at: string;
  messages: QAMessage[];
  total_messages: number;  // Add total_messages field
  session_duration?: number;
}

// Quiz Types
export interface QuizRequest {
  file_id: string;
  filename: string;
  num_questions: number;
  difficulty: 'easy' | 'medium' | 'hard';
  question_types?: ('multiple_choice' | 'true_false' | 'short_answer')[];
  include_explanations?: boolean;
  estimated_time?: number;
}

export interface QuizResponse {
  quiz_id: string;
  title: string;
  description?: string;
  file_id: string;
  filename: string;
  total_questions: number;
  total_points: number;
  difficulty: 'easy' | 'medium' | 'hard';
  estimated_time?: number;
  created_at: string;
  processing_time: number;
}

export interface QuizQuestionResponse {
  id: string;
  question: string;
  question_type: 'multiple_choice' | 'true_false' | 'short_answer';
  options?: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  points: number;
}

export interface QuizSessionCreate {
  quiz_id: string;
  file_id: string;
  filename: string;
}

export interface QuizSessionResponse {
  session_id: string;
  quiz_id: string;
  file_id: string;
  filename: string;
  started_at: string;
  is_completed: boolean;
  score?: number;
  time_taken?: number;
}

export interface QuizSubmission {
  session_id: string;
  answers: Record<string, string>;  // question_id -> user_answer
}

export interface QuizResult {
  session_id: string;
  quiz_id: string;
  score: number;  // percentage
  total_points_earned: number;
  total_possible_points: number;
  correct_answers: number;
  total_questions: number;
  time_taken: number;  // in seconds
  completed_at: string;
  question_results: Array<{
    question_id: string;
    question: string;
    user_answer: string;
    correct_answer: string;
    is_correct: boolean;
    points_earned: number;
    explanation?: string;
  }>;
  feedback?: string;
}

// Flashcard Types
export interface FlashcardRequest {
  file_id: string;
  filename: string;
}

export interface Flashcard {
  id: string;
  front: string;  // Question/prompt
  back: string;   // Answer/explanation
  difficulty: 'easy' | 'medium' | 'hard';
  category?: string;
}

export interface FlashcardResponse {
  flashcards: Flashcard[];
  file_id: string;
  filename: string;
  total_cards: number;
  processing_time: number;
  created_at: string;
}

// API service class
class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      throw error;
    }
  }

  // File upload with study mode
  async uploadFile(file: File, studyMode: string): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const url = `${this.baseUrl}/files/upload?study_mode=${studyMode}`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('File upload failed:', error);
      throw error;
    }
  }

  // Create QA session
  async createQASession(sessionData: QASessionCreate): Promise<QASessionResponse> {
    return this.request<QASessionResponse>('/qa/sessions', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    });
  }

  // Ask question
  async askQuestion(request: QARequest): Promise<QAResponse> {
    return this.request<QAResponse>('/qa/ask', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Get session with messages
  async getSession(sessionId: string): Promise<QASession> {
    return this.request<QASession>(`/qa/sessions/${sessionId}`);
  }

  // Get all sessions
  async getAllSessions(): Promise<QASessionResponse[]> {
    return this.request<QASessionResponse[]>('/qa/sessions');
  }

  // Delete session
  async deleteSession(sessionId: string): Promise<{ message: string; session_id: string }> {
    return this.request<{ message: string; session_id: string }>(`/qa/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  // Health check
  async healthCheck(): Promise<{ status: string; service: string }> {
    return this.request<{ status: string; service: string }>('/health');
  }

  // Quiz API Methods
  async generateQuiz(request: QuizRequest): Promise<QuizResponse> {
    return this.request<QuizResponse>('/quiz/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async createQuizSession(sessionData: QuizSessionCreate): Promise<QuizSessionResponse> {
    return this.request<QuizSessionResponse>('/quiz/sessions', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    });
  }

  async getQuizQuestions(quizId: string): Promise<QuizQuestionResponse[]> {
    return this.request<QuizQuestionResponse[]>(`/quiz/${quizId}/questions`);
  }

  async submitQuiz(submission: QuizSubmission): Promise<QuizResult> {
    return this.request<QuizResult>('/quiz/submit', {
      method: 'POST',
      body: JSON.stringify(submission),
    });
  }

  async getQuizSession(sessionId: string): Promise<QuizSessionResponse> {
    return this.request<QuizSessionResponse>(`/quiz/sessions/${sessionId}`);
  }

  async getAllQuizSessions(): Promise<QuizSessionResponse[]> {
    return this.request<QuizSessionResponse[]>('/quiz/sessions');
  }

  async deleteQuizSession(sessionId: string): Promise<{ message: string; session_id: string }> {
    return this.request<{ message: string; session_id: string }>(`/quiz/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  async quizHealthCheck(): Promise<{ status: string; service: string; active_quizzes: number; active_sessions: number; llm_integration: string }> {
    return this.request<{ status: string; service: string; active_quizzes: number; active_sessions: number; llm_integration: string }>('/quiz/health');
  }

  // Flashcard API Methods
  async generateFlashcards(request: FlashcardRequest): Promise<FlashcardResponse> {
    return this.request<FlashcardResponse>('/flashcards/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async flashcardHealthCheck(): Promise<{ status: string; service: string; llm_integration: string }> {
    return this.request<{ status: string; service: string; llm_integration: string }>('/flashcards/health');
  }
}

// Export singleton instance
export const apiService = new ApiService();
