# Flashcard service for generating flashcards from documents
from typing import Dict, Any, List
import logging
import uuid
from datetime import datetime

from ..models.flashcard import (
    Flashcard, FlashcardRequest, FlashcardResponse, DifficultyLevel
)
from .document import DocumentService
from .llm_service import llm_service

logger = logging.getLogger(__name__)

class FlashcardService:
    """Service for generating flashcards from documents"""
    
    def __init__(self, document_service: DocumentService = None, use_llm: bool = True):
        self.document_service = document_service or DocumentService()
        self.use_llm = use_llm
        
        logger.info(f"Initialized Flashcard Service with LLM integration (LLM: {'enabled' if use_llm else 'disabled'})")
    
    async def generate_flashcards(self, request: FlashcardRequest) -> FlashcardResponse:
        """Generate flashcards from a document"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Generating flashcards for file: {request.filename}")
            
            # Get document content using document service
            document_content = await self._get_document_content(request.file_id)
            
            # Generate flashcards using LLM
            flashcards_data = await self._generate_flashcards_from_content(
                document_content
            )
            
            # Convert to Flashcard objects
            flashcards = []
            for card_data in flashcards_data:
                flashcard = Flashcard(
                    id=card_data["id"],
                    front=card_data["front"],
                    back=card_data["back"],
                    difficulty=DifficultyLevel(card_data["difficulty"]),
                    category=card_data.get("category")
                )
                flashcards.append(flashcard)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Generated {len(flashcards)} flashcards in {processing_time:.2f}s")
            
            return FlashcardResponse(
                flashcards=flashcards,
                file_id=request.file_id,
                filename=request.filename,
                total_cards=len(flashcards),
                processing_time=processing_time,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating flashcards: {str(e)}")
            raise
    
    async def _get_document_content(self, file_id: str) -> str:
        """Get document content using document service"""
        try:
            # First try to get the full extracted text
            full_text = await self.document_service.get_extracted_text(file_id)
            
            if full_text and full_text.strip():
                logger.info(f"Retrieved full text content for file {file_id} ({len(full_text)} characters)")
                return full_text
            
            # Fallback: try to get chunks
            chunks = await self.document_service.get_document_chunks(file_id)
            
            if chunks:
                # Combine chunks into content
                content = "\n\n".join([chunk["content"] for chunk in chunks])
                
                if content.strip():
                    logger.info(f"Retrieved chunked content for file {file_id} ({len(content)} characters)")
                    return content
            
            # If still no content, try to get file info
            file_info = await self.document_service.get_file_info(file_id)
            if file_info and file_info.content_summary:
                full_text = file_info.content_summary.get('full_text', '')
                if full_text and full_text.strip():
                    logger.info(f"Retrieved content from file info for file {file_id} ({len(full_text)} characters)")
                    return full_text
            
            raise ValueError(f"No content found in document {file_id}")
            
        except Exception as e:
            logger.error(f"Error getting document content for {file_id}: {str(e)}")
            raise
    
    async def _generate_flashcards_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Generate flashcards using LLM"""
        try:
            if not self.use_llm:
                raise ValueError("LLM service not available")
            
            # Generate flashcards using LLM
            flashcards_data = await llm_service.generate_flashcards(content)
            
            return flashcards_data
            
        except Exception as e:
            logger.error(f"Error generating flashcards from content: {str(e)}")
            raise

# Global flashcard service instance
flashcard_service = FlashcardService()
