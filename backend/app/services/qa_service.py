# QA service for handling question-answer sessions with RAG integration
from typing import Dict, Any, List, Optional
import logging
import uuid
from datetime import datetime
import asyncio

from ..models.qa import (
    QASession, QAMessage, QARequest, QAResponse, 
    QASessionCreate, QASessionResponse, RAGContext
)
from .rag_pipeline import rag_pipeline_service
from .document import DocumentService
from .llm_service import llm_service

logger = logging.getLogger(__name__)

class QAService:
    """Service for handling QA sessions with RAG integration"""
    
    def __init__(self, document_service: DocumentService = None, use_llm: bool = True):
        self.document_service = document_service or DocumentService()
        self.active_sessions: Dict[str, QASession] = {}
        self.use_llm = use_llm
        
        logger.info(f"Initialized QA Service with RAG integration (LLM: {'enabled' if use_llm else 'disabled'})")
    
    async def create_session(self, session_data: QASessionCreate) -> QASessionResponse:
        """Create a new QA session"""
        try:
            session_id = str(uuid.uuid4())
            
            session = QASession(
                session_id=session_id,
                file_id=session_data.file_id,
                filename=session_data.filename,
                created_at=datetime.now(),
                messages=[],
                total_messages=0
            )
            
            # Store session
            self.active_sessions[session_id] = session
            
            logger.info(f"Created QA session {session_id} for file {session_data.filename}")
            
            return QASessionResponse(
                session_id=session_id,
                file_id=session_data.file_id,
                filename=session_data.filename,
                created_at=session.created_at,
                message_count=0,
                last_activity=None
            )
            
        except Exception as e:
            logger.error(f"Error creating QA session: {str(e)}")
            raise
    
    async def ask_question(self, request: QARequest) -> QAResponse:
        """Ask a question and get an answer using RAG"""
        start_time = datetime.now()
        
        try:
            # Get or create session
            session = await self._get_or_create_session(request)
            
            # Add user message to session
            user_message = QAMessage(
                id=str(uuid.uuid4()),
                type="user",
                content=request.question,
                timestamp=datetime.now()
            )
            session.messages.append(user_message)
            session.total_messages += 1
            
            # Generate answer using RAG
            answer, rag_context = await self._generate_rag_answer(
                request.question, 
                session.file_id, 
                request.use_rag,
                request.search_k
            )
            
            # Add assistant message to session
            assistant_message = QAMessage(
                id=str(uuid.uuid4()),
                type="assistant",
                content=answer,
                timestamp=datetime.now(),
                metadata={"rag_context": rag_context} if rag_context else None
            )
            session.messages.append(assistant_message)
            session.total_messages += 1
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update session duration
            session.session_duration = (datetime.now() - session.created_at).total_seconds()
            
            logger.info(f"Generated answer for session {session.session_id} in {processing_time:.2f}s")
            
            return QAResponse(
                answer=answer,
                session_id=session.session_id,
                message_id=assistant_message.id,
                timestamp=assistant_message.timestamp,
                rag_context=rag_context,
                processing_time=processing_time,
                confidence_score=self._calculate_confidence_score(rag_context) if rag_context else None
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Error generating answer: {str(e)}"
            logger.error(error_msg)
            
            # Return error response
            return QAResponse(
                answer=f"I'm sorry, I encountered an error while processing your question: {str(e)}",
                session_id=request.session_id or "error",
                message_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                rag_context=None,
                processing_time=processing_time,
                confidence_score=0.0
            )
    
    async def _get_or_create_session(self, request: QARequest) -> QASession:
        """Get existing session or create new one"""
        if request.session_id and request.session_id in self.active_sessions:
            return self.active_sessions[request.session_id]
        
        if not request.file_id:
            raise ValueError("File ID is required for new sessions")
        
        # Create new session directly without file info lookup
        # The filename should be provided in the request or we can use a default
        filename = getattr(request, 'filename', f"file_{request.file_id}")
        
        session_data = QASessionCreate(
            file_id=request.file_id,
            filename=filename
        )
        
        session_response = await self.create_session(session_data)
        return self.active_sessions[session_response.session_id]
    
    async def _generate_rag_answer(self, 
                                 question: str, 
                                 file_id: str, 
                                 use_rag: bool = True,
                                 search_k: int = 5) -> tuple[str, Optional[Dict[str, Any]]]:
        """Generate answer using RAG pipeline"""
        try:
            if not use_rag:
                # Fallback to generic response
                return self._generate_generic_answer(question), None
            
            # Search for relevant content using RAG
            search_result = await rag_pipeline_service.search_documents(
                query=question,
                k=search_k,
                file_id=file_id
            )
            
            if not search_result['success'] or not search_result['results']:
                return self._generate_generic_answer(question), None
            
            # Extract relevant context
            relevant_chunks = []
            similarity_scores = []
            
            for result in search_result['results']:
                relevant_chunks.append({
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'id': result['id']
                })
                similarity_scores.append(result.get('similarity_score', 0.0))
            
            # Generate answer based on context
            answer = await self._generate_contextual_answer(question, relevant_chunks, similarity_scores)
            
            # Prepare RAG context
            rag_context = {
                'relevant_chunks': relevant_chunks,
                'similarity_scores': similarity_scores,
                'source_file': file_id,
                'chunk_count': len(relevant_chunks),
                'search_query': question,
                'search_results_count': len(search_result['results'])
            }
            
            return answer, rag_context
            
        except Exception as e:
            logger.error(f"Error in RAG answer generation: {str(e)}")
            return self._generate_generic_answer(question), None
    
    async def _generate_contextual_answer(self, question: str, relevant_chunks: List[Dict[str, Any]], similarity_scores: List[float]) -> str:
        """Generate answer based on relevant document chunks using LLM"""
        try:
            # Combine relevant chunks into context
            context = "\n\n".join([chunk['content'] for chunk in relevant_chunks])
            
            if not context:
                return "I couldn't find specific information in the document that directly answers your question."
            
            # Generate answer using LLM or template
            if self.use_llm:
                answer = await llm_service.generate_answer(question, context)
            else:
                # Fallback to template-based answer
                answer_parts = []
                answer_parts.append(f"Based on the document content, here's what I found regarding your question: \"{question}\"")
                answer_parts.append("\n\nRelevant information from the document:")
                
                for i, chunk in enumerate(relevant_chunks[:3], 1):
                    excerpt = chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk['content']
                    answer_parts.append(f"\n{i}. {excerpt}")
                
                answer_parts.append(f"\n\nThis information is drawn from {len(relevant_chunks)} relevant sections of your document.")
                answer = " ".join(answer_parts)
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating contextual answer: {str(e)}")
            return self._generate_generic_answer(question)
    
    def _generate_generic_answer(self, question: str) -> str:
        """Generate a generic answer when RAG is not available"""
        return f"I understand you're asking about \"{question}\". However, I don't have access to the specific document content needed to provide a detailed answer. Please make sure the document has been properly uploaded and processed."
    
    def _calculate_confidence_score(self, rag_context: Optional[Dict[str, Any]]) -> Optional[float]:
        """Calculate confidence score based on RAG context"""
        if not rag_context or not rag_context.get('similarity_scores'):
            return None
        
        scores = rag_context['similarity_scores']
        if not scores:
            return 0.0
        
        # Calculate average similarity score as confidence
        avg_score = sum(scores) / len(scores)
        
        # Normalize to 0-1 range
        return min(max(avg_score, 0.0), 1.0)
    
    async def get_session(self, session_id: str) -> Optional[QASession]:
        """Get QA session by ID"""
        return self.active_sessions.get(session_id)
    
    async def get_session_messages(self, session_id: str) -> List[QAMessage]:
        """Get all messages for a session"""
        session = await self.get_session(session_id)
        if not session:
            return []
        return session.messages
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a QA session"""
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.info(f"Deleted QA session {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    async def get_all_sessions(self) -> List[QASessionResponse]:
        """Get all active sessions"""
        sessions = []
        for session in self.active_sessions.values():
            last_activity = session.messages[-1].timestamp if session.messages else None
            sessions.append(QASessionResponse(
                session_id=session.session_id,
                file_id=session.file_id,
                filename=session.filename,
                created_at=session.created_at,
                message_count=session.total_messages,
                last_activity=last_activity
            ))
        return sessions

# Initialize global QA service
qa_service = QAService()
