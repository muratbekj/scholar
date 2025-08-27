# Quiz service for generating and managing quizzes from documents
from typing import Dict, Any, List, Optional, Tuple
import logging
import uuid
from datetime import datetime
import asyncio
import json

from ..models.quiz import (
    Quiz, QuizQuestion, QuizRequest, QuizResponse, QuizSession,
    QuizSubmission, QuizResult, QuizSessionCreate, QuizSessionResponse,
    QuizQuestionResponse, QuestionType, DifficultyLevel
)
from .rag_pipeline import rag_pipeline_service
from .document import DocumentService
from .llm_service import llm_service

logger = logging.getLogger(__name__)

class QuizService:
    """Service for generating and managing quizzes from documents"""
    
    def __init__(self, document_service: DocumentService = None, use_llm: bool = True):
        self.document_service = document_service or DocumentService()
        self.active_quizzes: Dict[str, Quiz] = {}
        self.active_sessions: Dict[str, QuizSession] = {}
        self.use_llm = use_llm
        
        logger.info(f"Initialized Quiz Service with LLM integration (LLM: {'enabled' if use_llm else 'disabled'})")
    
    async def generate_quiz(self, request: QuizRequest) -> QuizResponse:
        """Generate a quiz from a document"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Generating quiz for file: {request.filename} with {request.num_questions} questions")
            
            # Get document content using RAG pipeline
            document_content = await self._get_document_content(request.file_id)
            
            # Generate quiz questions using LLM
            questions = await self._generate_questions(
                document_content, 
                request.num_questions, 
                request.difficulty,
                request.question_types,
                request.include_explanations
            )
            
            # Create quiz
            quiz_id = str(uuid.uuid4())
            total_points = sum(q.points for q in questions)
            
            quiz = Quiz(
                quiz_id=quiz_id,
                title=f"Quiz on {request.filename}",
                description=f"Generated quiz with {request.num_questions} questions at {request.difficulty} difficulty",
                file_id=request.file_id,
                filename=request.filename,
                questions=questions,
                total_questions=len(questions),
                total_points=total_points,
                difficulty=request.difficulty,
                estimated_time=request.estimated_time or self._estimate_quiz_time(len(questions), request.difficulty),
                created_at=datetime.now()
            )
            
            # Store quiz
            self.active_quizzes[quiz_id] = quiz
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Generated quiz {quiz_id} with {len(questions)} questions in {processing_time:.2f}s")
            
            return QuizResponse(
                quiz_id=quiz_id,
                title=quiz.title,
                description=quiz.description,
                file_id=quiz.file_id,
                filename=quiz.filename,
                total_questions=quiz.total_questions,
                total_points=quiz.total_points,
                difficulty=quiz.difficulty,
                estimated_time=quiz.estimated_time,
                created_at=quiz.created_at,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error generating quiz: {str(e)}")
            raise
    
    async def create_session(self, session_data: QuizSessionCreate) -> QuizSessionResponse:
        """Create a new quiz session"""
        try:
            # Verify quiz exists
            if session_data.quiz_id not in self.active_quizzes:
                raise ValueError(f"Quiz {session_data.quiz_id} not found")
            
            session_id = str(uuid.uuid4())
            
            session = QuizSession(
                session_id=session_id,
                quiz_id=session_data.quiz_id,
                file_id=session_data.file_id,
                filename=session_data.filename,
                started_at=datetime.now(),
                answers={},
                is_completed=False
            )
            
            # Store session
            self.active_sessions[session_id] = session
            
            logger.info(f"Created quiz session {session_id} for quiz {session_data.quiz_id}")
            
            return QuizSessionResponse(
                session_id=session_id,
                quiz_id=session_data.quiz_id,
                file_id=session_data.file_id,
                filename=session_data.filename,
                started_at=session.started_at,
                is_completed=False,
                score=None,
                time_taken=None
            )
            
        except Exception as e:
            logger.error(f"Error creating quiz session: {str(e)}")
            raise
    
    async def get_quiz_questions(self, quiz_id: str) -> List[QuizQuestionResponse]:
        """Get quiz questions without correct answers (for user display)"""
        try:
            if quiz_id not in self.active_quizzes:
                raise ValueError(f"Quiz {quiz_id} not found")
            
            quiz = self.active_quizzes[quiz_id]
            
            # Convert to response format (without correct answers)
            questions = []
            for q in quiz.questions:
                questions.append(QuizQuestionResponse(
                    id=q.id,
                    question=q.question,
                    question_type=q.question_type,
                    options=q.options,
                    difficulty=q.difficulty,
                    points=q.points
                ))
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting quiz questions: {str(e)}")
            raise
    
    async def submit_quiz(self, submission: QuizSubmission) -> QuizResult:
        """Submit quiz answers and get results"""
        try:
            if submission.session_id not in self.active_sessions:
                raise ValueError(f"Session {submission.session_id} not found")
            
            session = self.active_sessions[submission.session_id]
            
            if session.is_completed:
                raise ValueError("Quiz session already completed")
            
            # Get quiz
            if session.quiz_id not in self.active_quizzes:
                raise ValueError(f"Quiz {session.quiz_id} not found")
            
            quiz = self.active_quizzes[session.quiz_id]
            
            # Calculate results
            results = await self._calculate_results(quiz, submission.answers)
            results.session_id = submission.session_id
            results.time_taken = (datetime.now() - session.started_at).total_seconds()
            
            # Update session
            session.answers = submission.answers
            session.completed_at = datetime.now()
            session.score = results.score
            session.total_points_earned = results.total_points_earned
            session.total_possible_points = results.total_possible_points
            session.time_taken = results.time_taken
            session.is_completed = True
            
            logger.info(f"Quiz session {submission.session_id} completed with score: {results.score:.1f}%")
            
            return results
            
        except Exception as e:
            logger.error(f"Error submitting quiz: {str(e)}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[QuizSession]:
        """Get a specific quiz session"""
        return self.active_sessions.get(session_id)
    
    async def get_all_sessions(self) -> List[QuizSessionResponse]:
        """Get all active quiz sessions"""
        sessions = []
        for session in self.active_sessions.values():
            sessions.append(QuizSessionResponse(
                session_id=session.session_id,
                quiz_id=session.quiz_id,
                file_id=session.file_id,
                filename=session.filename,
                started_at=session.started_at,
                is_completed=session.is_completed,
                score=session.score,
                time_taken=session.time_taken
            ))
        return sessions
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a quiz session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Deleted quiz session {session_id}")
            return True
        return False
    
    async def _get_document_content(self, file_id: str) -> str:
        """Get document content using RAG pipeline"""
        try:
            # Get document chunks from RAG pipeline
            chunks = await rag_pipeline_service.get_document_chunks(file_id)
            
            # Combine chunks into content
            content = "\n\n".join([chunk["content"] for chunk in chunks])
            
            if not content.strip():
                raise ValueError("No content found in document")
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting document content: {str(e)}")
            raise
    
    async def _generate_questions(self, 
                                content: str, 
                                num_questions: int, 
                                difficulty: DifficultyLevel,
                                question_types: Optional[List[QuestionType]] = None,
                                include_explanations: bool = True) -> List[QuizQuestion]:
        """Generate quiz questions using LLM"""
        try:
            if not self.use_llm:
                raise ValueError("LLM service not available")
            
            # Default question types if not specified
            if not question_types:
                question_types = [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]
            
            # Generate questions using LLM
            questions_data = await llm_service.generate_quiz_questions(
                content, num_questions, difficulty, question_types, include_explanations
            )
            
            # Convert to QuizQuestion objects
            questions = []
            for i, q_data in enumerate(questions_data):
                question = QuizQuestion(
                    id=str(uuid.uuid4()),
                    question=q_data["question"],
                    question_type=q_data["type"],
                    options=q_data.get("options"),
                    correct_answer=q_data["correct_answer"],
                    explanation=q_data.get("explanation") if include_explanations else None,
                    difficulty=difficulty,
                    points=1
                )
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            raise
    
    async def _calculate_results(self, quiz: Quiz, answers: Dict[str, str]) -> QuizResult:
        """Calculate quiz results"""
        try:
            total_points_earned = 0
            correct_answers = 0
            question_results = []
            
            for question in quiz.questions:
                user_answer = answers.get(question.id, "")
                is_correct = self._check_answer(question, user_answer)
                
                if is_correct:
                    total_points_earned += question.points
                    correct_answers += 1
                
                question_results.append({
                    "question_id": question.id,
                    "question": question.question,
                    "user_answer": user_answer,
                    "correct_answer": question.correct_answer,
                    "is_correct": is_correct,
                    "points_earned": question.points if is_correct else 0,
                    "explanation": question.explanation
                })
            
            # Calculate score
            score = (total_points_earned / quiz.total_points) * 100 if quiz.total_points > 0 else 0
            
            # Generate feedback
            feedback = self._generate_feedback(score, correct_answers, quiz.total_questions)
            
            return QuizResult(
                session_id="",  # Will be set by caller
                quiz_id=quiz.quiz_id,
                score=score,
                total_points_earned=total_points_earned,
                total_possible_points=quiz.total_points,
                correct_answers=correct_answers,
                total_questions=quiz.total_questions,
                time_taken=0,  # Will be calculated by caller
                completed_at=datetime.now(),
                question_results=question_results,
                feedback=feedback
            )
            
        except Exception as e:
            logger.error(f"Error calculating results: {str(e)}")
            raise
    
    def _check_answer(self, question: QuizQuestion, user_answer: str) -> bool:
        """Check if user answer is correct"""
        if not user_answer.strip():
            return False
        
        # Normalize answers for comparison
        correct = question.correct_answer.lower().strip()
        user = user_answer.lower().strip()
        
        if question.question_type == QuestionType.TRUE_FALSE:
            # Handle true/false variations
            true_variants = ["true", "t", "yes", "y", "1"]
            false_variants = ["false", "f", "no", "n", "0"]
            
            if correct in true_variants and user in true_variants:
                return True
            elif correct in false_variants and user in false_variants:
                return True
            return False
        
        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            # For multiple choice, check if user selected the correct option
            return user == correct
        
        else:  # SHORT_ANSWER
            # For short answer, use fuzzy matching
            return user == correct or correct in user or user in correct
    
    def _generate_feedback(self, score: float, correct_answers: int, total_questions: int) -> str:
        """Generate feedback based on quiz performance"""
        if score >= 90:
            return f"Excellent! You got {correct_answers}/{total_questions} questions correct. Great job!"
        elif score >= 80:
            return f"Good work! You got {correct_answers}/{total_questions} questions correct. Keep it up!"
        elif score >= 70:
            return f"Not bad! You got {correct_answers}/{total_questions} questions correct. Review the material for better understanding."
        elif score >= 60:
            return f"You got {correct_answers}/{total_questions} questions correct. Consider reviewing the material more thoroughly."
        else:
            return f"You got {correct_answers}/{total_questions} questions correct. This material needs more study time."
    
    def _estimate_quiz_time(self, num_questions: int, difficulty: DifficultyLevel) -> int:
        """Estimate quiz completion time in minutes"""
        base_time_per_question = {
            DifficultyLevel.EASY: 1,
            DifficultyLevel.MEDIUM: 2,
            DifficultyLevel.HARD: 3
        }
        
        return num_questions * base_time_per_question[difficulty]

# Global quiz service instance
quiz_service = QuizService()
