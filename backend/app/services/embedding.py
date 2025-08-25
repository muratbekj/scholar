# Embedding service for converting text into embeddings
from langchain_ollama import OllamaEmbeddings
from typing import List, Dict, Any, Optional
import logging
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Result of embedding operation"""
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class EmbeddingService:
    """Service for generating embeddings using LangChain Ollama"""
    
    def __init__(self, model_name: str = "nomic-embed-text", 
                 batch_size: int = 10, 
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.embeddings = OllamaEmbeddings(model=model_name)
        logger.info(f"Initialized embedding service with model: {model_name}")
    
    async def embed_text(self, text: str, metadata: Dict[str, Any] = None) -> EmbeddingResult:
        """Embed a single text with retry logic"""
        metadata = metadata or {}
        
        for attempt in range(self.max_retries):
            try:
                # Generate embedding
                embedding = await self._generate_embedding(text)
                
                return EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    metadata=metadata,
                    success=True
                )
                
            except Exception as e:
                error_msg = f"Embedding attempt {attempt + 1} failed: {str(e)}"
                logger.warning(error_msg)
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    return EmbeddingResult(
                        text=text,
                        embedding=[],
                        metadata=metadata,
                        success=False,
                        error=str(e)
                    )
    
    async def embed_batch(self, texts: List[str], metadata_list: List[Dict[str, Any]] = None) -> List[EmbeddingResult]:
        """Embed multiple texts in batches"""
        if not texts:
            return []
        
        metadata_list = metadata_list or [{}] * len(texts)
        results = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_metadata = metadata_list[i:i + self.batch_size]
            
            logger.info(f"Processing embedding batch {i//self.batch_size + 1}/{(len(texts) + self.batch_size - 1)//self.batch_size}")
            
            # Process batch concurrently
            batch_tasks = [
                self.embed_text(text, metadata) 
                for text, metadata in zip(batch_texts, batch_metadata)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle any exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append(EmbeddingResult(
                        text=batch_texts[j],
                        embedding=[],
                        metadata=batch_metadata[j],
                        success=False,
                        error=str(result)
                    ))
                else:
                    results.append(result)
        
        return results
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            # Use LangChain Ollama embeddings
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def get_embedding_dimensions(self) -> int:
        """Get the dimensions of the embedding vectors"""
        try:
            # Test embedding to get dimensions
            test_embedding = self.embeddings.embed_query("test")
            return len(test_embedding)
        except Exception as e:
            logger.error(f"Error getting embedding dimensions: {str(e)}")
            return 0
    
    async def validate_embedding_model(self) -> Dict[str, Any]:
        """Validate that the embedding model is working correctly"""
        try:
            test_text = "This is a test sentence for embedding validation."
            embedding = await self._generate_embedding(test_text)
            
            return {
                "status": "healthy",
                "model_name": self.model_name,
                "embedding_dimensions": len(embedding),
                "test_embedding_length": len(embedding)
            }
        except Exception as e:
            return {
                "status": "error",
                "model_name": self.model_name,
                "error": str(e)
            }

# Initialize global embedding service
embedding_service = EmbeddingService()
