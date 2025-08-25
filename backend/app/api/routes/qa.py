# Question-Answer API routes
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging

from ...models.qa import (
    QARequest, QAResponse, QASessionCreate, QASessionResponse,
    QAMessage, QASession
)
from ...services.qa_service import qa_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qa", tags=["qa"])

@router.post("/ask", response_model=QAResponse)
async def ask_question(request: QARequest):
    """
    Ask a question about an uploaded document using RAG
    """
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        logger.info(f"Processing question: {request.question[:100]}...")
        
        response = await qa_service.ask_question(request)
        
        logger.info(f"Generated answer for session {response.session_id}")
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/sessions", response_model=QASessionResponse)
async def create_session(session_data: QASessionCreate):
    """
    Create a new QA session for a document
    """
    try:
        logger.info(f"Creating QA session for file: {session_data.filename}")
        
        session = await qa_service.create_session(session_data)
        
        logger.info(f"Created QA session {session.session_id}")
        return session
        
    except Exception as e:
        logger.error(f"Error creating QA session: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sessions/{session_id}", response_model=QASession)
async def get_session(session_id: str):
    """
    Get a specific QA session with all messages
    """
    try:
        session = await qa_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sessions/{session_id}/messages", response_model=List[QAMessage])
async def get_session_messages(session_id: str):
    """
    Get all messages for a specific QA session
    """
    try:
        messages = await qa_service.get_session_messages(session_id)
        if not messages:
            raise HTTPException(status_code=404, detail="Session not found or no messages")
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sessions", response_model=List[QASessionResponse])
async def get_all_sessions():
    """
    Get all active QA sessions
    """
    try:
        sessions = await qa_service.get_all_sessions()
        return sessions
        
    except Exception as e:
        logger.error(f"Error getting all sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a QA session
    """
    try:
        success = await qa_service.delete_session(session_id)
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
    Health check endpoint for QA service
    """
    try:
        # Check if QA service is working
        active_sessions_count = len(qa_service.active_sessions)
        
        return {
            "status": "healthy",
            "service": "qa-with-rag",
            "active_sessions": active_sessions_count,
            "rag_integration": "enabled"
        }
        
    except Exception as e:
        logger.error(f"QA service health check failed: {str(e)}")
        return {
            "status": "error",
            "service": "qa-with-rag",
            "error": str(e)
        }
