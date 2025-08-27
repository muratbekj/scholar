# QA model for storing question-answer session logs
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime

class QAMessage(BaseModel):
    """Model for individual QA messages"""
    id: str
    type: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class QASession(BaseModel):
    """Model for QA session"""
    session_id: str
    file_id: str
    filename: str
    created_at: datetime
    messages: List[QAMessage] = []
    total_messages: int = 0
    session_duration: Optional[float] = None  # in seconds

class QARequest(BaseModel):
    """Model for QA request"""
    question: str
    file_id: Optional[str] = None
    session_id: Optional[str] = None
    filename: Optional[str] = None  # Add filename to avoid file lookup
    use_rag: bool = True
    search_k: int = 5

class QAResponse(BaseModel):
    """Model for QA response"""
    answer: str
    session_id: str
    message_id: str
    timestamp: datetime
    rag_context: Optional[Dict[str, Any]] = None
    processing_time: float
    confidence_score: Optional[float] = None

class RAGContext(BaseModel):
    """Model for RAG context information"""
    relevant_chunks: List[Dict[str, Any]]
    similarity_scores: List[float]
    source_file: str
    chunk_count: int
    search_query: str

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
