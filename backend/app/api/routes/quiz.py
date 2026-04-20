# Quiz API routes
import logging
from typing import List

from fastapi import APIRouter, HTTPException

from ...models.quiz import (
    QuizQuestionResponse,
    QuizRequest,
    QuizResponse,
    QuizResult,
    QuizSessionCreate,
    QuizSessionResponse,
    QuizSubmission,
)
from ...services.quiz_service import quiz_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    try:
        if not request.file_id.strip():
            raise HTTPException(status_code=400, detail="File ID cannot be empty")
        return await quiz_service.generate_quiz(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error generating quiz: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sessions", response_model=QuizSessionResponse)
async def create_session(session_data: QuizSessionCreate):
    try:
        return await quiz_service.create_session(session_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error creating quiz session: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{quiz_id}/questions", response_model=List[QuizQuestionResponse])
async def get_quiz_questions(quiz_id: str):
    try:
        questions = await quiz_service.get_quiz_questions(quiz_id)
        if not questions:
            raise HTTPException(status_code=404, detail="Quiz not found or no questions")
        return questions
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error getting quiz questions for %s: %s", quiz_id, exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/submit", response_model=QuizResult)
async def submit_quiz(submission: QuizSubmission):
    try:
        if not submission.answers:
            raise HTTPException(status_code=400, detail="No answers provided")
        return await quiz_service.submit_quiz(submission)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error submitting quiz: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}", response_model=QuizSessionResponse)
async def get_session(session_id: str):
    try:
        session = await quiz_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return QuizSessionResponse(
            session_id=session.session_id,
            quiz_id=session.quiz_id,
            file_id=session.file_id,
            filename=session.filename,
            started_at=session.started_at,
            is_completed=session.is_completed,
            score=session.score,
            time_taken=session.time_taken,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error getting session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions", response_model=List[QuizSessionResponse])
async def get_all_sessions():
    try:
        return await quiz_service.get_all_sessions()
    except Exception as exc:
        logger.error("Error getting all quiz sessions: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    try:
        success = await quiz_service.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted successfully", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    try:
        return {
            "status": "healthy",
            "service": "quiz-generation",
            "active_quizzes": len(quiz_service.active_quizzes),
            "active_sessions": len(quiz_service.active_sessions),
            "llm_integration": "enabled" if quiz_service.use_llm else "disabled",
        }
    except Exception as exc:
        logger.error("Quiz service health check failed: %s", exc)
        return {"status": "error", "service": "quiz-generation", "error": str(exc)}
