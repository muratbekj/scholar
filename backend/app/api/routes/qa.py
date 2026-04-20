# Question-Answer API routes
import logging
from typing import List

from fastapi import APIRouter, HTTPException

from ...models.qa import (
    QAMessage,
    QAReflectionSubmitRequest,
    QARequest,
    QAResponse,
    QASession,
    QASessionCreate,
    QASessionResponse,
)
from ...services.qa_service import qa_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=QAResponse)
async def ask_question(request: QARequest):
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        return await qa_service.ask_question(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error processing question: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reflect", response_model=QAResponse)
async def submit_reflection(request: QAReflectionSubmitRequest):
    try:
        if not request.reflection.strip():
            raise HTTPException(status_code=400, detail="Reflection cannot be empty")
        return await qa_service.submit_reflection(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error submitting reflection: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sessions", response_model=QASessionResponse)
async def create_session(session_data: QASessionCreate):
    try:
        return await qa_service.create_session(session_data)
    except Exception as exc:
        logger.error("Error creating QA session: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}", response_model=QASession)
async def get_session(session_id: str):
    try:
        session = await qa_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error getting session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}/messages", response_model=List[QAMessage])
async def get_session_messages(session_id: str):
    try:
        messages = await qa_service.get_session_messages(session_id)
        if not messages:
            raise HTTPException(status_code=404, detail="Session not found or no messages")
        return messages
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error getting messages for session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions", response_model=List[QASessionResponse])
async def get_all_sessions():
    try:
        return await qa_service.get_all_sessions()
    except Exception as exc:
        logger.error("Error getting all sessions: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    try:
        success = await qa_service.delete_session(session_id)
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
            "service": "qa-with-rag",
            "active_sessions": len(qa_service.active_sessions),
            "rag_integration": "enabled",
        }
    except Exception as exc:
        logger.error("QA service health check failed: %s", exc)
        return {"status": "error", "service": "qa-with-rag", "error": str(exc)}
