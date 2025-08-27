# Quiz API routes
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging

from ...models.quiz import (
    QuizRequest, QuizResponse, QuizSessionCreate, QuizSessionResponse,
    QuizSubmission, QuizResult, QuizQuestionResponse
)
from ...services.quiz_service import quiz_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quiz", tags=["quiz"])

@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """
    Generate a quiz from an uploaded document
    """
    try:
        if not request.file_id.strip():
            raise HTTPException(status_code=400, detail="File ID cannot be empty")
        
        logger.info(f"Generating quiz for file: {request.filename} with {request.num_questions} questions")
        
        response = await quiz_service.generate_quiz(request)
        
        logger.info(f"Generated quiz {response.quiz_id} in {response.processing_time:.2f}s")
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/sessions", response_model=QuizSessionResponse)
async def create_session(session_data: QuizSessionCreate):
    """
    Create a new quiz session
    """
    try:
        logger.info(f"Creating quiz session for quiz: {session_data.quiz_id}")
        
        session = await quiz_service.create_session(session_data)
        
        logger.info(f"Created quiz session {session.session_id}")
        return session
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating quiz session: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{quiz_id}/questions", response_model=List[QuizQuestionResponse])
async def get_quiz_questions(quiz_id: str):
    """
    Get quiz questions without correct answers (for user display)
    """
    try:
        questions = await quiz_service.get_quiz_questions(quiz_id)
        if not questions:
            raise HTTPException(status_code=404, detail="Quiz not found or no questions")
        
        return questions
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quiz questions for {quiz_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/submit", response_model=QuizResult)
async def submit_quiz(submission: QuizSubmission):
    """
    Submit quiz answers and get results
    """
    try:
        if not submission.answers:
            raise HTTPException(status_code=400, detail="No answers provided")
        
        logger.info(f"Submitting quiz for session: {submission.session_id}")
        
        result = await quiz_service.submit_quiz(submission)
        
        logger.info(f"Quiz submitted for session {submission.session_id}, score: {result.score:.1f}%")
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting quiz: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get a specific quiz session
    """
    try:
        session = await quiz_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sessions", response_model=List[QuizSessionResponse])
async def get_all_sessions():
    """
    Get all active quiz sessions
    """
    try:
        sessions = await quiz_service.get_all_sessions()
        return sessions
        
    except Exception as e:
        logger.error(f"Error getting all sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a quiz session
    """
    try:
        success = await quiz_service.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session deleted successfully", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for quiz service
    """
    try:
        # Check if quiz service is working
        active_quizzes_count = len(quiz_service.active_quizzes)
        active_sessions_count = len(quiz_service.active_sessions)
        
        return {
            "status": "healthy",
            "service": "quiz-generation",
            "active_quizzes": active_quizzes_count,
            "active_sessions": active_sessions_count,
            "llm_integration": "enabled" if quiz_service.use_llm else "disabled"
        }
        
    except Exception as e:
        logger.error(f"Quiz service health check failed: {str(e)}")
        return {
            "status": "error",
            "service": "quiz-generation",
            "error": str(e)
        }
