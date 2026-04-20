# QA model for storing question-answer session logs
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .study import (
    AuditSummary,
    AnswerSegment,
    EvidenceRef,
    GapStep,
    QAGenerationMode,
    QAResponseState,
    ReflectionState,
)


class QAMessage(BaseModel):
    """Model for individual QA messages"""

    id: str
    type: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class RAGContext(BaseModel):
    """Model for RAG context information"""

    relevant_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    similarity_scores: List[float] = Field(default_factory=list)
    source_file: str
    chunk_count: int
    search_query: str
    search_results_count: int = 0


class PendingQAExchange(BaseModel):
    """State for a gated Q&A exchange waiting for reflection."""

    pending_question_id: str
    question: str
    created_at: datetime
    complexity_score: int
    reflection_prompt: str
    visible_cue: Optional[str] = None
    hidden_evidence_count: int = 0
    visible_evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    rag_context: Optional[RAGContext] = None
    generation_mode: QAGenerationMode = QAGenerationMode.STANDARD


class QASession(BaseModel):
    """Model for QA session"""

    session_id: str
    file_id: str
    filename: str
    created_at: datetime
    messages: List[QAMessage] = Field(default_factory=list)
    total_messages: int = 0
    session_duration: Optional[float] = None
    pending_questions: Dict[str, PendingQAExchange] = Field(default_factory=dict)


class QARequest(BaseModel):
    """Model for QA request"""

    question: str
    file_id: Optional[str] = None
    session_id: Optional[str] = None
    filename: Optional[str] = None
    use_rag: bool = True
    search_k: int = 5
    generation_mode: QAGenerationMode = QAGenerationMode.STANDARD


class QAReflectionSubmitRequest(BaseModel):
    """Model for submitting the reflection step of a gated answer."""

    session_id: str
    reflection: str
    pending_question_id: Optional[str] = None


class QAResponse(BaseModel):
    """Model for QA response"""

    answer: str
    session_id: str
    message_id: str
    timestamp: datetime
    rag_context: Optional[RAGContext] = None
    processing_time: float
    confidence_score: Optional[float] = None
    response_state: QAResponseState = QAResponseState.ANSWERED
    reflection_state: ReflectionState = ReflectionState.BYPASSED
    reflection_prompt: Optional[str] = None
    visible_cue: Optional[str] = None
    hidden_evidence_count: int = 0
    pending_question_id: Optional[str] = None
    answer_segments: List[AnswerSegment] = Field(default_factory=list)
    audit_summary: Optional[AuditSummary] = None
    visible_evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    complexity_score: Optional[int] = None
    recent_history_summary: Optional[str] = None
    generation_mode: QAGenerationMode = QAGenerationMode.STANDARD
    gap_steps: List[GapStep] = Field(default_factory=list)
    # Echoed from POST /qa/reflect for Human–Machine collaboration UI (intuition vs model answer).
    intuition_text: Optional[str] = None


class QASessionCreate(BaseModel):
    """Model for creating a new QA session"""

    file_id: str
    filename: str


class QASessionResponse(BaseModel):
    """Model for QA session response"""

    session_id: str
    file_id: str
    filename: str
    created_at: datetime
    message_count: int
    last_activity: Optional[datetime] = None
    pending_questions: int = 0
