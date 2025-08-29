# Flashcard model for storing generated flashcards
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class DifficultyLevel(str, Enum):
    """Flashcard difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Flashcard(BaseModel):
    """Model for individual flashcard"""
    id: str
    front: str  # Question/prompt
    back: str   # Answer/explanation
    difficulty: DifficultyLevel
    category: Optional[str] = None  # Optional topic categorization

class FlashcardRequest(BaseModel):
    """Model for flashcard generation request"""
    file_id: str
    filename: str

class FlashcardResponse(BaseModel):
    """Model for flashcard generation response"""
    flashcards: List[Flashcard]
    file_id: str
    filename: str
    total_cards: int
    processing_time: float
    created_at: datetime
