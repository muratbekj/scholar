import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.models.flashcard import Flashcard, FlashcardRequest, FlashcardResponse, DifficultyLevel
from app.services.flashcard_service import FlashcardService
from app.services.llm_service import LLMService


class TestFlashcardModels:
    """Test flashcard model validation"""
    
    def test_flashcard_model(self):
        """Test flashcard model creation and validation"""
        flashcard = Flashcard(
            id="test_1",
            front="What is AI?",
            back="Artificial Intelligence is a branch of computer science.",
            difficulty=DifficultyLevel.EASY,
            category="Definitions"
        )
        
        assert flashcard.id == "test_1"
        assert flashcard.front == "What is AI?"
        assert flashcard.back == "Artificial Intelligence is a branch of computer science."
        assert flashcard.difficulty == DifficultyLevel.EASY
        assert flashcard.category == "Definitions"
    
    def test_flashcard_request_model(self):
        """Test flashcard request model"""
        request = FlashcardRequest(
            file_id="test_file_123",
            filename="test_document.pdf"
        )
        
        assert request.file_id == "test_file_123"
        assert request.filename == "test_document.pdf"
    
    def test_flashcard_response_model(self):
        """Test flashcard response model"""
        flashcards = [
            Flashcard(
                id="test_1",
                front="What is AI?",
                back="Artificial Intelligence is a branch of computer science.",
                difficulty=DifficultyLevel.EASY,
                category="Definitions"
            )
        ]
        
        response = FlashcardResponse(
            flashcards=flashcards,
            file_id="test_file_123",
            filename="test_document.pdf",
            total_cards=1,
            processing_time=2.5,
            created_at=datetime.now()
        )
        
        assert response.flashcards == flashcards
        assert response.file_id == "test_file_123"
        assert response.filename == "test_document.pdf"
        assert response.total_cards == 1
        assert response.processing_time == 2.5


class TestFlashcardService:
    """Test flashcard service functionality"""
    
    @pytest.fixture
    def mock_document_service(self):
        """Mock document service"""
        mock_service = Mock()
        mock_service.get_extracted_text = AsyncMock(return_value="This is test content about artificial intelligence.")
        mock_service.get_document_chunks = AsyncMock(return_value=None)
        mock_service.get_file_info = AsyncMock(return_value=None)
        return mock_service
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service"""
        mock_service = Mock()
        mock_service.generate_flashcards = AsyncMock(return_value=[
            {
                "id": "flashcard_1",
                "front": "What is artificial intelligence?",
                "back": "Artificial intelligence (AI) is a branch of computer science.",
                "difficulty": "easy",
                "category": "Definitions"
            },
            {
                "id": "flashcard_2",
                "front": "What are the main applications of AI?",
                "back": "AI is used in machine learning, natural language processing, and robotics.",
                "difficulty": "medium",
                "category": "Applications"
            }
        ])
        return mock_service
    
    @pytest.mark.asyncio
    async def test_generate_flashcards_success(self, mock_document_service, mock_llm_service):
        """Test successful flashcard generation"""
        with patch('app.services.flashcard_service.llm_service', mock_llm_service):
            service = FlashcardService(document_service=mock_document_service)
            
            request = FlashcardRequest(
                file_id="test_file_123",
                filename="test_document.pdf"
            )
            
            response = await service.generate_flashcards(request)
            
            assert response.file_id == "test_file_123"
            assert response.filename == "test_document.pdf"
            assert response.total_cards == 2
            assert len(response.flashcards) == 2
            assert response.flashcards[0].front == "What is artificial intelligence?"
            assert response.flashcards[0].back == "Artificial intelligence (AI) is a branch of computer science."
            assert response.flashcards[0].difficulty == DifficultyLevel.EASY
            assert response.flashcards[0].category == "Definitions"
    
    @pytest.mark.asyncio
    async def test_generate_flashcards_no_content(self, mock_document_service, mock_llm_service):
        """Test flashcard generation with no document content"""
        mock_document_service.get_extracted_text = AsyncMock(return_value="")
        mock_document_service.get_document_chunks = AsyncMock(return_value=[])
        mock_document_service.get_file_info = AsyncMock(return_value=None)
        
        service = FlashcardService(document_service=mock_document_service)
        
        request = FlashcardRequest(
            file_id="test_file_123",
            filename="test_document.pdf"
        )
        
        with pytest.raises(ValueError, match="No content found in document"):
            await service.generate_flashcards(request)
    
    @pytest.mark.asyncio
    async def test_generate_flashcards_llm_error(self, mock_document_service, mock_llm_service):
        """Test flashcard generation when LLM service fails"""
        mock_llm_service.generate_flashcards = AsyncMock(side_effect=Exception("LLM service error"))
        
        with patch('app.services.flashcard_service.llm_service', mock_llm_service):
            service = FlashcardService(document_service=mock_document_service)
            
            request = FlashcardRequest(
                file_id="test_file_123",
                filename="test_document.pdf"
            )
            
            with pytest.raises(Exception, match="LLM service error"):
                await service.generate_flashcards(request)


class TestLLMServiceFlashcards:
    """Test LLM service flashcard generation"""
    
    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance"""
        return LLMService(model_name="test-model", temperature=0.7)
    
    @pytest.mark.asyncio
    async def test_generate_flashcards_method_exists(self, llm_service):
        """Test that generate_flashcards method exists"""
        assert hasattr(llm_service, 'generate_flashcards')
        assert callable(llm_service.generate_flashcards)
    
    @pytest.mark.asyncio
    async def test_validate_flashcard_format(self, llm_service):
        """Test flashcard format validation"""
        # Test valid flashcard
        valid_card = {
            "front": "What is AI?",
            "back": "Artificial Intelligence",
            "difficulty": "easy"
        }
        assert llm_service._validate_flashcard_format(valid_card) == True
        
        # Test invalid flashcard (missing front)
        invalid_card = {
            "back": "Artificial Intelligence",
            "difficulty": "easy"
        }
        assert llm_service._validate_flashcard_format(invalid_card) == False
        
        # Test invalid flashcard (missing back)
        invalid_card2 = {
            "front": "What is AI?",
            "difficulty": "easy"
        }
        assert llm_service._validate_flashcard_format(invalid_card2) == False
    
    @pytest.mark.asyncio
    async def test_generate_fallback_flashcards(self, llm_service):
        """Test fallback flashcard generation"""
        content = "Artificial intelligence is a branch of computer science. It includes machine learning and deep learning."
        
        flashcards = llm_service._generate_fallback_flashcards(content, 3)
        
        assert len(flashcards) == 3
        assert all("id" in card for card in flashcards)
        assert all("front" in card for card in flashcards)
        assert all("back" in card for card in flashcards)
        assert all("difficulty" in card for card in flashcards)


# Note: API endpoint tests would require a FastAPI test client fixture
# These tests are commented out until we have proper test client setup
# class TestFlashcardAPI:
#     """Test flashcard API endpoints"""
#     
#     @pytest.mark.asyncio
#     async def test_generate_flashcards_endpoint(self, client):
#         """Test flashcard generation endpoint"""
#         request_data = {
#             "file_id": "test_file_123",
#             "filename": "test_document.pdf"
#         }
#         
#         with patch('app.services.flashcard_service.flashcard_service') as mock_service:
#             mock_response = FlashcardResponse(
#                 flashcards=[
#                     Flashcard(
#                         id="test_1",
#                         front="What is AI?",
#                         back="Artificial Intelligence",
#                         difficulty=DifficultyLevel.EASY,
#                         category="Definitions"
#                     )
#                 ],
#                 file_id="test_file_123",
#                 filename="test_document.pdf",
#                 total_cards=1,
#                 processing_time=1.5,
#                 created_at=datetime.now()
#             )
#             mock_service.generate_flashcards = AsyncMock(return_value=mock_response)
#             
#             response = await client.post("/flashcards/generate", json=request_data)
#             
#             assert response.status_code == 200
#             data = response.json()
#             assert data["file_id"] == "test_file_123"
#             assert data["filename"] == "test_document.pdf"
#             assert data["total_cards"] == 1
#             assert len(data["flashcards"]) == 1
#     
#     @pytest.mark.asyncio
#     async def test_generate_flashcards_invalid_request(self, client):
#         """Test flashcard generation with invalid request"""
#         # Missing file_id
#         request_data = {
#             "filename": "test_document.pdf"
#         }
#         
#         response = await client.post("/flashcards/generate", json=request_data)
#         assert response.status_code == 422  # Validation error
#     
#     @pytest.mark.asyncio
#     async def test_flashcard_health_check(self, client):
#         """Test flashcard health check endpoint"""
#         response = await client.get("/flashcards/health")
#         assert response.status_code == 200
#         data = response.json()
#         assert data["status"] in ["healthy", "error"]
#         assert data["service"] == "flashcard-generation"


# Integration test
class TestFlashcardIntegration:
    """Integration tests for flashcard functionality"""
    
    @pytest.mark.asyncio
    async def test_full_flashcard_generation_flow(self):
        """Test complete flashcard generation flow"""
        # This test would require a real document and LLM service
        # For now, we'll test the flow with mocks
        mock_document_service = Mock()
        mock_document_service.get_extracted_text = AsyncMock(return_value="Test content about AI and machine learning.")
        
        mock_llm_service = Mock()
        mock_llm_service.generate_flashcards = AsyncMock(return_value=[
            {
                "id": "flashcard_1",
                "front": "What is AI?",
                "back": "Artificial Intelligence",
                "difficulty": "easy",
                "category": "Definitions"
            }
        ])
        
        with patch('app.services.flashcard_service.llm_service', mock_llm_service):
            service = FlashcardService(document_service=mock_document_service)
            
            request = FlashcardRequest(
                file_id="test_file_123",
                filename="test_document.pdf"
            )
            
            response = await service.generate_flashcards(request)
            
            # Verify the complete flow
            assert response.total_cards == 1
            assert len(response.flashcards) == 1
            assert response.flashcards[0].front == "What is AI?"
            assert response.flashcards[0].back == "Artificial Intelligence"
            assert response.processing_time > 0
