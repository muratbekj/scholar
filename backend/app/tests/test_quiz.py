# Test quiz functionality
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from app.models.quiz import (
    QuizRequest, QuizQuestion, QuestionType, DifficultyLevel,
    QuizSessionCreate, QuizSubmission
)
from app.services.quiz_service import QuizService
from app.services.llm_service import LLMService

@pytest.fixture
def mock_document_service():
    return Mock()

@pytest.fixture
def mock_llm_service():
    return Mock()

@pytest.fixture
def quiz_service(mock_document_service):
    return QuizService(document_service=mock_document_service, use_llm=False)

@pytest.fixture
def sample_quiz_request():
    return QuizRequest(
        file_id="test-file-123",
        filename="test_document.pdf",
        num_questions=5,
        difficulty=DifficultyLevel.MEDIUM,
        question_types=[QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]
    )

@pytest.fixture
def sample_questions():
    return [
        QuizQuestion(
            id="q1",
            question="What is the main topic?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="This is correct because...",
            difficulty=DifficultyLevel.MEDIUM,
            points=1
        ),
        QuizQuestion(
            id="q2",
            question="Is this statement true?",
            question_type=QuestionType.TRUE_FALSE,
            options=["True", "False"],
            correct_answer="True",
            explanation="This is true because...",
            difficulty=DifficultyLevel.MEDIUM,
            points=1
        )
    ]

class TestQuizService:
    
    @pytest.mark.asyncio
    async def test_create_session(self, quiz_service, sample_questions):
        """Test creating a quiz session"""
        # Create a mock quiz
        quiz_id = "test-quiz-123"
        quiz_service.active_quizzes[quiz_id] = Mock(
            quiz_id=quiz_id,
            questions=sample_questions,
            total_points=2
        )
        
        session_data = QuizSessionCreate(
            quiz_id=quiz_id,
            file_id="test-file-123",
            filename="test_document.pdf"
        )
        
        session = await quiz_service.create_session(session_data)
        
        assert session.session_id is not None
        assert session.quiz_id == quiz_id
        assert session.file_id == "test-file-123"
        assert session.is_completed == False
        assert session.score is None
    
    @pytest.mark.asyncio
    async def test_submit_quiz(self, quiz_service, sample_questions):
        """Test submitting quiz answers"""
        # Create a mock quiz
        quiz_id = "test-quiz-123"
        mock_quiz = Mock()
        mock_quiz.quiz_id = quiz_id
        mock_quiz.questions = sample_questions
        mock_quiz.total_points = 2
        mock_quiz.total_questions = 2
        quiz_service.active_quizzes[quiz_id] = mock_quiz
        
        # Create a session
        session_id = "test-session-123"
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.quiz_id = quiz_id
        mock_session.started_at = datetime.now()
        mock_session.is_completed = False
        quiz_service.active_sessions[session_id] = mock_session
        
        # Submit answers
        submission = QuizSubmission(
            session_id=session_id,
            answers={
                "q1": "A",  # Correct
                "q2": "False"  # Incorrect
            }
        )
        
        result = await quiz_service.submit_quiz(submission)
        
        assert result.session_id == session_id
        assert result.quiz_id == quiz_id
        assert result.score == 50.0  # 1 out of 2 correct
        assert result.correct_answers == 1
        assert result.total_questions == 2
        assert len(result.question_results) == 2
    
    def test_check_answer_multiple_choice(self, quiz_service, sample_questions):
        """Test multiple choice answer checking"""
        question = sample_questions[0]  # Multiple choice question
        
        # Test correct answer
        assert quiz_service._check_answer(question, "A") == True
        
        # Test incorrect answer
        assert quiz_service._check_answer(question, "B") == False
        
        # Test case insensitive
        assert quiz_service._check_answer(question, "a") == True
    
    def test_check_answer_true_false(self, quiz_service, sample_questions):
        """Test true/false answer checking"""
        question = sample_questions[1]  # True/false question
        
        # Test correct answer
        assert quiz_service._check_answer(question, "True") == True
        assert quiz_service._check_answer(question, "true") == True
        assert quiz_service._check_answer(question, "T") == True
        assert quiz_service._check_answer(question, "Yes") == True
        
        # Test incorrect answer
        assert quiz_service._check_answer(question, "False") == False
        assert quiz_service._check_answer(question, "No") == False
    
    def test_generate_feedback(self, quiz_service):
        """Test feedback generation"""
        # Test excellent score
        feedback = quiz_service._generate_feedback(95.0, 19, 20)
        assert "Excellent" in feedback
        
        # Test good score
        feedback = quiz_service._generate_feedback(85.0, 17, 20)
        assert "Good work" in feedback
        
        # Test poor score
        feedback = quiz_service._generate_feedback(45.0, 9, 20)
        assert "needs more study time" in feedback
    
    def test_estimate_quiz_time(self, quiz_service):
        """Test quiz time estimation"""
        # Test easy difficulty
        time = quiz_service._estimate_quiz_time(10, DifficultyLevel.EASY)
        assert time == 10  # 1 minute per question
        
        # Test medium difficulty
        time = quiz_service._estimate_quiz_time(10, DifficultyLevel.MEDIUM)
        assert time == 20  # 2 minutes per question
        
        # Test hard difficulty
        time = quiz_service._estimate_quiz_time(10, DifficultyLevel.HARD)
        assert time == 30  # 3 minutes per question

class TestQuizModels:
    
    def test_quiz_request_validation(self):
        """Test quiz request model validation"""
        # Valid request
        request = QuizRequest(
            file_id="test-file-123",
            filename="test.pdf",
            num_questions=10,
            difficulty=DifficultyLevel.MEDIUM
        )
        assert request.num_questions == 10
        assert request.difficulty == DifficultyLevel.MEDIUM
        
        # Test default values
        request = QuizRequest(
            file_id="test-file-123",
            filename="test.pdf"
        )
        assert request.num_questions == 10  # Default value
        assert request.difficulty == DifficultyLevel.MEDIUM  # Default value
    
    def test_question_types_enum(self):
        """Test question type enum values"""
        assert QuestionType.MULTIPLE_CHOICE == "multiple_choice"
        assert QuestionType.TRUE_FALSE == "true_false"
        assert QuestionType.SHORT_ANSWER == "short_answer"
    
    def test_difficulty_levels_enum(self):
        """Test difficulty level enum values"""
        assert DifficultyLevel.EASY == "easy"
        assert DifficultyLevel.MEDIUM == "medium"
        assert DifficultyLevel.HARD == "hard"
