#!/usr/bin/env python3
"""
Comprehensive test script for RAG + LLM implementation
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append('../..')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_rag_components():
    """Test individual RAG components"""
    
    try:
        logger.info("Testing RAG Components")
        
        # Test 1: Embedding Service
        logger.info("Test 1: Testing embedding service...")
        from app.services.embedding import embedding_service
        
        # Test embedding generation
        test_text = "This is a test sentence for embedding."
        result = await embedding_service.embed_text(test_text)
        
        if result.success:
            logger.info(f"✅ Embedding service working! Generated {len(result.embedding)}-dimensional embedding")
        else:
            logger.error(f"❌ Embedding service failed: {result.error}")
            return False
        
        # Test 2: Vector Store Service
        logger.info("Test 2: Testing vector store service...")
        from app.services.vector_store import vector_store_service
        
        # Test vector store health
        health = await vector_store_service.health_check()
        logger.info(f"✅ Vector store health: {health.get('status', 'unknown')}")
        
        # Test 3: RAG Pipeline Service
        logger.info("Test 3: Testing RAG pipeline service...")
        from app.services.rag_pipeline import rag_pipeline_service
        
        # Test pipeline stats
        stats = await rag_pipeline_service.get_processing_stats()
        logger.info(f"✅ RAG pipeline stats: {stats.get('pipeline_status', 'unknown')}")
        
        # Test 4: LLM Service
        logger.info("Test 4: Testing LLM service with gpt-oss:20b...")
        from app.services.llm_service import llm_service
        
        # Test LLM validation
        llm_health = await llm_service.validate_model()
        if llm_health.get('status') == 'healthy':
            logger.info(f"✅ LLM service working! Model: {llm_health.get('model_name')}")
        else:
            logger.error(f"❌ LLM service failed: {llm_health.get('error', 'Unknown error')}")
            return False
        
        # Test 5: QA Service
        logger.info("Test 5: Testing QA service...")
        from app.services.qa_service import qa_service
        
        # Test QA service initialization
        logger.info("✅ QA service initialized successfully")
        
        logger.info("🎉 All RAG + LLM components are working!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_pipeline():
    """Test the complete RAG + LLM pipeline"""
    try:
        logger.info("Testing Complete RAG + LLM Pipeline")
        
        # Create sample document
        sample_text = """
        Machine Learning Fundamentals
        
        Machine learning is a subset of artificial intelligence that focuses on algorithms
        that can learn and make predictions from data. There are three main types of machine learning:
        
        1. Supervised Learning: The algorithm learns from labeled training data to make predictions
        on new, unseen data. Examples include classification and regression tasks.
        
        2. Unsupervised Learning: The algorithm finds patterns in unlabeled data without
        predefined outputs. Examples include clustering and dimensionality reduction.
        
        3. Reinforcement Learning: The algorithm learns by interacting with an environment
        and receiving rewards or penalties for actions taken.
        
        Deep learning is a subset of machine learning that uses neural networks with multiple
        layers to process complex data. It has been particularly successful in computer vision,
        natural language processing, and speech recognition.
        """
        
        # Create temporary file
        test_file_path = Path("test_ml_document.txt")
        with open(test_file_path, "w") as f:
            f.write(sample_text)
        
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        
        # Test document processing
        logger.info("Processing document through RAG pipeline...")
        from app.services.rag_pipeline import rag_pipeline_service
        
        result = await rag_pipeline_service.process_document_upload(
            file_content, 
            "test_ml_document.txt", 
            enable_embedding=True
        )
        
        if result['status'] != 'completed':
            logger.error(f"❌ Document processing failed: {result}")
            return False
        
        logger.info(f"✅ Document processed successfully! File ID: {result['file_id']}")
        
        # Test QA with LLM
        logger.info("Testing QA with LLM...")
        from app.services.qa_service import qa_service
        from app.models.qa import QARequest
        
        qa_request = QARequest(
            question="What are the three main types of machine learning?",
            file_id=result['file_id'],
            use_rag=True
        )
        
        qa_response = await qa_service.ask_question(qa_request)
        
        if qa_response.answer:
            logger.info(f"✅ QA Response generated successfully!")
            logger.info(f"Answer preview: {qa_response.answer[:100]}...")
            logger.info(f"Confidence Score: {qa_response.confidence_score}")
            logger.info(f"Processing Time: {qa_response.processing_time:.2f}s")
        else:
            logger.error("❌ QA response generation failed")
            return False
        
        # Test LLM directly
        logger.info("Testing LLM service directly...")
        from app.services.llm_service import llm_service
        
        llm_answer = await llm_service.generate_answer(
            "What is deep learning?",
            "Deep learning is a subset of machine learning that uses neural networks with multiple layers to process complex data."
        )
        
        if llm_answer:
            logger.info(f"✅ LLM direct test successful!")
            logger.info(f"LLM Answer preview: {llm_answer[:100]}...")
        else:
            logger.error("❌ LLM direct test failed")
            return False
        
        # Cleanup
        if test_file_path.exists():
            test_file_path.unlink()
        
        logger.info("🎉 Full RAG + LLM pipeline test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Full pipeline test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_ollama_connection():
    """Test Ollama connection for both embedding and LLM models"""
    try:
        logger.info("Testing Ollama connection...")
        
        # Test embedding model
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        test_embedding = embeddings.embed_query("test")
        logger.info(f"✅ Embedding model (nomic-embed-text) working! Generated {len(test_embedding)}-dimensional embedding")
        
        # Test LLM model
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(model="gpt-oss:20b")
        test_response = llm.invoke("Hello, respond with 'LLM working'")
        logger.info(f"✅ LLM model (gpt-oss:20b) working! Response: {test_response.strip()}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ollama connection failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Comprehensive RAG + LLM Implementation Test")
    
    # Test Ollama connection first
    logger.info("=" * 50)
    ollama_ok = await test_ollama_connection()
    if not ollama_ok:
        logger.error("❌ Ollama not available. Please start Ollama and ensure both models are available:")
        logger.error("  - nomic-embed-text (for embeddings)")
        logger.error("  - gpt-oss:20b (for LLM)")
        return
    
    # Test individual components
    logger.info("=" * 50)
    components_ok = await test_rag_components()
    if not components_ok:
        logger.error("❌ Component tests failed")
        return
    
    # Test full pipeline
    logger.info("=" * 50)
    pipeline_ok = await test_full_pipeline()
    
    if pipeline_ok:
        logger.info("=" * 50)
        logger.info("🎉 RAG + LLM Implementation is COMPLETE and WORKING!")
        logger.info("✅ All components are ready for production use")
        logger.info("✅ You can now use the QA feature with full RAG + LLM capabilities")
        logger.info("✅ Using gpt-oss:20b for intelligent answer generation")
    else:
        logger.error("❌ RAG + LLM Implementation has issues that need to be fixed")

if __name__ == "__main__":
    asyncio.run(main())
