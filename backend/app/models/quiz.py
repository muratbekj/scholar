# Quiz model for storing quiz questions and answers
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .study import EvidenceRef, GapStep, QuizMode


class QuestionType(str, Enum):
    """Types of quiz questions"""

    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class DifficultyLevel(str, Enum):
    """Quiz difficulty levels"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuizQuestion(BaseModel):
    """Model for individual quiz questions"""

    id: str
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    points: int = 1
    mode: QuizMode = QuizMode.STANDARD
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    prior_ai_answer: Optional[str] = None
    review_guidance: Optional[str] = None
    gap_prompt: Optional[str] = None
    accepted_reasoning: List[str] = Field(default_factory=list)
    gap_steps: List[GapStep] = Field(default_factory=list)
    grading_rubric: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class Quiz(BaseModel):
    """Model for a complete quiz"""

    quiz_id: str
    title: str
    description: Optional[str] = None
    file_id: str
    filename: str
    questions: List[QuizQuestion]
    total_questions: int
    total_points: int
    difficulty: DifficultyLevel
    mode: QuizMode = QuizMode.STANDARD
    estimated_time: Optional[int] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class QuizRequest(BaseModel):
    """Model for quiz generation request"""

    file_id: str
    filename: str
    num_questions: int = Field(ge=1, le=50, default=10)
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    question_types: Optional[List[QuestionType]] = None
    include_explanations: bool = True
    estimated_time: Optional[int] = None
    mode: QuizMode = QuizMode.STANDARD


class QuizResponse(BaseModel):
    """Model for quiz generation response"""

    quiz_id: str
    title: str
    description: Optional[str] = None
    file_id: str
    filename: str
    total_questions: int
    total_points: int
    difficulty: DifficultyLevel
    mode: QuizMode = QuizMode.STANDARD
    estimated_time: Optional[int] = None
    created_at: datetime
    processing_time: float


class QuizSession(BaseModel):
    """Model for user's quiz-taking session"""

    session_id: str
    quiz_id: str
    file_id: str
    filename: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    answers: Dict[str, str] = Field(default_factory=dict)
    score: Optional[float] = None
    total_points_earned: Optional[int] = None
    total_possible_points: Optional[int] = None
    time_taken: Optional[float] = None
    is_completed: bool = False


class QuizSubmission(BaseModel):
    """Model for quiz answer submission"""

    session_id: str
    answers: Dict[str, str]


class QuizResult(BaseModel):
    """Model for quiz results"""

    session_id: str
    quiz_id: str
    score: float
    total_points_earned: int
    total_possible_points: int
    correct_answers: int
    total_questions: int
    time_taken: float
    completed_at: datetime
    question_results: List[Dict[str, Any]]
    feedback: Optional[str] = None


class QuizSessionCreate(BaseModel):
    """Model for creating a new quiz session"""

    quiz_id: str
    file_id: str
    filename: str


class QuizSessionResponse(BaseModel):
    """Model for quiz session response"""

    session_id: str
    quiz_id: str
    file_id: str
    filename: str
    started_at: datetime
    is_completed: bool
    score: Optional[float] = None
    time_taken: Optional[float] = None


class QuizQuestionResponse(BaseModel):
    """Model for quiz question without correct answer (for user display)"""

    id: str
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    difficulty: DifficultyLevel
    points: int
    mode: QuizMode = QuizMode.STANDARD
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    prior_ai_answer: Optional[str] = None
    review_guidance: Optional[str] = None
    gap_prompt: Optional[str] = None
    gap_steps: List[GapStep] = Field(default_factory=list)
    grading_rubric: List[str] = Field(default_factory=list)
