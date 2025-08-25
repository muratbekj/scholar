# Test chunking functionality
import pytest
from unittest.mock import Mock, patch
import tempfile
import os
import sys
from pathlib import Path

# Add the app directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.chunking import TextChunkingService, TextChunk
from app.services.document import DocumentService


class TestTextChunkingService:
    """Test the text chunking service"""
    
    def test_fixed_size_chunking(self):
        """Test fixed size chunking"""
        chunker = TextChunkingService(chunk_size=100, chunk_overlap=20)
        text = "This is a test document with multiple sentences. " * 10
        
        chunks = chunker.chunk_text(text, strategy="fixed_size")
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
        assert all(len(chunk.content) <= 100 for chunk in chunks)
    
    def test_sentence_chunking(self):
        """Test sentence-based chunking"""
        chunker = TextChunkingService(chunk_size=50, chunk_overlap=10)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        
        chunks = chunker.chunk_text(text, strategy="sentences")
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
    
    def test_paragraph_chunking(self):
        """Test paragraph-based chunking"""
        chunker = TextChunkingService(chunk_size=30, chunk_overlap=10)  # Smaller chunk size
        text = "First paragraph with more content.\n\nSecond paragraph with more content.\n\nThird paragraph with more content."
        
        chunks = chunker.chunk_text(text, strategy="paragraphs")
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
    
    def test_semantic_chunking(self):
        """Test semantic chunking"""
        chunker = TextChunkingService(chunk_size=100, chunk_overlap=20)
        text = "# Header 1\nContent here.\n\n## Header 2\nMore content."
        
        chunks = chunker.chunk_text(text, strategy="semantic")
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
    
    def test_chunk_statistics(self):
        """Test chunk statistics"""
        chunker = TextChunkingService(chunk_size=100, chunk_overlap=20)
        text = "Test text. " * 20
        
        chunks = chunker.chunk_text(text, strategy="fixed_size")
        stats = chunker.get_chunk_statistics(chunks)
        
        assert "total_chunks" in stats
        assert "average_chunk_size" in stats
        assert "min_chunk_size" in stats
        assert "max_chunk_size" in stats


@pytest.mark.asyncio
class TestDocumentServiceChunking:
    """Test document service with chunking"""
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Create a temporary upload directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def document_service(self, temp_upload_dir):
        """Create document service with small threshold for testing"""
        return DocumentService(
            upload_dir=temp_upload_dir,
            large_document_threshold=100,  # Small threshold for testing
            chunk_size=50,
            chunk_overlap=10
        )
    
    @patch('app.services.document.DocumentExtractor')
    async def test_large_document_chunking(self, mock_extractor, document_service):
        """Test that large documents get chunked"""
        # Mock the extractor to return a large document
        mock_extractor.extract_text.return_value = {
            'content': [{'content': 'Large document content. ' * 20}],
            'metadata': {},
            'format': 'text'
        }
        
        # Create a mock file
        file_content = b"test content"
        filename = "test.txt"
        
        # Process the upload
        result = await document_service.process_upload(file_content, filename)
        
        # Check that chunking info is present
        assert result.content_summary['chunking_info']['is_chunked'] is True
        assert 'chunks' in result.content_summary
        assert len(result.content_summary['chunks']) > 1
    
    @patch('app.services.document.DocumentExtractor')
    async def test_small_document_no_chunking(self, mock_extractor, document_service):
        """Test that small documents don't get chunked"""
        # Mock the extractor to return a small document
        mock_extractor.extract_text.return_value = {
            'content': [{'content': 'Small document.'}],
            'metadata': {},
            'format': 'text'
        }
        
        # Create a mock file
        file_content = b"test content"
        filename = "test.txt"
        
        # Process the upload
        result = await document_service.process_upload(file_content, filename)
        
        # Check that chunking info indicates no chunking
        assert result.content_summary['chunking_info']['is_chunked'] is False
        assert 'chunks' not in result.content_summary


def run_simple_tests():
    """Run simple tests without pytest for quick verification"""
    print("Running simple chunking tests...")
    
    # Test basic chunking
    chunker = TextChunkingService(chunk_size=50, chunk_overlap=10)
    text = "This is a test document. It has multiple sentences. We will chunk it."
    
    chunks = chunker.chunk_text(text, strategy="sentences")
    print(f"✓ Created {len(chunks)} chunks from text")
    
    # Test statistics
    stats = chunker.get_chunk_statistics(chunks)
    print(f"✓ Statistics: {stats['total_chunks']} chunks, avg size: {stats['average_chunk_size']:.1f}")
    
    print("All basic tests passed!")


if __name__ == "__main__":
    # Run simple tests if run directly
    run_simple_tests()
