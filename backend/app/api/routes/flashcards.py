# Flashcard API routes
from fastapi import APIRouter, HTTPException
import logging

from ...models.flashcard import FlashcardRequest, FlashcardResponse
from ...services.flashcard_service import flashcard_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flashcards", tags=["flashcards"])

@router.post("/generate", response_model=FlashcardResponse)
async def generate_flashcards(request: FlashcardRequest):
    """
    Generate flashcards from an uploaded document
    """
    try:
        if not request.file_id.strip():
            raise HTTPException(status_code=400, detail="File ID cannot be empty")
        
        logger.info(f"Generating flashcards for file: {request.filename}")
        
        response = await flashcard_service.generate_flashcards(request)
        
        logger.info(f"Generated {response.total_cards} flashcards in {response.processing_time:.2f}s")
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating flashcards: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for flashcard service
    """
    try:
        return {
            "status": "healthy",
            "service": "flashcard-generation",
            "llm_integration": "enabled" if flashcard_service.use_llm else "disabled"
        }
        
    except Exception as e:
        logger.error(f"Flashcard service health check failed: {str(e)}")
        return {
            "status": "error",
            "service": "flashcard-generation",
            "error": str(e)
        }
