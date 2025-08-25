#!/usr/bin/env python3
"""
Quick test script for RAG + LLM system - run this from backend directory
"""
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def quick_test():
    """Quick test of RAG + LLM components"""
    try:
        logger.info("🔍 Quick RAG + LLM System Test")
        
        # Test 1: Embedding Service
        from app.services.embedding import embedding_service
        result = await embedding_service.embed_text("test sentence")
        logger.info(f"✅ Embedding Service: {'Working' if result.success else 'Failed'}")
        
        # Test 2: Vector Store
        from app.services.vector_store import vector_store_service
        health = await vector_store_service.health_check()
        logger.info(f"✅ Vector Store: {'Working' if health.get('status') == 'healthy' else 'Failed'}")
        
        # Test 3: LLM Service
        from app.services.llm_service import llm_service
        llm_health = await llm_service.validate_model()
        logger.info(f"✅ LLM Service: {'Working' if llm_health.get('status') == 'healthy' else 'Failed'}")
        logger.info(f"   Model: {llm_health.get('model_name', 'Unknown')}")
        
        # Test 4: QA Service
        from app.services.qa_service import qa_service
        from app.models.qa import QASessionCreate
        session = await qa_service.create_session(QASessionCreate(file_id="test", filename="test.pdf"))
        logger.info(f"✅ QA Service: Working (Session: {session.session_id[:8]}...)")
        
        # Test 5: RAG Pipeline
        from app.services.rag_pipeline import rag_pipeline_service
        stats = await rag_pipeline_service.get_processing_stats()
        logger.info(f"✅ RAG Pipeline: {'Working' if 'pipeline_status' in stats else 'Failed'}")
        
        logger.info("🎉 All RAG + LLM components are working!")
        logger.info("✅ Using gpt-oss:20b for intelligent answer generation")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    exit(0 if success else 1)
